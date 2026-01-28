"""
TrustVault Webhook Model
Webhook configurations and event logs
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Webhook(Base):
    """
    Webhook configuration for a tenant.
    Tenants can configure multiple webhooks for different events.
    """
    __tablename__ = "webhooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Webhook config
    name = Column(String(255), nullable=True)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)  # For HMAC signature

    # Events to subscribe to
    events = Column(JSON, default=list)
    # Example: ["verification.completed", "verification.failed", "verification.manual_review"]

    # Headers to include
    headers = Column(JSON, default=dict)
    # Example: {"X-Custom-Header": "value"}

    # Retry config
    retry_count = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)

    # Status
    is_active = Column(Boolean, default=True)

    # Stats
    total_sent = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    last_sent_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="webhooks")
    events_log = relationship("WebhookEvent", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Webhook {self.name or self.url[:30]}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": self.events,
            "is_active": self.is_active,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "last_sent_at": self.last_sent_at.isoformat() if self.last_sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WebhookEvent(Base):
    """
    Log of webhook delivery attempts.
    Useful for debugging and retry logic.
    """
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id = Column(String(36), ForeignKey("webhooks.id"), nullable=False, index=True)

    # Event details
    event_type = Column(String(100), nullable=False)  # e.g., "verification.completed"
    payload = Column(JSON, nullable=False)

    # Related entity
    entity_type = Column(String(50), nullable=True)  # e.g., "verification"
    entity_id = Column(String(36), nullable=True)

    # Delivery status
    status = Column(String(20), default="pending")  # pending, sent, failed
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    # Response info
    response_status = Column(Integer, nullable=True)  # HTTP status code
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Error info
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="events_log")

    def __repr__(self):
        return f"<WebhookEvent {self.event_type} ({self.status})>"
