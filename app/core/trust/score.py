"""
TrustVault Trust Score Engine
Unified identity verification scoring system

The Trust Score combines multiple verification signals into a single
confidence score (0-100) that determines the verification outcome.

Scoring Formula:
  score = (w1 * face) + (w2 * liveness) + (w3 * document) + (w4 * age) + (w5 * uniqueness) - penalty

Decision Thresholds:
  - >= 85: AUTO_VERIFIED (high confidence)
  - >= 50: MANUAL_REVIEW (medium confidence)
  - < 50: REJECTED (low confidence)
"""

import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from app.config import get_settings

logger = structlog.get_logger(__name__)


class TrustScoreEngine:
    """
    Unified trust scoring engine for identity verification.

    Combines multiple factors:
    - Face similarity (30%)
    - Liveness detection (25%)
    - Document verification (20%)
    - Age consistency (10%)
    - Uniqueness checks (15%)
    - Risk penalties (subtracted)
    """

    # Scoring weights (must sum to 1.0)
    WEIGHTS = {
        'face': 0.30,        # Face similarity is critical
        'liveness': 0.25,    # Anti-spoof protection
        'document': 0.20,    # Document quality
        'age': 0.10,         # Age consistency
        'uniqueness': 0.15,  # Duplicate detection
    }

    def __init__(self):
        self.settings = get_settings()
        # Use configured thresholds or defaults
        self.thresholds = {
            'auto_verify': self.settings.trust_auto_approve_threshold,
            'manual_review': self.settings.trust_manual_review_threshold,
            'reject': self.settings.trust_rejection_threshold,
        }

    async def calculate(
        self,
        face_similarity: float,
        liveness_score: float,
        liveness_passed: bool,
        document_confidence: float = 0.0,
        ocr_confidence: float = 0.0,
        document_type_verified: bool = True,
        dob: Optional[str] = None,
        estimated_age: Optional[int] = None,
        is_unique_document: bool = True,
        is_unique_face: bool = True,
        fuzzy_match_found: bool = False,
        device_fingerprint: Optional[str] = None,
        previous_rejections: int = 0,
    ) -> Dict[str, Any]:
        """
        Calculate unified trust score from verification signals.

        Args:
            face_similarity: Cosine similarity between selfie and document (0-1)
            liveness_score: Anti-spoof confidence (0-1)
            liveness_passed: Boolean liveness check result
            document_confidence: Document type detection confidence (0-1)
            ocr_confidence: OCR text extraction confidence (0-100)
            document_type_verified: Document type matches expected
            dob: Date of birth from document (YYYY-MM-DD)
            estimated_age: Estimated age from face
            is_unique_document: Document not used by another user
            is_unique_face: Face not matched to another user
            fuzzy_match_found: Fuzzy hash matched (potential duplicate)
            device_fingerprint: Device ID for risk assessment
            previous_rejections: Number of previous KYC rejections

        Returns:
            Dictionary with:
            - score: 0-100 trust score
            - decision: auto_verified, manual_review, rejected
            - confidence: high, medium, low
            - breakdown: Score per factor
            - reasons: Human-readable explanations
            - flags: Risk flags for review
        """
        breakdown = {}
        reasons = []
        flags = []

        # 1. Face Score (0-1)
        face_score = max(0, min(1, face_similarity))
        if face_similarity < 0.5:
            reasons.append("Low face similarity between selfie and document")
            flags.append("LOW_FACE_MATCH")
        elif face_similarity < 0.7:
            reasons.append("Moderate face similarity - may need review")
            flags.append("MODERATE_FACE_MATCH")
        breakdown['face'] = round(face_score * 100, 1)

        # 2. Liveness Score (0-1)
        if not liveness_passed:
            liveness_final = liveness_score * 0.5  # Penalize failed liveness
            reasons.append("Liveness check failed - possible spoofing attempt")
            flags.append("LIVENESS_FAILED")
        else:
            liveness_final = liveness_score
        breakdown['liveness'] = round(liveness_final * 100, 1)

        # 3. Document Score (0-1)
        ocr_normalized = min(ocr_confidence / 100.0, 1.0)
        doc_type_bonus = 0.2 if document_type_verified else 0
        document_score = (document_confidence * 0.5) + (ocr_normalized * 0.3) + doc_type_bonus
        document_score = min(document_score, 1.0)

        if document_confidence < 0.5:
            reasons.append("Document type unclear or unrecognized")
            flags.append("UNCLEAR_DOCUMENT")
        if ocr_confidence < 50:
            reasons.append("Poor document quality - text extraction difficult")
            flags.append("LOW_OCR_QUALITY")
        breakdown['document'] = round(document_score * 100, 1)

        # 4. Age Consistency Score (0-1)
        age_score = self._calculate_age_consistency(dob, estimated_age)
        if age_score < 0.5 and dob and estimated_age:
            doc_age = self._age_from_dob(dob)
            if doc_age:
                reasons.append(f"Age mismatch: document shows ~{doc_age}yrs, face appears ~{estimated_age}yrs")
                flags.append("AGE_MISMATCH")
        breakdown['age'] = round(age_score * 100, 1)

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
            reasons.append("Possible face match detected (fuzzy)")
            flags.append("FUZZY_MATCH")
        uniqueness_score = max(0, uniqueness_score)
        breakdown['uniqueness'] = round(uniqueness_score * 100, 1)

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
            reasons.append(f"User has {previous_rejections} previous rejection(s)")
        if not is_unique_document or not is_unique_face:
            risk_penalty += 0.1
        breakdown['risk_penalty'] = round(risk_penalty * 100, 1)

        # Final Score (0-100)
        final_score = max(0, min(1.0, base_score - risk_penalty))
        score_100 = round(final_score * 100, 1)

        # Decision based on thresholds
        if final_score >= self.thresholds['auto_verify']:
            decision = 'auto_verified'
            confidence = 'high'
        elif final_score >= self.thresholds['manual_review']:
            decision = 'manual_review'
            confidence = 'medium'
        else:
            decision = 'rejected'
            confidence = 'low'

        if not reasons:
            reasons.append("All verification checks passed")

        logger.info(
            "trust_score.calculated",
            score=score_100,
            decision=decision,
            flags=flags
        )

        return {
            'score': score_100,
            'decision': decision,
            'confidence': confidence,
            'breakdown': breakdown,
            'reasons': reasons,
            'flags': flags,
        }

    def get_decision(
        self,
        score: float,
        custom_thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Get verification decision from score.

        Args:
            score: Trust score (0-100)
            custom_thresholds: Optional custom thresholds to override defaults

        Returns:
            Decision details with recommended actions
        """
        thresholds = custom_thresholds or {
            'auto_verify': self.thresholds['auto_verify'] * 100,
            'manual_review': self.thresholds['manual_review'] * 100,
        }

        # Ensure score is in 0-100 range
        score = max(0, min(100, score))

        if score >= thresholds.get('auto_verify', 85):
            return {
                'decision': 'auto_verified',
                'confidence': 'high',
                'recommended_action': 'Approve automatically',
                'next_steps': [
                    'User verification complete',
                    'Grant access to verified features',
                    'Store verification record for compliance',
                ],
            }
        elif score >= thresholds.get('manual_review', 50):
            return {
                'decision': 'manual_review',
                'confidence': 'medium',
                'recommended_action': 'Queue for manual review',
                'next_steps': [
                    'Assign to verification team',
                    'Request additional documents if needed',
                    'Compare against fraud patterns',
                    'Make final decision within 24-48 hours',
                ],
            }
        else:
            return {
                'decision': 'rejected',
                'confidence': 'low',
                'recommended_action': 'Reject and notify user',
                'next_steps': [
                    'Inform user of rejection reason',
                    'Allow re-submission with better documents',
                    'Flag for potential fraud review if score very low',
                ],
            }

    def _calculate_age_consistency(
        self,
        dob: Optional[str],
        estimated_age: Optional[int]
    ) -> float:
        """Calculate age consistency between document DOB and face-estimated age."""
        if not dob or not estimated_age:
            return 0.7  # Neutral if missing data

        doc_age = self._age_from_dob(dob)
        if doc_age is None:
            return 0.7

        age_diff = abs(doc_age - estimated_age)

        # Allow more tolerance for older people
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
        """Calculate age from date of birth string."""
        try:
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
