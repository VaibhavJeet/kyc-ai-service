"""
TrustVault Audit Log Model
Compliance and security audit trail
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class AuditLog(Base):
    """
    Audit log for compliance and security.
    Tracks all significant actions in the system.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

    # Actor
    actor_type = Column(String(50), nullable=False)  # user, api_key, system, admin
    actor_id = Column(String(36), nullable=True)  # API key ID or user ID
    actor_ip = Column(String(45), nullable=True)
    actor_user_agent = Column(String(500), nullable=True)

    # Action
    action = Column(String(100), nullable=False, index=True)
    # Examples:
    # - verification.created
    # - verification.completed
    # - api_key.created
    # - api_key.revoked
    # - webhook.created
    # - settings.updated
    # - tenant.plan_changed

    # Resource
    resource_type = Column(String(50), nullable=True)  # verification, api_key, webhook, tenant
    resource_id = Column(String(36), nullable=True)

    # Details
    description = Column(Text, nullable=True)
    old_value = Column(JSON, nullable=True)  # For updates
    new_value = Column(JSON, nullable=True)  # For updates
    metadata = Column(JSON, default=dict)

    # Status
    status = Column(String(20), default="success")  # success, failure

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} at {self.created_at}>"

    def to_dict(self):
        return {
            "id": self.id,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "actor_ip": self.actor_ip,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Helper function to create audit log entries
def create_audit_log(
    db,
    action: str,
    tenant_id: str = None,
    actor_type: str = "system",
    actor_id: str = None,
    actor_ip: str = None,
    resource_type: str = None,
    resource_id: str = None,
    description: str = None,
    old_value: dict = None,
    new_value: dict = None,
    metadata: dict = None,
    status: str = "success",
):
    """
    Helper function to create audit log entries.

    Usage:
        create_audit_log(
            db,
            action="verification.created",
            tenant_id=tenant.id,
            actor_type="api_key",
            actor_id=api_key.id,
            resource_type="verification",
            resource_id=verification.id,
        )
    """
    log = AuditLog(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_ip=actor_ip,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        old_value=old_value,
        new_value=new_value,
        metadata=metadata or {},
        status=status,
    )
    db.add(log)
    db.commit()
    return log
