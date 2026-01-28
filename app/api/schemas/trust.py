"""
TrustVault Trust Score Schemas
Pydantic models for trust score endpoints
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class TrustScoreRequest(BaseModel):
    """Request model for calculating trust score"""
    face_similarity: float = Field(..., ge=0, le=1, description="Face match similarity 0-1")
    liveness_score: float = Field(..., ge=0, le=1, description="Liveness confidence 0-1")
    liveness_passed: bool = Field(..., description="Whether liveness check passed")
    document_confidence: float = Field(..., ge=0, le=1, description="Document type confidence 0-1")
    ocr_confidence: float = Field(0, ge=0, le=100, description="OCR confidence 0-100")
    document_type_verified: bool = Field(True, description="Document type matches expected")
    dob: Optional[str] = Field(None, description="Date of birth from document (YYYY-MM-DD)")
    estimated_age: Optional[int] = Field(None, description="Estimated age from face")
    is_unique_document: bool = Field(True, description="Document not used by another user")
    is_unique_face: bool = Field(True, description="Face not matched to another user")
    fuzzy_match_found: bool = Field(False, description="Fuzzy hash matched (potential duplicate)")
    device_fingerprint: Optional[str] = Field(None, description="Device fingerprint for risk assessment")
    previous_rejections: int = Field(0, ge=0, description="Number of previous KYC rejections")


class TrustScoreResponse(BaseModel):
    """Response model for trust score"""
    score: float = Field(..., ge=0, le=100, description="Trust score 0-100")
    decision: str  # auto_verified, manual_review, rejected
    confidence: str  # high, medium, low
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Score breakdown by factor")
    reasons: List[str] = Field(default_factory=list, description="Human-readable reasons")
    flags: List[str] = Field(default_factory=list, description="Risk flags")
    success: bool = True
    error: Optional[str] = None


class TrustDecisionRequest(BaseModel):
    """Request model for getting decision from score"""
    score: float = Field(..., ge=0, le=100, description="Trust score")
    custom_thresholds: Optional[Dict[str, float]] = Field(
        None,
        description="Custom thresholds (auto_verify, manual_review, reject)"
    )


class TrustDecisionResponse(BaseModel):
    """Response model for trust decision"""
    decision: str  # auto_verified, manual_review, rejected
    confidence: str  # high, medium, low
    recommended_action: str
    next_steps: List[str] = Field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
