from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
from .routers import payments_router, summary_router
from .database import db
from . import http_client, health_manager as health_manager_module
from .http_client import UltraFastHTTPClient
from .payment_processor import payment_processor
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with performance optimizations
app = FastAPI(
    title="Rinha Backend 2025",
    description="Ultra-fast payment processing backend",
    version="1.0.0",
    docs_url=None,  # Disable docs for performance
    redoc_url=None,  # Disable redoc for performance
    openapi_url=None  # Disable openapi for performance
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(payments_router)
app.include_router(summary_router)

@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    logger.info("Starting Rinha Backend 2025...")
    
    try:
        # Initialize Redis client
        logger.info("Initializing Redis client...")
        redis_pool = redis.ConnectionPool(host='redis', port=6379, db=0, decode_responses=True)
        health_manager_module.redis_client = redis.Redis(connection_pool=redis_pool)
        await health_manager_module.redis_client.ping() # Verify connection
        logger.info("Redis client initialized successfully")

        # Initialize HTTP Client
        logger.info("Initializing HTTP client...")
        http_client.http_client = UltraFastHTTPClient()
        logger.info("HTTP client initialized successfully")

        # Initialize database
        logger.info("Initializing database...")
        await db.init_pool()
        logger.info("Database initialized successfully")
        
        # Start health monitoring
        logger.info("Starting health monitoring...")
        # health_manager singleton is already imported, just need to start it
        from .health_manager import health_manager
        await health_manager.start_background_monitoring()
        logger.info("Health monitoring started successfully")
        
        # Start DB writer worker
        logger.info("Starting DB writer worker...")
        payment_processor.start_db_writer()
        logger.info("DB writer worker started successfully")
        
        logger.info("Rinha Backend 2025 started successfully!")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Rinha Backend 2025...")
    
    try:
        # Stop DB writer worker first
        payment_processor.stop_db_writer()

        # Stop health monitoring
        from .health_manager import health_manager
        await health_manager.stop_background_monitoring()
        
        # Close Redis client
        if health_manager_module.redis_client:
            await health_manager_module.redis_client.close()

        # Close HTTP client
        if http_client.http_client:
            await http_client.http_client.close()
        
        logger.info("Shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/status")
async def status():
    """Status endpoint with processor information"""
    return {
        "status": "running",
        "processors": payment_processor.get_processor_status()
    } 