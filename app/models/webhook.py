from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime

Base = declarative_base()

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(String, nullable=False)
    notification_id = Column(String, nullable=False, unique=True)
    notification_type = Column(String, nullable=False)
    notification_data = Column(JSON, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    version = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_notification_id', 'notification_id'),
        Index('idx_notification_type', 'notification_type'),
        Index('idx_timestamp', 'timestamp'),
    )

class WebhookAttempt(Base):
    __tablename__ = "webhook_attempts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success, failed, retry
    error_message = Column(Text)
    payload = Column(JSON, nullable=False)
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_notification_id_status', 'notification_id', 'status'),
        Index('idx_created_at', 'created_at'),
    )

class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(String, nullable=False, unique=True)
    endpoint_url = Column(String, nullable=False)
    notification_types = Column(JSON, nullable=False)  # Array of notification types
    is_active = Column(String, default="true")  # true, false
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_subscription_id', 'subscription_id'),
        Index('idx_endpoint_url', 'endpoint_url'),
        Index('idx_is_active', 'is_active'),
    )

class WebhookSignature(Base):
    __tablename__ = "webhook_signatures"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String, nullable=False, unique=True)
    signature = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    verification_status = Column(String, nullable=False)  # verified, failed, pending
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_signature_notification_id', 'notification_id'),
        Index('idx_verification_status', 'verification_status'),
    ) 