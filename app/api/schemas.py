"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


# ============= Face Verification =============


class FaceCompareRequest(BaseModel):
    """Request to compare two face images"""

    document_image: str = Field(..., description="Base64 encoded document image")
    selfie_image: str = Field(..., description="Base64 encoded selfie image")


class FaceCompareResponse(BaseModel):
    """Response from face comparison"""

    similarity: float = Field(..., ge=0, le=1, description="Cosine similarity score")
    is_match: bool = Field(..., description="Whether faces match")
    confidence: str = Field(..., description="Confidence level: high, medium, low")
    document_age: Optional[int] = Field(None, description="Estimated age from document photo")
    selfie_age: Optional[int] = Field(None, description="Estimated age from selfie")
    embedding_hash: Optional[str] = Field(None, description="Privacy-preserving hash for deduplication")
    fuzzy_hashes: Optional[List[str]] = Field(None, description="Fuzzy hashes for appearance-tolerant matching")
    error: Optional[str] = None


class FaceEmbeddingRequest(BaseModel):
    """Request to extract face embedding"""

    image: str = Field(..., description="Base64 encoded image")


class FaceEmbeddingResponse(BaseModel):
    """Response with face embedding"""

    embedding: Optional[List[float]] = Field(None, description="512-dim face embedding")
    embedding_hash: Optional[str] = Field(None, description="SHA256 hash of embedding")
    fuzzy_hashes: Optional[List[str]] = Field(None, description="Fuzzy hashes")
    age: Optional[int] = Field(None, description="Estimated age")
    gender: Optional[str] = Field(None, description="Detected gender: M or F")
    det_score: Optional[float] = Field(None, description="Face detection confidence")
    error: Optional[str] = None


# ============= Liveness Detection =============


class LivenessRequest(BaseModel):
    """Request for liveness detection"""

    image: str = Field(..., description="Base64 encoded selfie image")


class LivenessResponse(BaseModel):
    """Response from liveness detection"""

    is_live: bool = Field(..., description="Whether the image is of a live person")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    scores: Dict[str, float] = Field(..., description="Individual check scores")
    reason: str = Field(..., description="Explanation of result")
    error: Optional[str] = None


# ============= Document Verification =============


class DocumentOCRRequest(BaseModel):
    """Request for document OCR"""

    image: str = Field(..., description="Base64 encoded document image")
    expected_type: Optional[str] = Field(
        None, description="Expected document type: aadhaar, pan, passport, etc."
    )


class DocumentOCRResponse(BaseModel):
    """Response from document OCR"""

    document_type: Optional[str] = Field(None, description="Detected document type")
    type_confidence: float = Field(0, description="Document type detection confidence")
    type_match: bool = Field(False, description="Whether detected type matches expected")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Extracted fields")
    raw_text: Optional[str] = Field(None, description="Raw OCR text")
    ocr_confidence: float = Field(0, description="OCR confidence score")
    error: Optional[str] = None


# ============= Unified Verification =============


class UnifiedVerifyRequest(BaseModel):
    """Request for complete KYC verification"""

    document_image: str = Field(..., description="Base64 encoded document image")
    selfie_image: str = Field(..., description="Base64 encoded selfie image")
    expected_document_type: Optional[str] = Field(None, description="Expected document type")
    dob: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    device_fingerprint: Optional[str] = Field(None, description="Device fingerprint hash")
    ip_address: Optional[str] = Field(None, description="Client IP address")


class UnifiedVerifyResponse(BaseModel):
    """Response from complete KYC verification"""

    # Overall result
    score: float = Field(..., ge=0, le=100, description="Identity confidence score")
    decision: str = Field(..., description="Decision: auto_verified, manual_review, rejected")
    confidence: str = Field(..., description="Confidence level: high, medium, low")

    # Breakdown
    breakdown: Dict[str, float] = Field(..., description="Score breakdown by category")
    reasons: List[str] = Field(..., description="Human-readable reasons")
    flags: List[str] = Field(..., description="Warning flags")

    # Face verification
    face_similarity: float = Field(..., description="Face match score")
    is_face_match: bool = Field(..., description="Whether faces match")

    # Liveness
    is_live: bool = Field(..., description="Liveness check result")
    liveness_confidence: float = Field(..., description="Liveness confidence")

    # Document
    document_type: Optional[str] = Field(None, description="Detected document type")
    document_fields: Dict[str, Any] = Field(default_factory=dict, description="Extracted fields")

    # Age
    estimated_age: Optional[int] = Field(None, description="Estimated age from selfie")
    age_consistency: Optional[float] = Field(None, description="Age-DOB consistency score")

    # Deduplication
    embedding_hash: Optional[str] = Field(None, description="Face embedding hash")
    fuzzy_hashes: Optional[List[str]] = Field(None, description="Fuzzy hashes")

    error: Optional[str] = None


# ============= Identity Scoring =============


class IdentityScoreRequest(BaseModel):
    """Request for identity scoring calculation"""

    face_similarity: float = Field(..., ge=0, le=1, description="Face match score")
    liveness_score: float = Field(0.5, ge=0, le=1, description="Liveness score")
    liveness_passed: bool = Field(False, description="Whether liveness passed")
    document_confidence: float = Field(0.5, ge=0, le=1, description="Document confidence")
    ocr_confidence: float = Field(0.5, ge=0, le=1, description="OCR confidence")
    document_type_verified: bool = Field(False, description="Document type matched")
    dob: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    estimated_age: Optional[int] = Field(None, description="Estimated age")
    is_unique_document: bool = Field(True, description="No duplicate document")
    is_unique_face: bool = Field(True, description="No duplicate face")
    fuzzy_match_found: bool = Field(False, description="Fuzzy hash match found")
    device_fingerprint: Optional[str] = Field(None, description="Device fingerprint")
    previous_rejections: int = Field(0, ge=0, description="Number of previous rejections")


class IdentityScoreResponse(BaseModel):
    """Response from identity scoring"""

    score: float = Field(..., ge=0, le=100, description="Identity confidence score")
    decision: str = Field(..., description="Decision: auto_verified, manual_review, rejected")
    confidence: str = Field(..., description="Confidence level: high, medium, low")
    breakdown: Dict[str, float] = Field(..., description="Score breakdown")
    reasons: List[str] = Field(..., description="Human-readable reasons")
    flags: List[str] = Field(..., description="Warning flags")


# ============= Health Check =============


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    version: str = Field(..., description="Service version")
    models: Dict[str, bool] = Field(..., description="Model initialization status")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
