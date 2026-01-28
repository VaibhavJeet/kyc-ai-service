"""
TrustVault Verification Model
Stores verification requests and results
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Float, Integer, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class VerificationDecision(str, enum.Enum):
    AUTO_VERIFIED = "auto_verified"
    MANUAL_REVIEW = "manual_review"
    REJECTED = "rejected"
    PENDING = "pending"


class VerificationType(str, enum.Enum):
    FACE = "face"
    LIVENESS = "liveness"
    DOCUMENT = "document"
    KYC = "kyc"  # Full KYC (face + liveness + document)
    BUSINESS = "business"


class Verification(Base):
    """
    Main verification record.
    Stores the verification request and final results.
    """
    __tablename__ = "verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)

    # External reference (client's reference ID)
    external_id = Column(String(255), nullable=True, index=True)

    # Type of verification
    verification_type = Column(String(20), default=VerificationType.KYC.value)

    # Status
    status = Column(String(20), default=VerificationStatus.PENDING.value, index=True)
    decision = Column(String(20), default=VerificationDecision.PENDING.value, index=True)

    # Trust Score
    trust_score = Column(Float, nullable=True)  # 0-100
    confidence = Column(String(20), nullable=True)  # high, medium, low

    # Face verification results
    face_match = Column(Boolean, nullable=True)
    face_similarity = Column(Float, nullable=True)  # 0-1

    # Liveness results
    is_live = Column(Boolean, nullable=True)
    liveness_score = Column(Float, nullable=True)  # 0-1

    # Document results
    document_type = Column(String(50), nullable=True)  # aadhaar, pan, passport, etc.
    document_number = Column(String(100), nullable=True)  # Encrypted
    extracted_name = Column(String(255), nullable=True)
    extracted_dob = Column(String(20), nullable=True)
    ocr_confidence = Column(Float, nullable=True)  # 0-100

    # Detailed results (JSON)
    results = Column(JSON, default=dict)
    # Stores full breakdown, flags, reasons, etc.

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_fingerprint = Column(String(255), nullable=True)

    # Processing info
    processing_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="verifications")
    images = relationship("VerificationImage", back_populates="verification", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Verification {self.id[:8]} ({self.status})>"

    def to_dict(self, include_sensitive: bool = False):
        result = {
            "id": self.id,
            "external_id": self.external_id,
            "type": self.verification_type,
            "status": self.status,
            "decision": self.decision,
            "trust_score": self.trust_score,
            "confidence": self.confidence,
            "face_match": self.face_match,
            "face_similarity": self.face_similarity,
            "is_live": self.is_live,
            "liveness_score": self.liveness_score,
            "document_type": self.document_type,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

        if include_sensitive:
            result.update({
                "document_number": self.document_number,
                "extracted_name": self.extracted_name,
                "extracted_dob": self.extracted_dob,
                "results": self.results,
            })

        return result


class VerificationImage(Base):
    """
    Stores references to verification images.
    Actual images can be stored in S3/local storage.
    """
    __tablename__ = "verification_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    verification_id = Column(String(36), ForeignKey("verifications.id"), nullable=False, index=True)

    # Image type
    image_type = Column(String(20), nullable=False)  # selfie, document_front, document_back

    # Storage
    storage_path = Column(String(500), nullable=True)  # Path in S3 or local storage
    storage_backend = Column(String(20), default="local")  # local, s3

    # Image metadata
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Hash for deduplication
    file_hash = Column(String(64), nullable=True, index=True)

    # Face embedding hash (for duplicate detection)
    embedding_hash = Column(String(64), nullable=True, index=True)
    fuzzy_hashes = Column(JSON, default=list)  # Multiple fuzzy hashes

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete for compliance

    # Relationships
    verification = relationship("Verification", back_populates="images")

    def __repr__(self):
        return f"<VerificationImage {self.image_type} for {self.verification_id[:8]}>"
