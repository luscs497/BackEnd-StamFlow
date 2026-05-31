from sqlalchemy import Column, BigInteger, String, DateTime, JSON, Enum, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class WebhookStatus(str, enum.Enum):
    processing = "processing"
    success = "success"
    ignored = "ignored"
    error = "error"

class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    topic = Column(String(50), nullable=False, index=True) 
    resource_id = Column(String(100), nullable=True, index=True) 
    payload = Column(JSON)
    status = Column(Enum(WebhookStatus, name="webhook_status", native_enum=True), default=WebhookStatus.processing)
    error_message = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("topic", "resource_id", "status", name="uq_webhook_logs_topic_resource_id"),
    )