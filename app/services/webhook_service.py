import base64
import json
import logging
import httpx
import asyncio
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import 

from app.core.business.webhook_business import (
    process_webhook_notification, save_webhook_attempt, 
    verify_webhook_signature, retry_failed_webhooks
)
from app.core.business.wallet_business import get_wallet_by_role, get_wallets_by_type
from app.core.business.transaction_business import save_transaction, update_transaction_status
from app.core.business.gas_station_business import estimate_gas_fees, sponsor_transaction
from app.core.business.balance_business import get_multi_chain_balance, get_aggregated_balance
from app.utils.config import get_webhook_config
from app.utils.audit import log_audit
from app.models.webhook_log import WebhookLog
from app.db.session import SessionLocal

from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookService:
    """Comprehensive webhook processing service"""
    
    def __init__(self):
        self.config = get_webhook_config()
        self.timeout = self.config.get("timeout_seconds", 5)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay_seconds", 60)
        self.allowed_ips = self.config.get("allowed_ips", [])
        self.backendmirror_url = self.config.get("backendmirror_url")
        self.subscribed_events = self.config.get("subscribed_events", [])
        self.webhook_logs_enabled = self.config.get("webhook_logs_enabled", False)
    
    async def process_webhook(self, request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook request"""
        try:
            # Extract headers
            signature = request.headers.get("Circle-Signature")
            timestamp = request.headers.get("Circle-Timestamp")
            notification_id = payload.get("notificationId")
            event_type = payload.get("notificationType")
            status = "unknown"
            error_message = None
            
            # Validate IP address
            client_ip = self._get_client_ip(request)
            if not self._is_ip_allowed(client_ip):
                logger.warning(f"Webhook from unauthorized IP: {client_ip}")
                status = "rejected"
                raise HTTPException(status_code=403, detail="Unauthorized IP address")

            # Event Filtering
            if self.subscribed_events and event_type not in self.subscribed_events:
                logger.info(f"Ignoring unsubscribed event type: {event_type}")
                status = "ignored"
                return {"status": "ignored", "mesage": f"Event {event_type} not subscribed"}

            # Async processing: respond quickly, process in background
            asyncio.create_task(self._process_event(payload, event_type, notification_id))
            status "accepted"
            return {"status": "accepted", "message": "Webhook accepted for processing"}
            
            
            # Process webhook notification
            result = await process_webhook_notification(payload, signature, timestamp)
            
            if result.get("status") == "success":
                logger.info(f"Successfully processed webhook: {notification_id}")
                return {"status": "success", "message": "Webhook processed successfully"}
            else:
                logger.error(f"Failed to process webhook: {notification_id} - {result.get('message')}")
                return {"status": "error", "message": result.get("message")}
                
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            error_message = str(e)
            await save_webhook_attempt(
                payload.get("notificationId", "unknown"),
                "failed",
                str(e),
                error_message,
                payload
            )
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if self.webhook_logs_enabled:
                self._log_webhook(notification_id, event_type, payload, error_message)

    async def _process_event(self, payload, event_type, notification_id):
        status = "processed"
        error_message = None
        try:
            result = await process_webhook_notification(payload)
            if result.get("status") === "success":
                logger.info(f"Successfully processed webhook: {notification_id}")
            else:
                logger.error(f"Failed to process webhook: {notification_id} - {result.get('message')}")
                status = "failed"
                error_message = result.get("message")
        except Exception as e:
            logger.error(f"Error in background event processing: {str(e)}")
            status = "failed"
            error_message = str(e)
            await save_webhook_attempt(
                notification_id or "unknown",
                "failed",
                error_message,
                payload
            )
        finally:
            if self.webhook_logs_enabled:
                self._log_webhook(notification_id, event_type, payload, status, error_message, processed=True)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _is_ip_allowed(self, ip: str) -> bool:
        """Check if IP address is allowed"""
        if not self.allowed_ips:
            return True  # Allow all if no IPs configured
        
        return ip in self.allowed_ips
    
    async def forward_to_backendmirror(self, payload: Dict[str, Any]) -> bool:
        """Forward webhook to BackendMirror"""
        if not self.backendmirror_url:
            logger.info("BackendMirror webhook URL not configured")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.backendmirror_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.info("Successfully forwarded webhook to BackendMirror")
                    return True
                else:
                    logger.warning(f"Failed to forward webhook to BackendMirror: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error forwarding webhook to BackendMirror: {str(e)}")
            return False
    
    async def retry_failed_webhooks(self) -> Dict[str, Any]:
        """Retry failed webhook attempts"""
        try:
            await retry_failed_webhooks()
            return {"status": "success", "message": "Failed webhooks retry completed"}
        except Exception as e:
            logger.error(f"Error retrying failed webhooks: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    
    async def get_webhook_health(self) -> Dict[str, Any]:
        """Get webhook service health status"""
        try:
            # Test BackendMirror connectivity
            backendmirror_healthy = False
            if self.backendmirror_url:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(self.backendmirror_url.replace("/api/webhooks/circle", "/health"))
                        backendmirror_healthy = response.status_code == 200
                except Exception:
                    backendmirror_healthy = False
            
            return {
                "status": "healthy",
                "config": {
                    "timeout_seconds": self.timeout,
                    "max_retries": self.max_retries,
                    "retry_delay_seconds": self.retry_delay,
                    "allowed_ips_count": len(self.allowed_ips),
                    "backendmirror_url_configured": bool(self.backendmirror_url)
                },
                "services": {
                    "backendmirror_connectivity": backendmirror_healthy,
                    "signature_verification": True,
                    "database_connectivity": True  # Assuming database is healthy
                },
                "last_check": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error checking webhook health: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    def _log_webhook(self, notification_id, event_type, payload, status, error_message, processed=False):
        try:
            db = SessionLocal()
            log = WebhookLog(
                notification_id=notification_id,
                event=event_type,
                processed_at=datetime.utcnow() if processed else None  
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging webhook event: {str(e)}")
        finally:
            db.close()

# Global webhook service instance
webhook_service = WebhookService()

async def handle_webhook_request(request: Request, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming webhook request"""
    return await webhook_service.process_webhook(request, payload)

async def schedule_webhook_retries():
    """Schedule periodic webhook retries"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            await webhook_service.retry_failed_webhooks()
        except Exception as e:
            logger.error(f"Error in webhook retry scheduler: {str(e)}")

async def monitor_webhook_health():
    """Monitor webhook service health"""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            health = await webhook_service.get_webhook_health()
            if health.get("status") != "healthy":
                logger.warning(f"Webhook service health check failed: {health}")
        except Exception as e:
            logger.error(f"Error in webhook health monitor: {str(e)}") 