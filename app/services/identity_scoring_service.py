"""
Identity Scoring Service - Unified Identity Verification Score
Combines multiple signals into a single confidence score.

Scoring Formula:
  score = (w1 * face_score) + (w2 * liveness_score) + (w3 * document_score)
        + (w4 * age_consistency_score) + (w5 * uniqueness_score) - (risk_penalty)

Where:
  - face_score: Face similarity (0-1)
  - liveness_score: Anti-spoof confidence (0-1)
  - document_score: OCR confidence + type verification (0-1)
  - age_consistency_score: Age from face matches DOB (0-1)
  - uniqueness_score: Not duplicate document/face (0-1)
  - risk_penalty: Device fingerprint risk, previous rejections, etc.

NOTE: This is SERVER-SIDE scoring. The Flutter app does on-device verification
and sends results. This service is for enhanced verification or manual review cases.
"""

import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class IdentityScoringService:
    """Unified identity scoring based on multiple verification signals"""

    # Weights for scoring (must sum to 1.0)
    WEIGHTS = {
        'face': 0.30,        # Face similarity is most important
        'liveness': 0.25,    # Anti-spoof/liveness
        'document': 0.20,    # Document OCR quality
        'age': 0.10,         # Age consistency
        'uniqueness': 0.15,  # Not a duplicate
    }

    # Decision thresholds
    THRESHOLDS = {
        'auto_verify': 0.85,      # Auto-approve above this
        'manual_review': 0.50,    # Manual review between 0.50-0.85
        'reject': 0.50,           # Auto-reject below this
    }

    def __init__(self):
        self.settings = get_settings()

    async def calculate_score(
        self,
        face_similarity: float,
        liveness_score: float,
        liveness_passed: bool,
        document_confidence: float,
        ocr_confidence: float,
        document_type_verified: bool,
        dob: Optional[str] = None,
        estimated_age: Optional[int] = None,
        is_unique_document: bool = True,
        is_unique_face: bool = True,
        fuzzy_match_found: bool = False,
        device_fingerprint: Optional[str] = None,
        previous_rejections: int = 0,
    ) -> Dict[str, Any]:
        """
        Calculate unified identity score from multiple signals.

        Args:
            face_similarity: Cosine similarity between selfie and document (0-1)
            liveness_score: Anti-spoof confidence (0-1)
            liveness_passed: Boolean liveness check result
            document_confidence: Document type detection confidence (0-1)
            ocr_confidence: OCR text extraction confidence (0-100)
            document_type_verified: Document type matches expected
            dob: Date of birth from document (YYYY-MM-DD or DD/MM/YYYY)
            estimated_age: Estimated age from face
            is_unique_document: Document not used by another user
            is_unique_face: Face not matched to another user
            fuzzy_match_found: Fuzzy hash matched (potential duplicate)
            device_fingerprint: Device ID for risk assessment
            previous_rejections: Number of previous KYC rejections for this user

        Returns:
            Dictionary with score, decision, confidence, breakdown, reasons, flags
        """
        breakdown = {}
        reasons = []
        flags = []

        # 1. Face Score (0-1)
        face_score = face_similarity
        if face_similarity < 0.5:
            reasons.append("Low face similarity")
            flags.append("LOW_FACE_MATCH")
        breakdown['face'] = face_score

        # 2. Liveness Score (0-1)
        if not liveness_passed:
            liveness_final = liveness_score * 0.5  # Penalize failed liveness
            reasons.append("Liveness check failed")
            flags.append("LIVENESS_FAILED")
        else:
            liveness_final = liveness_score
        breakdown['liveness'] = liveness_final

        # 3. Document Score (0-1)
        ocr_normalized = min(ocr_confidence / 100.0, 1.0)
        doc_type_bonus = 0.2 if document_type_verified else 0
        document_score = (document_confidence * 0.5) + (ocr_normalized * 0.3) + doc_type_bonus
        document_score = min(document_score, 1.0)

        if document_confidence < 0.5:
            reasons.append("Document type unclear")
            flags.append("UNCLEAR_DOCUMENT")
        if ocr_confidence < 50:
            reasons.append("Poor document quality/OCR")
            flags.append("LOW_OCR_QUALITY")
        breakdown['document'] = document_score

        # 4. Age Consistency Score (0-1)
        age_score = self._calculate_age_consistency(dob, estimated_age)
        if age_score < 0.5 and dob and estimated_age:
            reasons.append(f"Age mismatch: document says ~{self._age_from_dob(dob)}, face appears ~{estimated_age}")
            flags.append("AGE_MISMATCH")
        breakdown['age'] = age_score

        # 5. Uniqueness Score (0-1)
        uniqueness_score = 1.0
        if not is_unique_document:
            uniqueness_score -= 0.5
            reasons.append("Document already registered to another user")
            flags.append("DUPLICATE_DOCUMENT")
        if not is_unique_face:
            uniqueness_score -= 0.3
            reasons.append("Face matched to existing user")
            flags.append("DUPLICATE_FACE")
        if fuzzy_match_found:
            uniqueness_score -= 0.2
            reasons.append("Possible face match (fuzzy)")
            flags.append("FUZZY_MATCH")
        uniqueness_score = max(0, uniqueness_score)
        breakdown['uniqueness'] = uniqueness_score

        # Calculate weighted base score
        base_score = (
            self.WEIGHTS['face'] * face_score +
            self.WEIGHTS['liveness'] * liveness_final +
            self.WEIGHTS['document'] * document_score +
            self.WEIGHTS['age'] * age_score +
            self.WEIGHTS['uniqueness'] * uniqueness_score
        )

        # 6. Risk Penalty (0-0.3)
        risk_penalty = 0
        if previous_rejections > 0:
            risk_penalty += min(0.1 * previous_rejections, 0.2)
            flags.append(f"PREVIOUS_REJECTIONS_{previous_rejections}")
        if not is_unique_document or not is_unique_face:
            risk_penalty += 0.1
        breakdown['risk_penalty'] = risk_penalty

        # Final Score
        final_score = max(0, min(1.0, base_score - risk_penalty))

        # Decision
        if final_score >= self.THRESHOLDS['auto_verify']:
            decision = 'auto_verified'
            confidence = 'high'
        elif final_score >= self.THRESHOLDS['manual_review']:
            decision = 'manual_review'
            confidence = 'medium'
        else:
            decision = 'rejected'
            confidence = 'low'

        if not reasons:
            reasons.append("All checks passed")

        return {
            'score': round(final_score * 100, 1),  # 0-100
            'decision': decision,
            'confidence': confidence,
            'breakdown': {k: round(v * 100, 1) for k, v in breakdown.items()},
            'reasons': reasons,
            'flags': flags,
        }

    def _calculate_age_consistency(
        self,
        dob: Optional[str],
        estimated_age: Optional[int]
    ) -> float:
        """
        Calculate age consistency between document DOB and face-estimated age.
        """
        if not dob or not estimated_age:
            return 0.7  # Neutral if missing data

        doc_age = self._age_from_dob(dob)
        if doc_age is None:
            return 0.7

        # Calculate age difference
        age_diff = abs(doc_age - estimated_age)

        # Allow more tolerance for older people (age estimation is less accurate)
        if doc_age > 50:
            tolerance = 10
        elif doc_age > 30:
            tolerance = 7
        else:
            tolerance = 5

        if age_diff <= tolerance:
            return 1.0
        elif age_diff <= tolerance * 2:
            return 0.7
        elif age_diff <= tolerance * 3:
            return 0.4
        else:
            return 0.1

    def _age_from_dob(self, dob: str) -> Optional[int]:
        """Calculate age from date of birth string"""
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    birth_date = datetime.strptime(dob, fmt).date()
                    today = date.today()
                    age = today.year - birth_date.year
                    if (today.month, today.day) < (birth_date.month, birth_date.day):
                        age -= 1
                    return age
                except ValueError:
                    continue
            return None
        except Exception:
            return None


# Singleton
_identity_scoring_service: Optional[IdentityScoringService] = None


def get_identity_scoring_service() -> IdentityScoringService:
    """Get or create identity scoring service instance"""
    global _identity_scoring_service
    if _identity_scoring_service is None:
        _identity_scoring_service = IdentityScoringService()
    return _identity_scoring_service
