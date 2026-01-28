"""
TrustVault API Key Model
API keys for authentication
"""

import uuid
import secrets
import hashlib
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"tv_{'live' if True else 'test'}_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(key.encode()).hexdigest()


class APIKey(Base):
    """
    API Key model for tenant authentication.
    Keys are hashed before storage.
    """
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # Key info (key_hash stores the hashed key, key_prefix for identification)
    name = Column(String(255), nullable=False)  # e.g., "Production Key", "Test Key"
    key_prefix = Column(String(20), nullable=False)  # First 8 chars for identification
    key_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Type
    key_type = Column(String(20), default="live")  # live, test

    # Permissions (which endpoints can this key access)
    permissions = Column(JSON, default=list)
    # Example: ["verify:face", "verify:document", "trust:score"]
    # Empty list = all permissions

    # Rate limiting
    rate_limit = Column(Integer, default=100)  # requests per minute

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)

    # IP whitelist (optional)
    allowed_ips = Column(JSON, default=list)  # Empty = all IPs allowed

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # None = never expires
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.name} ({self.key_prefix}...)>"

    @classmethod
    def create(cls, tenant_id: str, name: str, key_type: str = "live", **kwargs):
        """Create a new API key and return both the model and the raw key"""
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        key_prefix = raw_key[:12]  # "tv_live_xxxx"

        api_key = cls(
            tenant_id=tenant_id,
            name=name,
            key_type=key_type,
            key_prefix=key_prefix,
            key_hash=key_hash,
            **kwargs
        )

        return api_key, raw_key

    @classmethod
    def verify(cls, raw_key: str) -> str:
        """Return hash for verification"""
        return hash_api_key(raw_key)

    def to_dict(self, include_key: bool = False):
        result = {
            "id": self.id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "key_type": self.key_type,
            "permissions": self.permissions,
            "rate_limit": self.rate_limit,
            "is_active": self.is_active,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "total_requests": self.total_requests,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
        return result
