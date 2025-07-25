import asyncio
import time
import logging
import random
import json
from typing import Dict, Optional
from . import http_client
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis client - will be initialized on app startup
redis_client: Optional[redis.Redis] = None

class SmartHealthManager:
    def __init__(self):
        self.background_task: Optional[asyncio.Task] = None
        self.running = False
        self.processors = {
            'default': 'http://payment-processor-default:8080/payments/service-health',
            'fallback': 'http://payment-processor-fallback:8080/payments/service-health'
        }
        self.lock_key = "health_check_lock"

    async def start_background_monitoring(self):
        if self.running: return
        self.running = True
        self.background_task = asyncio.create_task(self._background_monitor())
        logger.info("Background health monitoring started")

    async def stop_background_monitoring(self):
        self.running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError: pass
        logger.info("Background health monitoring stopped")

    async def _background_monitor(self):
        """Leader election loop to perform health checks."""
        await asyncio.sleep(random.uniform(0, 1))
        while self.running:
            try:
                # Try to acquire a lock with a timeout.
                # The first worker to acquire it becomes the leader.
                is_leader = await redis_client.set(self.lock_key, "leader", ex=10, nx=True)
                if is_leader:
                    logger.info("Acquired health check lock, performing checks.")
                    await self._update_health_status_in_redis()
                else:
                    logger.debug("Did not acquire health check lock.")
                
                # Wait 5 seconds before the next leader election attempt.
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)

    async def _update_health_status_in_redis(self):
        """Fetch health status and store it in Redis."""
        tasks = [self._check_and_store(p) for p in self.processors.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_and_store(self, processor: str):
        try:
            url = self.processors[processor]
            result = await http_client.http_client.get_fast(url)
            
            health_status = {
                'failing': result.get('failing', True) if result else True,
                'minResponseTime': result.get('minResponseTime', 9999) if result else 9999,
                'checked_at': time.time()
            }
            await redis_client.set(f"health:{processor}", json.dumps(health_status))
        except Exception as e:
            logger.error(f"Failed to check and store health for {processor}: {e}")

    async def get_best_processor(self) -> str:
        """Get the best processor from Redis cache."""
        try:
            default_raw = await redis_client.get("health:default")
            fallback_raw = await redis_client.get("health:fallback")

            default_health = json.loads(default_raw) if default_raw else {"failing": True, "minResponseTime": 9999}
            fallback_health = json.loads(fallback_raw) if fallback_raw else {"failing": True, "minResponseTime": 9999}

            # Estimated profit per request = (1 - fee) / latency
            DEFAULT_FEE = 0.05  # 5% fee
            FALLBACK_FEE = 0.15  # 15% fee

            # Protect against div-by-zero and absent keys
            d_latency = max(default_health.get("minResponseTime", 9999), 1)
            f_latency = max(fallback_health.get("minResponseTime", 9999), 1)

            score_default = (0 if default_health.get("failing", True) else 1) * ((1 - DEFAULT_FEE) / d_latency)
            score_fallback = (0 if fallback_health.get("failing", True) else 1) * ((1 - FALLBACK_FEE) / f_latency)

            return "default" if score_default >= score_fallback else "fallback"
        except Exception as e:
            logger.error(f"Failed to get best processor from Redis: {e}")
            return "default"

    async def is_processor_healthy(self, processor: str) -> bool:
        """Check if a processor is healthy from Redis cache."""
        try:
            raw_data = await redis_client.get(f"health:{processor}")
            if not raw_data: return False
            health = json.loads(raw_data)
            return not health.get("failing", True)
        except Exception as e:
            logger.error(f"Failed to check health for {processor} from Redis: {e}")
            return False

# Global instance
health_manager = SmartHealthManager() 