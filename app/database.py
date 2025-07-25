import asyncpg
import asyncio
from typing import Dict, Optional
from decimal import Decimal
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FastDatabase:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def init_pool(self):
        """Initialize connection pool with performance optimizations"""
        try:
            self.pool = await asyncpg.create_pool(
                host='postgres',
                port=5432,
                user='postgres',
                password='postgres',
                database='payments',
                min_size=5,
                max_size=10,
                command_timeout=5.0,
                server_settings={
                    'jit': 'off',
                    'synchronous_commit': 'off',
                    'random_page_cost': '1.1',
                    'effective_io_concurrency': '200'
                }
            )
            await self._create_tables()
            logger.info("Database pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def _create_tables(self):
        """Create optimized tables, one statement at a time for robustness."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    correlation_id VARCHAR(255) UNIQUE NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    processor VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_processor ON payments(processor);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_correlation_id ON payments(correlation_id);")
    
    async def insert_payment_fast(self, correlation_id: str, amount: Decimal, processor: str) -> bool:
        """Insert payment with maximum performance"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO payments (correlation_id, amount, processor, created_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (correlation_id) DO NOTHING
                    """,
                    correlation_id, amount, processor
                )
            return True
        except Exception as e:
            logger.error(f"Failed to insert payment: {e}")
            return False
    
    async def insert_many_payments_fast(self, payments: list) -> bool:
        """Insert a batch of payments using executemany for high performance."""
        if not payments:
            return True
        try:
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO payments (correlation_id, amount, processor, created_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (correlation_id) DO NOTHING
                    """,
                    payments
                )
            return True
        except Exception as e:
            logger.error(f"Failed to insert batch of payments: {e}")
            return False

    async def get_summary_fast(self, from_time: Optional[str] = None, to_time: Optional[str] = None) -> Dict:
        """Get payment summary with maximum performance"""
        try:
            async with self.pool.acquire() as conn:
                if from_time and to_time:
                    from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
                    to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
                    rows = await conn.fetch(
                        """
                        SELECT 
                            processor,
                            COUNT(*) as total_requests,
                            COALESCE(SUM(amount), 0) as total_amount
                        FROM payments 
                        WHERE created_at BETWEEN $1 AND $2
                        GROUP BY processor
                        """,
                        from_dt, to_dt
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT 
                            processor,
                            COUNT(*) as total_requests,
                            COALESCE(SUM(amount), 0) as total_amount
                        FROM payments 
                        GROUP BY processor
                        """
                    )
            
            result = {
                'default': {'totalRequests': 0, 'totalAmount': 0.0}, 
                'fallback': {'totalRequests': 0, 'totalAmount': 0.0}
            }
            
            for row in rows:
                processor_name = row['processor']
                if processor_name == 'default':
                    result['default']['totalRequests'] = row['total_requests']
                    result['default']['totalAmount'] = float(row['total_amount'])
                elif processor_name == 'fallback':
                    result['fallback']['totalRequests'] = row['total_requests']
                    result['fallback']['totalAmount'] = float(row['total_amount'])
            
            return result
                
        except Exception as e:
            logger.error(f"Failed to get summary: {e}")
            return {
                'default': {'totalRequests': 0, 'totalAmount': 0.0}, 
                'fallback': {'totalRequests': 0, 'totalAmount': 0.0}
            }

# Global database instance
db = FastDatabase() 