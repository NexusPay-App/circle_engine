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

@router.get("/wallets/role/{role}")
async def get_wallet_by_role_endpoint(role: str):
    """
    Get wallet details by role (e.g backendMirror, circleEngine, solanaOperations)
    via the webhook management API.
    """
    try:
        wallet = await get_wallet_by_role(role)
        if wallet:
            return {
                "wallet": {
                    "id": wallet.id,
                    "address": wallet.address,
                    "blockchain": wallet.blockchain,
                    "account_type": wallet.account_type,
                    "role": wallet.role,
                    "wallet_type": wallet.wallet_type,
                    "state": wallet.state
                }
            }
        raise HTTPException(status_code=404, detail=f"Wallet with role '{role}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet by role via  webhook API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets/type/{wallet_type}")
async def get_wallet_by_type(wallet_type: str):
    """
    Get all wallets by type (EVM, SOLANA) via the webhook management API.
    """
    try:
        wallets = get_wallets_by_type(wallet_type)
        return {
            "wallets": [
                {
                    "id": wallet.id,
                    "address": wallet.address,
                    "blockchain": wallet.blockchain,
                    "account_type": wallet.account_type,
                    "role": wallet.role,
                    "wallet_type": wallet.wallet_type,
                    "state": wallet.state
                }
                for wallet in wallets
            ],
            "total": len(wallets),
            "wallet_type": wallet_type

        }
    except Exception as e:
        logger.error(f"Error getting wallets by type via webhook API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("transactions/blockchain/{blockchain}")
async def get_transactions_by_blockchain(blockchain: str, limit: int = 100):
    """
    Get transactions by blockchain via the webhook management API.
    """
    try:
        transactions = get_transactions_by_blockchain(blockchain, limit)
        return {
            "transactions": [
                {
                    "id": tx.id,
                    "wallet_id": tx.wallet_id,
                    "token_id": tx.token_id,
                    "destination_address": tx.destination_address,
                    "amount": tx.amount,
                    "status": tx.status,
                    "blockchain": tx.blockchain,
                    "tx_hash": tx.tx_hash,
                    "confirmations": tx.confirmations,
                    "confirmation_required": tx.confirmation_required,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None,
                }
                for tx in transactions
            ],
            "total": len(transactions),
            "blockchain": blockchain
        }
    except Exception as e:
        logger.error(f"Error getting transactions by blockchain via webhook API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("wallets/{wallet_id}/multi-chain-balance")
async def get_multi_chain_balance(wallet_id: str):
    """
    Get aggregated balance across all blockchains for a specific wallet via
    the webhook management API.
    """
    try:
        balance_data = await get_multi_chain_balance(wallet_id)
        if balance_data:
            return balance_data
        raise HTTPException(status_code=404, detail=f"Balance data not found for wallet ID: {wallet_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting multi-chain balance via webhook API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/aggregated-balances")
async def get_aggregated_balance(
    role: Optional[str] = None,
    wallet_type: Optional[str] = None
):
    """
    Get aggregated balance across multiple wallets, optionally filtered by role or wallet type,
    via the webhook management API.
    """
    try:
        aggregated_data = await get_aggregated_balance(role=role, wallet_type=wallet_type)
        if aggregated_data:
            return aggregated_data
        raise HTTPException(status_code=404, detail="No aggregated balance data found.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting aggregated balance via webhook  API: {str(e)}")
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


@router.get("/gas-station/estimate-fees")
async def estimate_gas_fees(
    blockchain: str,
    transaction_type: str = "transfer",
    gas_level: str = "MEDIUM"
):
    """
    Estimate gas fees for a specific blockchain and transaction type
    via the webhook management API.
    """
    try:
        estimate = await estimate_gas_fees(blockchain, transaction_type, gas_level)
        return estimate
    except Exception as e:
        logger.error(f"Error estimating gas fees via webhook API: {str(e)}")
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


class SponsorTransactionRequest(BaseModel):
    transaction_id: str
    wallet_id: str
    blockchain: str
    gas_level: str = "MEDIUM"

@router.post("/gas-station/sponsor-transaction")
async def api_sponsor_transaction_endpoint(request_body: SponsorTransactionRequest):
    """
    Manually sponsor a transaction using Circle Gas Station
    via the webhook management API.
    (USE WITH EXTREME CAUTION - REQUIRES STRONG AUTHENTICATION)
    """
    try:
        # Implement robust authentication and authorization here
        # For example, check if the user making this API call has admin privileges

        result = await sponsor_transaction(
            request_body.transaction_id,
            request_body.wallet_id,
            request_body.blockchain,
            request_body.gas_level
        )
        return result
    except Exception as e:
        logger.error(f"Error sponsoring transaction via webhook API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
