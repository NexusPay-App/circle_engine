from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.services.webhook_service import webhook_service, handle_webhook_request
from app.core.business.webhook_business import get_webhook_statistics
from app.core.business.wallet_business import get_wallet_by_role, get_wallets_by_type
from app.core.business.transaction_business import get_transactions_by_blockchain
from app.core.business.balance_business import get_multi_chain_balance, get_aggregated_balance, get_ecosystem_balance_summary
from app.core.business.gas_station_business import estimate_gas_fees, sponsor_transaction, get_gas_station_status, monitor_gas_station_health
from app.utils.config import get_webhook_config
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class WebhookPayload(BaseModel):
    subscriptionId: str
    notificationId: str
    notificationType: str
    notification: Dict[str, Any]
    timestamp: str
    version: int

class WebhookHealthResponse(BaseModel):
    status: str
    config: Dict[str, Any]
    services: Dict[str, Any]
    last_check: float

@router.post("/circle")
async def receive_circle_webhook(request: Request, payload: WebhookPayload):
    """
    Receive and process Circle webhook notifications
    """
    try:
        result = await handle_webhook_request(request, payload.dict())
        return result
    except Exception as e:
        logger.error(f"Error processing Circle webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def get_webhook_health() -> WebhookHealthResponse:
    """
    Get webhook service health status
    """
    try:
        health = await webhook_service.get_webhook_health()
        return WebhookHealthResponse(**health)
    except Exception as e:
        logger.error(f"Error getting webhook health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry")
async def retry_failed_webhooks():
    """
    Manually trigger retry of failed webhook attempts
    """
    try:
        result = await webhook_service.retry_failed_webhooks()
        return result
    except Exception as e:
        logger.error(f"Error retrying failed webhooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_webhook_statistics_endpoint(days: int = 30):
    """
    Get webhook processing statistics
    """
    try:
        stats = get_webhook_statistics(days)
        return {
            "statistics": stats,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting webhook statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_webhook_config_endpoint():
    """
    Get current webhook configuration
    """
    try:
        config = get_webhook_config()
        # Remove sensitive information
        safe_config = {
            "timeout_seconds": config.get("timeout_seconds"),
            "max_retries": config.get("max_retries"),
            "retry_delay_seconds": config.get("retry_delay_seconds"),
            "backendmirror_url_configured": bool(config.get("backendmirror_url")),
            "allowed_ips_count": len(config.get("allowed_ips", [])),
            "allowed_ips": config.get("allowed_ips", [])  # Show IPs for debugging
        }
        return safe_config
    except Exception as e:
        logger.error(f"Error getting webhook config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gas-station/status")
async def get_gas_station_status_endpoint(blockchain: Optional[str] = None):
    """
    Get gas station status for supported blockchains
    """
    try:
        status = await get_gas_station_status(blockchain)
        return status
    except Exception as e:
        logger.error(f"Error getting gas station status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gas-station/health")
async def get_gas_station_health_endpoint():
    """
    Get comprehensive gas station health status
    """
    try:
        health = await monitor_gas_station_health()
        return health
    except Exception as e:
        logger.error(f"Error getting gas station health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ecosystem/balance")
async def get_ecosystem_balance_endpoint():
    """
    Get complete ecosystem balance summary
    """
    try:
        balance_summary = await get_ecosystem_balance_summary()
        return balance_summary
    except Exception as e:
        logger.error(f"Error getting ecosystem balance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_webhook_endpoint():
    """
    Test webhook endpoint connectivity
    """
    try:
        return {
            "status": "success",
            "message": "Webhook endpoint is working",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": 1
        }
    except Exception as e:
        logger.error(f"Error in webhook test: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.head("/")
async def webhook_head_request():
    """
    Handle HEAD requests for webhook endpoint validation
    """
    return {"status": "ok"}

# Additional webhook management endpoints

@router.get("/events")
async def get_webhook_events(limit: int = 100, notification_type: Optional[str] = None):
    """
    Get recent webhook events
    """
    try:
        from app.db.session import SessionLocal
        from app.models.webhook import WebhookEvent
        
        db = SessionLocal()
        try:
            query = db.query(WebhookEvent).order_by(WebhookEvent.created_at.desc())
            
            if notification_type:
                query = query.filter(WebhookEvent.notification_type == notification_type)
            
            events = query.limit(limit).all()
            
            return {
                "events": [
                    {
                        "id": event.id,
                        "notification_id": event.notification_id,
                        "notification_type": event.notification_type,
                        "subscription_id": event.subscription_id,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                        "version": event.version,
                        "created_at": event.created_at.isoformat() if event.created_at else None
                    }
                    for event in events
                ],
                "total": len(events),
                "limit": limit
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting webhook events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attempts")
async def get_webhook_attempts(limit: int = 100, status: Optional[str] = None):
    """
    Get webhook attempt history
    """
    try:
        from app.db.session import SessionLocal
        from app.models.webhook import WebhookAttempt
        
        db = SessionLocal()
        try:
            query = db.query(WebhookAttempt).order_by(WebhookAttempt.created_at.desc())
            
            if status:
                query = query.filter(WebhookAttempt.status == status)
            
            attempts = query.limit(limit).all()
            
            return {
                "attempts": [
                    {
                        "id": attempt.id,
                        "notification_id": attempt.notification_id,
                        "status": attempt.status,
                        "attempt_number": attempt.attempt_number,
                        "error_message": attempt.error_message,
                        "created_at": attempt.created_at.isoformat() if attempt.created_at else None
                    }
                    for attempt in attempts
                ],
                "total": len(attempts),
                "limit": limit
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting webhook attempts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signatures")
async def get_webhook_signatures(limit: int = 100, verification_status: Optional[str] = None):
    """
    Get webhook signature verification history
    """
    try:
        from app.db.session import SessionLocal
        from app.models.webhook import WebhookSignature
        
        db = SessionLocal()
        try:
            query = db.query(WebhookSignature).order_by(WebhookSignature.created_at.desc())
            
            if verification_status:
                query = query.filter(WebhookSignature.verification_status == verification_status)
            
            signatures = query.limit(limit).all()
            
            return {
                "signatures": [
                    {
                        "id": sig.id,
                        "notification_id": sig.notification_id,
                        "verification_status": sig.verification_status,
                        "timestamp": sig.timestamp,
                        "created_at": sig.created_at.isoformat() if sig.created_at else None
                    }
                    for sig in signatures
                ],
                "total": len(signatures),
                "limit": limit
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting webhook signatures: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 