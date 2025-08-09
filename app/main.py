from fastapi import FastAPI
from app.api.routes import router as api_router
from app.api.webhook_routes import router as webhook_router
from app.api.webhook_log_routes import router as webhook_log_router

from app.services.webhook_service import schedule_webhook_retries, monitor_webhook_health
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Circle Payments Engine",
    description="Enhanced Circle Payments Engine with Three-Wallet Architecture and Webhook Notifications",
    version="2.0.0"
)

# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")
app.include_router(webhook_log_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Starting Circle Payments Engine...")
    
    # Start background tasks
    asyncio.create_task(schedule_webhook_retries())
    asyncio.create_task(monitor_webhook_health())
    
    logger.info("Circle Payments Engine started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down Circle Payments Engine...")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Circle Payments Engine API",
        "version": "2.0.0",
        "features": [
            "Three-Wallet Architecture (BackendMirror, Circle Engine, Solana)",
            "Multi-Chain Support (EVM + Solana)",
            "Webhook Notifications with Signature Verification",
            "Gas Station Integration",
            "Multi-Chain Balance Aggregation",
            "Enhanced Transaction Tracking"
        ],
        "endpoints": {
            "api": "/api",
            "webhooks": "/api/webhooks",
            "health": "/api/webhooks/health",
            "documentation": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Circle Payments Engine",
        "version": "2.0.0"
    }
