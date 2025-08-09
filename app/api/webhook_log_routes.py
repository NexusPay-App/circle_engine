from fastapi import APIRouter, HTTPException
from app.models.webhook_log import WebhookLog
from app.db.session import SessionLocal

router = APIRouter()

@router.get("/webhook-logs")
def get_webhook_logs(limit: int = 100):
    db = SessionLocal()
    try:
        logs = db.query(WebhookLog).order_by(WebhookLog.created_at.desc()).limit(limit).all()
        return {"logs": [log.__dict__ for log in logs]}
    finally:
        db.close()


@router.get("/webhook-logs/resend/{log_id}")
async def resend_webhook(log_id: int):
    db = SessionLocal()
    try:
        log = db.query(WebhookLog).filter(WebhookLog.id == log_id).first()
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        
        # Re-process the webhook event
        from app.services.webhook_service import webhook_service
        await webhook_service._process_event(log.payload, log.event_type, log.notification_id)
        return {"status": "resent"}
    finally:
        db.close()