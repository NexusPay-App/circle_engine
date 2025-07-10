from app.models.wallet import AuditLog
from app.utils.logger import logger
from app.db.session import SessionLocal

def log_audit(event_type: str, event_data: dict):
    logger.info(f"AUDIT: {event_type} - {event_data}")
    db = SessionLocal()
    try:
        audit = AuditLog(event_type=event_type, event_data=event_data)
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
    finally:
        db.close()