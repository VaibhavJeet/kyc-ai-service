"""
TrustVault Python SDK - Data Models
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class FaceVerifyRequest:
    selfie_base64: str
    document_base64: str


@dataclass
class FaceVerifyResponse:
    match: bool
    similarity: float
    threshold: float
    confidence: str
    face_detected_selfie: bool = True
    face_detected_document: bool = True
    recommendation: Optional[str] = None


@dataclass
class KYCVerifyRequest:
    selfie_base64: str
    document_base64: str
    document_type: Optional[str] = None
    expected_name: Optional[str] = None
    expected_dob: Optional[str] = None


@dataclass
class KYCVerifyResponse:
    face_match: bool
    face_similarity: float
    is_live: bool
    liveness_score: float
    trust_score: float
    decision: str
    confidence: str
    overall_pass: bool
    reasons: List[str] = field(default_factory=list)
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    extracted_name: Optional[str] = None
    extracted_dob: Optional[str] = None


@dataclass
class TrustScoreRequest:
    face_similarity: float
    liveness_score: float
    liveness_passed: bool
    document_confidence: float
    ocr_confidence: float
    document_type_verified: bool = False
    dob: Optional[str] = None
    estimated_age: Optional[int] = None
    is_unique_document: bool = True
    is_unique_face: bool = True
    fuzzy_match_found: bool = False
    device_fingerprint: Optional[str] = None
    previous_rejections: int = 0
    
    def dict(self) -> Dict[str, Any]:
        return {
            "face_similarity": self.face_similarity,
            "liveness_score": self.liveness_score,
            "liveness_passed": self.liveness_passed,
            "document_confidence": self.document_confidence,
            "ocr_confidence": self.ocr_confidence,
            "document_type_verified": self.document_type_verified,
            "dob": self.dob,
            "estimated_age": self.estimated_age,
            "is_unique_document": self.is_unique_document,
            "is_unique_face": self.is_unique_face,
            "fuzzy_match_found": self.fuzzy_match_found,
            "device_fingerprint": self.device_fingerprint,
            "previous_rejections": self.previous_rejections,
        }


@dataclass
class TrustScoreResponse:
    score: float
    decision: str
    confidence: str
    breakdown: Dict[str, float] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)


@dataclass
class BusinessVerifyRequest:
    business_name: str
    phone_number: Optional[str] = None
    registration_number: Optional[str] = None
    website: Optional[str] = None


@dataclass
class BusinessVerifyResponse:
    is_verified: bool
    business_name: str
    verification_status: str
    risk_level: str
    risk_score: float = 50.0
    message: Optional[str] = None
    matched_business: Optional[Dict[str, Any]] = None
