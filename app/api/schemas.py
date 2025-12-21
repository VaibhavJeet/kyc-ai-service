"""
API Schemas - Pydantic models for request/response validation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============= Chat Schemas =============

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Conversation history")


class ChatResponse(BaseModel):
    response: str
    success: bool = True
    error: Optional[str] = None


# ============= Content Generation Schemas =============

class TitleRequest(BaseModel):
    description: str = Field(..., description="Task description to generate title from")


class TitleResponse(BaseModel):
    title: str
    success: bool = True


class DescriptionRequest(BaseModel):
    title: str = Field(..., description="Task title")
    context: Optional[str] = Field(default="", description="Additional context")


class DescriptionResponse(BaseModel):
    description: str
    success: bool = True


class BudgetRequest(BaseModel):
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    category: Optional[str] = Field(default="", description="Task category")
    currency: Optional[str] = Field(default="INR", description="Currency code")


class BudgetResponse(BaseModel):
    min: float
    max: float
    recommended: float
    currency: str = "INR"
    success: bool = True


# ============= KYC Schemas =============

class FaceCompareRequest(BaseModel):
    selfie_base64: str = Field(..., description="Base64 encoded selfie image")
    document_base64: str = Field(..., description="Base64 encoded document photo")


class FaceCompareResponse(BaseModel):
    match: bool
    similarity: float
    threshold: float
    success: bool = True
    error: Optional[str] = None


class LivenessCheckResponse(BaseModel):
    is_live: bool
    score: float
    details: Optional[Dict[str, float]] = None
    success: bool = True
    error: Optional[str] = None


class DocumentOCRRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded document image")
    document_type: Optional[str] = Field(default="auto", description="Document type hint")


class DocumentOCRResponse(BaseModel):
    text: str
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    confidence: float
    success: bool = True
    error: Optional[str] = None


class KYCVerifyRequest(BaseModel):
    selfie_base64: str = Field(..., description="Base64 encoded selfie")
    document_base64: str = Field(..., description="Base64 encoded ID document")
    expected_name: Optional[str] = Field(default=None, description="Expected name for verification")
    expected_dob: Optional[str] = Field(default=None, description="Expected DOB for verification")


class KYCVerifyResponse(BaseModel):
    face_match: bool
    face_similarity: float
    liveness_score: float
    is_live: bool
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    name_match: Optional[bool] = None
    dob_match: Optional[bool] = None
    overall_pass: bool
    confidence: float
    success: bool = True
    error: Optional[str] = None


# ============= Anti-Spoof Schemas =============

class AntiSpoofRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded face image")
    left_eye: Optional[List[int]] = Field(default=None, description="Left eye [x, y] coordinates")
    right_eye: Optional[List[int]] = Field(default=None, description="Right eye [x, y] coordinates")


class AntiSpoofResponse(BaseModel):
    is_live: bool
    confidence: float
    reason: str
    scores: Dict[str, float]
    success: bool = True
    error: Optional[str] = None


# ============= Identity Scoring Schemas =============

class IdentityScoreRequest(BaseModel):
    face_similarity: float = Field(..., description="Face match similarity 0-1")
    liveness_score: float = Field(..., description="Liveness confidence 0-1")
    liveness_passed: bool = Field(..., description="Whether liveness check passed")
    document_confidence: float = Field(..., description="Document type confidence 0-1")
    ocr_confidence: float = Field(..., description="OCR confidence 0-100")
    document_type_verified: bool = Field(default=True, description="Document type matches expected")
    dob: Optional[str] = Field(default=None, description="Date of birth from document")
    estimated_age: Optional[int] = Field(default=None, description="Estimated age from face")
    is_unique_document: bool = Field(default=True, description="Document not used by another user")
    is_unique_face: bool = Field(default=True, description="Face not matched to another user")
    fuzzy_match_found: bool = Field(default=False, description="Fuzzy hash matched")
    device_fingerprint: Optional[str] = Field(default=None, description="Device fingerprint")
    previous_rejections: int = Field(default=0, description="Number of previous rejections")


class IdentityScoreResponse(BaseModel):
    score: float  # 0-100
    decision: str  # auto_verified, manual_review, rejected
    confidence: str  # high, medium, low
    breakdown: Dict[str, float]
    reasons: List[str]
    flags: List[str]
    success: bool = True
    error: Optional[str] = None


# ============= Hash Generation Schemas =============

class GenerateHashRequest(BaseModel):
    embedding: List[float] = Field(..., description="Face embedding vector")


class GenerateHashResponse(BaseModel):
    embedding_hash: str
    fuzzy_hashes: List[str]
    success: bool = True


class CompareHashesRequest(BaseModel):
    hashes1: List[str] = Field(..., description="First set of fuzzy hashes")
    hashes2: List[str] = Field(..., description="Second set of fuzzy hashes")


class CompareHashesResponse(BaseModel):
    matching_levels: int
    confidence: float
    is_match: bool
    success: bool = True


# ============= Complete Verification Schema =============

class CompleteVerifyRequest(BaseModel):
    document_base64: str = Field(..., description="Base64 encoded ID document")
    selfie_base64: str = Field(..., description="Base64 encoded selfie")
    expected_document_type: Optional[str] = Field(default=None, description="Expected document type")
    dob: Optional[str] = Field(default=None, description="Expected date of birth")
    device_fingerprint: Optional[str] = Field(default=None, description="Device fingerprint")


class CompleteVerifyResponse(BaseModel):
    score: float
    decision: str
    confidence: str
    face_similarity: float
    is_face_match: bool
    is_live: bool
    liveness_confidence: float
    document_type: Optional[str] = None
    document_fields: Dict[str, Any] = {}
    estimated_age: Optional[int] = None
    age_consistency: Optional[float] = None
    embedding_hash: Optional[str] = None
    fuzzy_hashes: Optional[List[str]] = None
    breakdown: Dict[str, float] = {}
    reasons: List[str] = []
    flags: List[str] = []
    success: bool = True
    error: Optional[str] = None


# ============= Health Schemas =============

class ServiceStatus(BaseModel):
    name: str
    available: bool
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    services: List[ServiceStatus]
    version: str = "1.0.0"
