"""
TrustVault Protection Schemas
Pydantic models for protection endpoints
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============= Scam Detection =============

class ScamCheckRequest(BaseModel):
    phone_number: Optional[str] = Field(None, description="Phone number to check")
    email: Optional[str] = Field(None, description="Email address to check")
    business_name: Optional[str] = Field(None, description="Business name to check")
    url: Optional[str] = Field(None, description="URL to check")


class ScamCheckResponse(BaseModel):
    is_suspicious: bool
    risk_level: str  # low, medium, high, unknown
    risk_score: float = Field(0, ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    reports_count: int = 0
    first_reported: Optional[datetime] = None
    message: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


# ============= Alert System =============

class AlertRequest(BaseModel):
    alert_type: str = Field(..., description="Type of alert (suspicious_call, high_value_transaction, etc.)")
    recipient_phone: Optional[str] = Field(None, description="Phone number to alert")
    recipient_email: Optional[str] = Field(None, description="Email to alert")
    message: str = Field(..., description="Alert message")
    priority: str = Field("normal", description="Alert priority (low, normal, high, urgent)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class AlertResponse(BaseModel):
    alert_sent: bool
    alert_id: Optional[str] = None
    delivery_status: Optional[str] = None  # pending, sent, failed
    message: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


# ============= Blocklist =============

class BlocklistCheckRequest(BaseModel):
    identifier: str = Field(..., description="Identifier to check (phone, email, hash, etc.)")
    identifier_type: str = Field(..., description="Type of identifier (phone, email, face_hash, document_number)")


class BlocklistCheckResponse(BaseModel):
    is_blocked: bool
    reason: Optional[str] = None
    blocked_at: Optional[datetime] = None
    severity: Optional[str] = None  # low, medium, high, critical
    message: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
