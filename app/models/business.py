"""
TrustVault Business Verification Model
For Reverse KYC - verifying businesses and callers
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Float, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class BusinessRecord(Base):
    """
    Known business records from various sources.
    Used to verify if a business is legitimate.
    """
    __tablename__ = "business_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Business info
    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255), nullable=True)
    registration_number = Column(String(100), nullable=True, index=True)  # CIN, GSTIN, etc.
    registration_type = Column(String(50), nullable=True)  # cin, gstin, pan, etc.

    # Contact info
    phone_numbers = Column(JSON, default=list)  # List of known phone numbers
    email_domains = Column(JSON, default=list)  # List of known email domains
    websites = Column(JSON, default=list)  # List of known websites

    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    pincode = Column(String(10), nullable=True)

    # Verification status
    is_verified = Column(Boolean, default=False)  # Manually verified
    verification_source = Column(String(100), nullable=True)  # mca, gstn, manual, etc.
    verified_at = Column(DateTime, nullable=True)

    # Trust indicators
    trust_score = Column(Float, default=50.0)  # 0-100
    is_known_scam = Column(Boolean, default=False)
    scam_reports = Column(Integer, default=0)

    # Additional data
    industry = Column(String(100), nullable=True)
    founded_year = Column(Integer, nullable=True)
    employee_count = Column(String(50), nullable=True)
    annual_revenue = Column(String(50), nullable=True)

    # Metadata
    data_source = Column(String(100), nullable=True)  # Where this data came from
    raw_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<BusinessRecord {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "registration_number": self.registration_number,
            "phone_numbers": self.phone_numbers,
            "websites": self.websites,
            "is_verified": self.is_verified,
            "trust_score": self.trust_score,
            "is_known_scam": self.is_known_scam,
            "scam_reports": self.scam_reports,
            "city": self.city,
            "state": self.state,
        }


class BusinessVerification(Base):
    """
    Business verification requests (Reverse KYC).
    When someone wants to verify if a caller/business is legitimate.
    """
    __tablename__ = "business_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # What was checked
    query_type = Column(String(50), nullable=False)  # phone, business_name, registration, website
    query_value = Column(String(500), nullable=False)  # The actual value checked

    # Claimed identity
    claimed_business_name = Column(String(255), nullable=True)
    claimed_phone = Column(String(20), nullable=True)
    claimed_registration = Column(String(100), nullable=True)

    # Match results
    matched_business_id = Column(String(36), ForeignKey("business_records.id"), nullable=True)
    is_match_found = Column(Boolean, default=False)
    match_confidence = Column(Float, nullable=True)  # 0-1

    # Verification result
    is_verified = Column(Boolean, default=False)
    risk_level = Column(String(20), default="unknown")  # low, medium, high, critical, unknown
    risk_score = Column(Float, default=50.0)  # 0-100

    # Reasons
    verification_reasons = Column(JSON, default=list)
    risk_flags = Column(JSON, default=list)

    # Source data used for verification
    sources_checked = Column(JSON, default=list)  # List of data sources checked

    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<BusinessVerification {self.query_type}:{self.query_value[:20]}>"

    def to_dict(self):
        return {
            "id": self.id,
            "query_type": self.query_type,
            "query_value": self.query_value,
            "claimed_business_name": self.claimed_business_name,
            "is_match_found": self.is_match_found,
            "is_verified": self.is_verified,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "verification_reasons": self.verification_reasons,
            "risk_flags": self.risk_flags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
