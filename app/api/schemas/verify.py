"""
TrustVault Verification Schemas
Pydantic models for verification endpoints
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============= Face Verification =============

class FaceVerifyRequest(BaseModel):
    selfie_base64: str = Field(..., description="Base64 encoded selfie image")
    document_base64: str = Field(..., description="Base64 encoded document photo")


class FaceVerifyResponse(BaseModel):
    match: bool
    similarity: float = Field(..., ge=0, le=1)
    threshold: float
    confidence: str  # high, medium, low
    recommendation: str  # AUTO_VERIFY, MANUAL_REVIEW, REJECT
    face_detected_selfie: bool
    face_detected_document: bool
    success: bool = True
    error: Optional[str] = None


# ============= Liveness Detection =============

class LivenessRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded face image")
    left_eye: Optional[List[int]] = Field(None, description="Left eye coordinates [x, y]")
    right_eye: Optional[List[int]] = Field(None, description="Right eye coordinates [x, y]")


class LivenessResponse(BaseModel):
    is_live: bool
    score: float = Field(..., ge=0, le=1)
    details: Optional[Dict[str, float]] = None
    success: bool = True
    error: Optional[str] = None


# ============= Document Verification =============

class DocumentVerifyRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded document image")
    document_type: Optional[str] = Field("auto", description="Expected document type (aadhaar, pan, passport, auto)")


class DocumentVerifyResponse(BaseModel):
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    raw_text: str = ""
    confidence: float = Field(..., ge=0, le=100)
    success: bool = True
    error: Optional[str] = None


# ============= Full KYC Verification =============

class KYCVerifyRequest(BaseModel):
    selfie_base64: str = Field(..., description="Base64 encoded selfie")
    document_base64: str = Field(..., description="Base64 encoded ID document")
    document_type: Optional[str] = Field(None, description="Expected document type")
    expected_name: Optional[str] = Field(None, description="Expected name for matching")
    expected_dob: Optional[str] = Field(None, description="Expected DOB for matching")


class KYCVerifyResponse(BaseModel):
    # Face verification
    face_match: bool
    face_similarity: float

    # Liveness
    is_live: bool
    liveness_score: float

    # Document
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    extracted_name: Optional[str] = None
    extracted_dob: Optional[str] = None

    # Trust score
    trust_score: float
    decision: str  # auto_verified, manual_review, rejected
    confidence: str  # high, medium, low

    # Overall
    overall_pass: bool
    reasons: List[str] = []

    success: bool = True
    error: Optional[str] = None


# ============= Business Verification (Reverse KYC) =============

class BusinessVerifyRequest(BaseModel):
    business_name: str = Field(..., description="Name of the business to verify")
    phone_number: Optional[str] = Field(None, description="Phone number claiming to be from business")
    registration_number: Optional[str] = Field(None, description="Business registration number")
    website: Optional[str] = Field(None, description="Business website")
    email_domain: Optional[str] = Field(None, description="Email domain to verify")


class BusinessVerifyResponse(BaseModel):
    is_verified: bool
    business_name: str
    verification_status: str  # verified, pending, failed, unknown
    risk_level: str  # low, medium, high, unknown
    details: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
