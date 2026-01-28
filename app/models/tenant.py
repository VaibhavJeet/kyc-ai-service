"""
TrustVault Tenant Model
Multi-tenant support - each organization is a tenant
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Tenant(Base):
    """
    Tenant/Organization model for multi-tenancy.
    Each tenant has isolated data and API keys.
    """
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic info
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)

    # Company details
    company_name = Column(String(255), nullable=True)
    company_website = Column(String(500), nullable=True)
    company_address = Column(Text, nullable=True)

    # Subscription
    plan = Column(String(50), default="free")  # free, growth, business, enterprise
    plan_started_at = Column(DateTime, nullable=True)
    plan_expires_at = Column(DateTime, nullable=True)

    # Limits
    monthly_verification_limit = Column(Integer, default=100)
    verifications_this_month = Column(Integer, default=0)

    # Custom settings
    settings = Column(JSON, default=dict)
    # Example settings:
    # {
    #   "face_match_threshold": 0.85,
    #   "auto_approve_threshold": 0.90,
    #   "webhook_secret": "...",
    #   "allowed_document_types": ["aadhaar", "pan", "passport"]
    # }

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Email/business verified

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="tenant", cascade="all, delete-orphan")
    webhooks = relationship("Webhook", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.name} ({self.slug})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "email": self.email,
            "plan": self.plan,
            "monthly_limit": self.monthly_verification_limit,
            "verifications_used": self.verifications_this_month,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
