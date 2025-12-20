"""
Unified Identity Scoring Service
Combines all verification signals into a single confidence score
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime
from dataclasses import dataclass
import structlog

from ..config import settings

logger = structlog.get_logger()


@dataclass
class VerificationInput:
    """Input data for identity verification scoring"""

    # Face matching (0-1)
    face_similarity: float = 0.0
    face_match_source: str = "unknown"  # "arcface", "mobilefacenet", "fallback"

    # Liveness (0-1)
    liveness_score: float = 0.0
    liveness_passed: bool = False

    # Document verification (0-1)
    document_confidence: float = 0.0
    document_type_verified: bool = False
    ocr_confidence: float = 0.0

    # Age consistency
    dob: Optional[date] = None
    estimated_age: Optional[int] = None

    # Uniqueness
    is_unique_document: bool = True
    is_unique_face: bool = True
    fuzzy_match_found: bool = False

    # Risk signals
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    geo_location: Optional[str] = None
    submission_time: Optional[datetime] = None

    # Previous attempts
    previous_rejections: int = 0
    previous_manual_reviews: int = 0


@dataclass
class ScoringResult:
    """Result of identity verification scoring"""

    score: float  # 0-100
    decision: str  # "auto_verified", "manual_review", "rejected"
    confidence: str  # "high", "medium", "low"
    breakdown: Dict[str, float]
    reasons: List[str]
    flags: List[str]


class IdentityScoringService:
    """
    Unified identity verification scoring.

    Combines multiple signals with weighted scoring:
    - Face similarity (30%)
    - Liveness verification (20%)
    - Document verification (20%)
    - Age consistency (10%)
    - Uniqueness (15%)
    - Risk signals (5%)
    """

    # Scoring weights
    WEIGHTS = {
        "face": 0.30,
        "liveness": 0.20,
        "document": 0.20,
        "age": 0.10,
        "uniqueness": 0.15,
        "risk": 0.05,
    }

    # Decision thresholds
    AUTO_VERIFY_THRESHOLD = 85
    MANUAL_REVIEW_THRESHOLD = 60
    HIGH_CONFIDENCE_THRESHOLD = 90
    MEDIUM_CONFIDENCE_THRESHOLD = 70

    def __init__(self):
        self._initialized = True

    def calculate_age_from_dob(self, dob: date) -> int:
        """Calculate age from date of birth"""
        today = date.today()
        age = today.year - dob.year
        if today.month < dob.month or (today.month == dob.month and today.day < dob.day):
            age -= 1
        return age

    def calculate_age_consistency(
        self, dob: Optional[date], estimated_age: Optional[int]
    ) -> float:
        """
        Calculate age consistency score.
        Returns 1.0 if ages match within tolerance, lower if mismatch.
        """
        if dob is None or estimated_age is None:
            return 0.5  # Neutral if data missing

        actual_age = self.calculate_age_from_dob(dob)
        age_diff = abs(actual_age - estimated_age)

        if age_diff <= 3:
            return 1.0  # Perfect match
        elif age_diff <= 5:
            return 0.9  # Very close
        elif age_diff <= settings.AGE_TOLERANCE:
            return 0.7  # Acceptable
        elif age_diff <= 15:
            return 0.4  # Suspicious
        else:
            return 0.1  # Very suspicious (possible fraud)

    def calculate_risk_score(self, input_data: VerificationInput) -> float:
        """
        Calculate risk score based on behavioral signals.
        Returns 1.0 for low risk, lower values for higher risk.
        """
        risk_score = 1.0
        reasons = []

        # Previous rejections increase risk
        if input_data.previous_rejections > 0:
            penalty = min(0.3, input_data.previous_rejections * 0.1)
            risk_score -= penalty
            reasons.append(f"Previous rejections: {input_data.previous_rejections}")

        # Multiple manual reviews
        if input_data.previous_manual_reviews > 2:
            risk_score -= 0.1

        # Missing device fingerprint is slightly suspicious
        if input_data.device_fingerprint is None:
            risk_score -= 0.05

        # Time-based risk (submissions at unusual hours)
        if input_data.submission_time:
            hour = input_data.submission_time.hour
            if 2 <= hour <= 5:  # 2 AM - 5 AM
                risk_score -= 0.05

        return max(0.0, risk_score)

    def calculate_uniqueness_score(self, input_data: VerificationInput) -> float:
        """
        Calculate uniqueness score.
        Returns 1.0 if completely unique, 0.0 if duplicate detected.
        """
        if not input_data.is_unique_document:
            return 0.0  # Duplicate document is critical failure

        if not input_data.is_unique_face:
            return 0.0  # Duplicate face is critical failure

        if input_data.fuzzy_match_found:
            return 0.5  # Fuzzy match needs manual review

        return 1.0

    def score(self, input_data: VerificationInput) -> ScoringResult:
        """
        Calculate unified identity verification score.
        """
        breakdown = {}
        reasons = []
        flags = []

        # 1. Face similarity score
        face_score = input_data.face_similarity
        breakdown["face_match"] = round(face_score * 100, 1)

        if face_score < 0.4:
            flags.append("LOW_FACE_MATCH")
            reasons.append("Face similarity below threshold")
        elif face_score >= 0.7:
            reasons.append("Strong face match")

        # Adjust based on source
        if input_data.face_match_source == "fallback":
            face_score *= 0.8  # Reduce confidence for fallback matching
            flags.append("FALLBACK_MATCHING")

        # 2. Liveness score
        liveness_score = input_data.liveness_score if input_data.liveness_passed else 0.3
        breakdown["liveness"] = round(liveness_score * 100, 1)

        if not input_data.liveness_passed:
            flags.append("LIVENESS_FAILED")
            reasons.append("Liveness check did not pass")

        # 3. Document verification score
        doc_score = (
            input_data.document_confidence * 0.6 + input_data.ocr_confidence * 0.4
        )
        if input_data.document_type_verified:
            doc_score = min(1.0, doc_score + 0.1)
        else:
            flags.append("DOC_TYPE_UNVERIFIED")

        breakdown["document"] = round(doc_score * 100, 1)

        # 4. Age consistency score
        age_score = self.calculate_age_consistency(
            input_data.dob, input_data.estimated_age
        )
        breakdown["age_consistency"] = round(age_score * 100, 1)

        if age_score < 0.5:
            flags.append("AGE_MISMATCH")
            if input_data.dob and input_data.estimated_age:
                actual = self.calculate_age_from_dob(input_data.dob)
                reasons.append(
                    f"Age mismatch: DOB indicates {actual}, estimated {input_data.estimated_age}"
                )

        # 5. Uniqueness score
        uniqueness_score = self.calculate_uniqueness_score(input_data)
        breakdown["uniqueness"] = round(uniqueness_score * 100, 1)

        if uniqueness_score == 0:
            flags.append("DUPLICATE_DETECTED")
            if not input_data.is_unique_document:
                reasons.append("Document already used by another account")
            if not input_data.is_unique_face:
                reasons.append("Face matches existing verified account")
        elif uniqueness_score < 1.0:
            flags.append("POSSIBLE_DUPLICATE")
            reasons.append("Fuzzy match detected - needs manual review")

        # 6. Risk score
        risk_score = self.calculate_risk_score(input_data)
        breakdown["risk"] = round(risk_score * 100, 1)

        if risk_score < 0.7:
            flags.append("ELEVATED_RISK")

        # Calculate weighted total
        total_score = (
            face_score * self.WEIGHTS["face"]
            + liveness_score * self.WEIGHTS["liveness"]
            + doc_score * self.WEIGHTS["document"]
            + age_score * self.WEIGHTS["age"]
            + uniqueness_score * self.WEIGHTS["uniqueness"]
            + risk_score * self.WEIGHTS["risk"]
        ) * 100

        # Critical failures override score
        if uniqueness_score == 0:
            total_score = min(total_score, 30)  # Force rejection for duplicates
        if not input_data.liveness_passed and face_score < 0.5:
            total_score = min(total_score, 40)

        total_score = round(total_score, 1)

        # Determine decision
        if total_score >= self.AUTO_VERIFY_THRESHOLD:
            decision = "auto_verified"
        elif total_score >= self.MANUAL_REVIEW_THRESHOLD:
            decision = "manual_review"
        else:
            decision = "rejected"

        # Determine confidence level
        if total_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence = "high"
        elif total_score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = "medium"
        else:
            confidence = "low"

        # Add decision reason
        if decision == "auto_verified":
            reasons.insert(0, "All verification checks passed")
        elif decision == "manual_review":
            reasons.insert(0, "Some checks need manual verification")
        else:
            reasons.insert(0, "Verification failed")

        return ScoringResult(
            score=total_score,
            decision=decision,
            confidence=confidence,
            breakdown=breakdown,
            reasons=reasons,
            flags=flags,
        )


# Singleton instance
identity_scoring_service = IdentityScoringService()
