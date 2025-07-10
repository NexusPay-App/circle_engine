from app.db.session import SessionLocal
from app.models.webhook import WebhookEvent, WebhookAttempt, WebhookSubscription, WebhookSignature
from app.utils.audit import log_audit
from app.utils.config import get_webhook_config
from datetime import datetime
import logging
import httpx
import asyncio
import json
import base64
import hmac
import hashlib

logger = logging.getLogger(__name__)

async def save_webhook_event(subscription_id: str, notification_id: str, 
                           notification_type: str, notification_data: dict,
                           timestamp: str, version: int):
    """Save webhook event to database"""
    db = SessionLocal()
    try:
        # Parse timestamp
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        event = WebhookEvent(
            subscription_id=subscription_id,
            notification_id=notification_id,
            notification_type=notification_type,
            notification_data=notification_data,
            timestamp=parsed_timestamp,
            version=version
        )
        db.add(event)
        db.commit()
        log_audit("webhook_event_saved", {
            "notification_id": notification_id,
            "notification_type": notification_type
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving webhook event: {str(e)}")
        raise
    finally:
        db.close()

async def save_webhook_attempt(notification_id: str, status: str, 
                             error_message: str = None, payload: dict = None):
    """Save webhook attempt for debugging"""
    db = SessionLocal()
    try:
        # Get attempt number
        attempt_count = db.query(WebhookAttempt).filter(
            WebhookAttempt.notification_id == notification_id
        ).count()
        
        attempt = WebhookAttempt(
            notification_id=notification_id,
            status=status,
            error_message=error_message,
            payload=payload or {},
            attempt_number=attempt_count + 1
        )
        db.add(attempt)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving webhook attempt: {str(e)}")
        raise
    finally:
        db.close()

def verify_webhook_signature(payload: str, signature: str, timestamp: str, webhook_secret: str):
    """Verify webhook signature using HMAC SHA256"""
    try:
        # Create the signature string
        signature_string = f"{timestamp}.{payload}"
        
        # Create expected signature
        expected_signature = base64.b64encode(
            hmac.new(
                webhook_secret.encode('utf-8'),
                signature_string.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False

async def save_webhook_signature(notification_id: str, signature: str, timestamp: str, verification_status: str):
    """Save webhook signature for audit trail"""
    db = SessionLocal()
    try:
        sig = WebhookSignature(
            notification_id=notification_id,
            signature=signature,
            timestamp=timestamp,
            verification_status=verification_status
        )
        db.add(sig)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving webhook signature: {str(e)}")
        raise
    finally:
        db.close()

async def process_webhook_notification(notification_data: dict, signature: str = None, timestamp: str = None):
    """Process incoming webhook notification"""
    try:
        # Extract notification details
        subscription_id = notification_data.get("subscriptionId")
        notification_id = notification_data.get("notificationId")
        notification_type = notification_data.get("notificationType")
        notification = notification_data.get("notification", {})
        notification_timestamp = notification_data.get("timestamp")
        version = notification_data.get("version", 1)
        
        # Verify signature if provided
        if signature and timestamp:
            webhook_config = get_webhook_config()
            webhook_secret = webhook_config.get("webhook_secret")
            if webhook_secret:
                payload = json.dumps(notification_data, separators=(',', ':'))
                is_valid = verify_webhook_signature(payload, signature, timestamp, webhook_secret)
                verification_status = "verified" if is_valid else "failed"
                
                await save_webhook_signature(notification_id, signature, timestamp, verification_status)
                
                if not is_valid:
                    logger.warning(f"Invalid webhook signature for notification: {notification_id}")
                    return {"status": "error", "message": "Invalid signature"}
        
        # Save webhook event
        await save_webhook_event(
            subscription_id, notification_id, notification_type, 
            notification, notification_timestamp, version
        )
        
        # Process based on notification type
        await route_webhook_notification(notification_type, notification, notification_id)
        
        # Forward to BackendMirror if configured
        await forward_to_backendmirror(notification_data)
        
        return {"status": "success", "message": "Webhook processed successfully"}
        
    except Exception as e:
        logger.error(f"Error processing webhook notification: {str(e)}")
        await save_webhook_attempt(
            notification_data.get("notificationId", "unknown"),
            "failed",
            str(e),
            notification_data
        )
        return {"status": "error", "message": str(e)}

async def route_webhook_notification(notification_type: str, notification: dict, notification_id: str):
    """Route webhook notification based on type"""
    try:
        if notification_type == "transaction.status.updated":
            await handle_transaction_status_update(notification, notification_id)
        elif notification_type == "wallet.balance.updated":
            await handle_wallet_balance_update(notification, notification_id)
        elif notification_type == "wallet.created":
            await handle_wallet_created(notification, notification_id)
        elif notification_type == "webhooks.test":
            await handle_webhook_test(notification, notification_id)
        else:
            logger.info(f"Unhandled webhook notification type: {notification_type}")
            
    except Exception as e:
        logger.error(f"Error routing webhook notification: {str(e)}")
        raise

async def handle_transaction_status_update(notification: dict, notification_id: str):
    """Handle transaction status update notification"""
    try:
        from .transaction_business import update_transaction_status
        
        transaction_id = notification.get("transactionId")
        status = notification.get("status")
        
        if transaction_id and status:
            await update_transaction_status(transaction_id, status, notification)
            logger.info(f"Updated transaction {transaction_id} status to {status}")
        else:
            logger.warning(f"Missing transaction ID or status in notification: {notification_id}")
            
    except Exception as e:
        logger.error(f"Error handling transaction status update: {str(e)}")
        raise

async def handle_wallet_balance_update(notification: dict, notification_id: str):
    """Handle wallet balance update notification"""
    try:
        from .balance_business import update_wallet_balance
        
        wallet_id = notification.get("walletId")
        balances = notification.get("balances", [])
        
        if wallet_id and balances:
            await update_wallet_balance(wallet_id, balances)
            logger.info(f"Updated wallet {wallet_id} balances")
        else:
            logger.warning(f"Missing wallet ID or balances in notification: {notification_id}")
            
    except Exception as e:
        logger.error(f"Error handling wallet balance update: {str(e)}")
        raise

async def handle_wallet_created(notification: dict, notification_id: str):
    """Handle wallet created notification"""
    try:
        wallet_data = notification.get("wallet", {})
        if wallet_data:
            logger.info(f"New wallet created: {wallet_data.get('id')}")
            # Additional wallet creation logic can be added here
        else:
            logger.warning(f"Missing wallet data in notification: {notification_id}")
            
    except Exception as e:
        logger.error(f"Error handling wallet created notification: {str(e)}")
        raise

async def handle_webhook_test(notification: dict, notification_id: str):
    """Handle webhook test notification"""
    try:
        logger.info(f"Webhook test received: {notification}")
        # Webhook test logic can be added here
        
    except Exception as e:
        logger.error(f"Error handling webhook test: {str(e)}")
        raise

async def forward_to_backendmirror(notification_data: dict):
    """Forward webhook notification to BackendMirror"""
    try:
        webhook_config = get_webhook_config()
        backendmirror_url = webhook_config.get("backendmirror_url")
        
        if not backendmirror_url:
            logger.info("BackendMirror webhook URL not configured, skipping forward")
            return
        
        timeout = webhook_config.get("timeout_seconds", 5)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                backendmirror_url,
                json=notification_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully forwarded webhook to BackendMirror")
            else:
                logger.warning(f"Failed to forward webhook to BackendMirror: {response.status_code}")
                
    except Exception as e:
        logger.error(f"Error forwarding webhook to BackendMirror: {str(e)}")

async def retry_failed_webhooks():
    """Retry failed webhook attempts"""
    try:
        db = SessionLocal()
        webhook_config = get_webhook_config()
        max_retries = webhook_config.get("max_retries", 3)
        retry_delay = webhook_config.get("retry_delay_seconds", 60)
        
        # Get failed webhook attempts
        failed_attempts = db.query(WebhookAttempt).filter(
            WebhookAttempt.status == "failed",
            WebhookAttempt.attempt_number < max_retries
        ).all()
        
        for attempt in failed_attempts:
            try:
                # Get the original webhook event
                event = db.query(WebhookEvent).filter(
                    WebhookEvent.notification_id == attempt.notification_id
                ).first()
                
                if event:
                    # Retry processing
                    await process_webhook_notification(event.notification_data)
                    
                    # Update attempt status
                    attempt.status = "success"
                    db.commit()
                    
                    logger.info(f"Successfully retried webhook: {attempt.notification_id}")
                    
                    # Wait before next retry
                    await asyncio.sleep(retry_delay)
                    
            except Exception as e:
                logger.error(f"Error retrying webhook {attempt.notification_id}: {str(e)}")
                attempt.status = "failed"
                db.commit()
                
    except Exception as e:
        logger.error(f"Error in retry_failed_webhooks: {str(e)}")
    finally:
        db.close()

def get_webhook_statistics(days: int = 30):
    """Get webhook processing statistics"""
    db = SessionLocal()
    try:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        events = db.query(WebhookEvent).filter(
            WebhookEvent.created_at >= cutoff_date
        ).all()
        
        attempts = db.query(WebhookAttempt).filter(
            WebhookAttempt.created_at >= cutoff_date
        ).all()
        
        stats = {
            "total_events": len(events),
            "total_attempts": len(attempts),
            "successful_attempts": len([a for a in attempts if a.status == "success"]),
            "failed_attempts": len([a for a in attempts if a.status == "failed"]),
            "retry_attempts": len([a for a in attempts if a.status == "retry"]),
            "notification_types": {},
            "daily_breakdown": {}
        }
        
        # Notification type breakdown
        for event in events:
            event_type = event.notification_type
            if event_type not in stats["notification_types"]:
                stats["notification_types"][event_type] = 0
            stats["notification_types"][event_type] += 1
        
        # Daily breakdown
        for event in events:
            date_str = event.created_at.strftime("%Y-%m-%d")
            if date_str not in stats["daily_breakdown"]:
                stats["daily_breakdown"][date_str] = 0
            stats["daily_breakdown"][date_str] += 1
        
        return stats
    except Exception as e:
        logger.error(f"Error getting webhook statistics: {str(e)}")
        return {}
    finally:
        db.close() 