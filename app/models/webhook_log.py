from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base 
from datetime import datetime

Base = declarative_base()   

class WebhookLog(Base):
    __tablename__ = 'webhook_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(Datetime, default=datetime.utcnow)
    processed_at = Column(Datetime)
    error_message = Column(String, nullable=True)

    def __repr__(self):
        return f"<WebhookLog(id={self.id}, notification_id={self.notification_id}, event_type={self.event_type}, status={self.status}, created_at={self.created_at}, processed_at={self.processed_at}, error_message={self.error_message})>"