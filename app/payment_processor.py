import asyncio
import time
import logging
from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime, timezone
import json
from . import http_client, health_manager as health_manager_module
from .health_manager import health_manager
from .database import db

logger = logging.getLogger(__name__)

DB_WRITE_QUEUE_KEY = "db_write_queue"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class PaymentProcessor:
    def __init__(self):
        # More aggressive thresholds to reduce time stuck on fallback
        self.circuit_breakers = {
            'default': CircuitBreaker(failure_threshold=3, recovery_timeout=5),
            'fallback': CircuitBreaker(failure_threshold=3, recovery_timeout=5)
        }
        
        # Processor URLs
        self.processors = {
            'default': 'http://payment-processor-default:8080/payments',
            'fallback': 'http://payment-processor-fallback:8080/payments'
        }
        self.db_writer_task: Optional[asyncio.Task] = None
        self.running = False

    def start_db_writer(self):
        """Starts the background task that writes to the database."""
        if self.running: return
        self.running = True
        self.db_writer_task = asyncio.create_task(self._db_writer_worker())
        logger.info("Database writer worker started.")

    def stop_db_writer(self):
        """Stops the background database writer task."""
        self.running = False
        if self.db_writer_task:
            self.db_writer_task.cancel()
            try:
                asyncio.wait_for(self.db_writer_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("Database writer worker stopped.")

    async def _db_writer_worker(self):
        """Continuously pulls payments from Redis and writes them to PostgreSQL."""
        while self.running:
            try:
                # Use BRPOP to wait for items and pull a batch of up to 1000
                # This is more efficient than pulling one by one.
                # Timeout of 1s allows the loop to check self.running periodically.
                queue_data = await health_manager_module.redis_client.lpop(DB_WRITE_QUEUE_KEY, 1000)
                if not queue_data:
                    await asyncio.sleep(0.1) # short sleep when queue is empty
                    continue
                
                payments_to_write = []
                for item in queue_data:
                    try:
                        p = json.loads(item)
                        payments_to_write.append((p['correlation_id'], Decimal(p['amount']), p['processor']))
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(f"Could not decode payment data from queue: {item}, error: {e}")

                if payments_to_write:
                    success = await db.insert_many_payments_fast(payments_to_write)
                    if not success:
                        logger.error(f"Failed to write a batch of {len(payments_to_write)} payments to DB. Re-queuing items.")
                        # Push raw items back so we retry later (at-least-once guarantee)
                        await health_manager_module.redis_client.rpush(DB_WRITE_QUEUE_KEY, *queue_data)

            except Exception as e:
                logger.error(f"Error in DB writer worker: {e}")
                await asyncio.sleep(1) # a longer sleep on error

    async def process_payment(self, correlation_id: str, amount: Decimal) -> bool:
        """Process payment and push to Redis queue for DB writing."""
        # Get best processor based on health
        processor = await health_manager.get_best_processor()
        
        # Try primary processor first
        success = await self._try_processor(processor, correlation_id, amount)
        if success:
            return True
        
        # If primary failed, try fallback
        if processor == 'default':
            success = await self._try_processor('fallback', correlation_id, amount)
            if success:
                return True
        
        # If both failed, try default again (circuit breaker might have reset)
        if processor == 'fallback':
            success = await self._try_processor('default', correlation_id, amount)
            if success:
                return True
        
        logger.error(f"All processors failed for payment {correlation_id}")
        return False
    
    async def _try_processor(self, processor: str, correlation_id: str, amount: Decimal) -> bool:
        """Try to process payment with a specific processor"""
        circuit_breaker = self.circuit_breakers[processor]
        
        # Check circuit breaker
        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker OPEN for {processor}")
            return False
        
        # Check health cache from Redis
        if not await health_manager.is_processor_healthy(processor):
            logger.warning(f"Processor {processor} marked as unhealthy in Redis")
            circuit_breaker.on_failure()
            return False
        
        try:
            # Prepare payment data
            payment_data = {
                'correlationId': correlation_id,
                'amount': float(amount),
                'requestedAt': datetime.now(timezone.utc).isoformat()
            }
            
            # Send to processor
            url = self.processors[processor]
            result = await http_client.http_client.post_fast(url, payment_data)
            
            if result:
                # Success: update circuit breaker and store in DB immediately for consistency
                circuit_breaker.on_success()
                write_ok = await db.insert_payment_fast(correlation_id, amount, processor)
                if not write_ok:
                    # Fall back to queue so we don't lose the record
                    payment_for_queue = {
                        'correlation_id': correlation_id,
                        'amount': str(amount),
                        'processor': processor
                    }
                    await health_manager_module.redis_client.rpush(DB_WRITE_QUEUE_KEY, json.dumps(payment_for_queue))
                    logger.warning(f"DB insert failed for {correlation_id}. Payment queued for later persistence.")
                else:
                    logger.info(f"Payment {correlation_id} processed via {processor} and stored in DB.")
                return True
            else:
                # Failed - update circuit breaker
                circuit_breaker.on_failure()
                logger.warning(f"Payment {correlation_id} failed via {processor}")
                return False
                
        except Exception as e:
            # Exception - update circuit breaker
            circuit_breaker.on_failure()
            logger.error(f"Exception processing payment {correlation_id} via {processor}: {e}")
            return False
    
    def get_processor_status(self) -> Dict:
        """Get status of all processors"""
        return {
            'default': {
                'circuit_breaker': self.circuit_breakers['default'].state
            },
            'fallback': {
                'circuit_breaker': self.circuit_breakers['fallback'].state
            }
        }

# Global payment processor instance
payment_processor = PaymentProcessor() 