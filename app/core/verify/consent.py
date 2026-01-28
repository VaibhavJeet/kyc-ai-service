"""
TrustVault Consent Recording Service
Video-based consent verification for legal compliance

Use Cases:
- Loan agreements
- Medical consent
- Legal documents
- Rental agreements
- Employment contracts
"""

import uuid
import hashlib
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class ConsentType(str, Enum):
    """Types of consent that can be recorded"""
    LOAN_AGREEMENT = "loan_agreement"
    MEDICAL_CONSENT = "medical_consent"
    LEGAL_DOCUMENT = "legal_document"
    RENTAL_AGREEMENT = "rental_agreement"
    EMPLOYMENT_CONTRACT = "employment_contract"
    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    DATA_PROCESSING = "data_processing"
    CUSTOM = "custom"


class ConsentStatus(str, Enum):
    """Status of consent recording"""
    PENDING = "pending"
    RECORDING = "recording"
    PROCESSING = "processing"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class ConsentSession:
    """Consent recording session data"""
    id: str
    tenant_id: str
    consent_type: str
    document_id: Optional[str]
    document_hash: Optional[str]
    consent_text: str
    required_phrases: List[str]
    status: str
    created_at: datetime
    expires_at: datetime
    video_url: Optional[str] = None
    audio_transcript: Optional[str] = None
    face_verified: bool = False
    liveness_verified: bool = False
    phrases_verified: List[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    geolocation: Optional[Dict[str, Any]] = None


class ConsentRecordingService:
    """
    Service for recording and verifying video consent.

    Flow:
    1. Create consent session with required text/phrases
    2. User records video reading the consent
    3. System verifies:
       - Face matches registered identity
       - Liveness check passes
       - Audio contains required phrases
       - Timestamp and metadata recorded
    4. Consent proof stored securely
    """

    # Phrases that must be spoken for different consent types
    REQUIRED_PHRASES = {
        ConsentType.LOAN_AGREEMENT: [
            "I understand and agree",
            "I will repay the loan",
            "I have read the terms",
        ],
        ConsentType.MEDICAL_CONSENT: [
            "I give my consent",
            "I understand the risks",
            "I agree to the procedure",
        ],
        ConsentType.LEGAL_DOCUMENT: [
            "I have read and understood",
            "I agree to be bound",
            "This is my signature",
        ],
    }

    def __init__(self):
        self.sessions: Dict[str, ConsentSession] = {}  # In-memory for now

    async def create_session(
        self,
        tenant_id: str,
        consent_type: str,
        consent_text: str,
        document_id: Optional[str] = None,
        document_content: Optional[bytes] = None,
        custom_phrases: Optional[List[str]] = None,
        expires_in_minutes: int = 30,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new consent recording session.

        Args:
            tenant_id: Tenant ID
            consent_type: Type of consent
            consent_text: Full consent text to be shown
            document_id: Reference to external document
            document_content: Document content for hashing
            custom_phrases: Custom phrases user must speak
            expires_in_minutes: Session expiry time
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            Session details with ID and instructions
        """
        session_id = str(uuid.uuid4())

        # Get required phrases
        consent_type_enum = ConsentType(consent_type) if consent_type in [e.value for e in ConsentType] else ConsentType.CUSTOM
        required_phrases = custom_phrases or self.REQUIRED_PHRASES.get(consent_type_enum, [])

        # Hash document if provided
        document_hash = None
        if document_content:
            document_hash = hashlib.sha256(document_content).hexdigest()

        # Create session
        session = ConsentSession(
            id=session_id,
            tenant_id=tenant_id,
            consent_type=consent_type,
            document_id=document_id,
            document_hash=document_hash,
            consent_text=consent_text,
            required_phrases=required_phrases,
            status=ConsentStatus.PENDING.value,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
            ip_address=ip_address,
            user_agent=user_agent,
            phrases_verified=[],
        )

        self.sessions[session_id] = session

        logger.info(
            "consent.session_created",
            session_id=session_id,
            consent_type=consent_type,
            phrases_count=len(required_phrases)
        )

        return {
            "session_id": session_id,
            "consent_text": consent_text,
            "required_phrases": required_phrases,
            "instructions": self._get_instructions(consent_type_enum),
            "expires_at": session.expires_at.isoformat(),
            "status": session.status,
        }

    async def process_recording(
        self,
        session_id: str,
        video_base64: str,
        face_embedding: Optional[List[float]] = None,
        reference_face_embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Process a consent recording.

        Args:
            session_id: Consent session ID
            video_base64: Base64 encoded video
            face_embedding: Face embedding from video
            reference_face_embedding: Reference face for comparison

        Returns:
            Verification results
        """
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if session.status == ConsentStatus.EXPIRED.value:
            return {"success": False, "error": "Session expired"}

        if datetime.utcnow() > session.expires_at:
            session.status = ConsentStatus.EXPIRED.value
            return {"success": False, "error": "Session expired"}

        session.status = ConsentStatus.PROCESSING.value

        try:
            # 1. Extract audio and transcribe
            # In production, use speech-to-text API (Google, AWS, Azure)
            transcript = await self._transcribe_audio(video_base64)
            session.audio_transcript = transcript

            # 2. Verify required phrases are spoken
            verified_phrases = self._verify_phrases(transcript, session.required_phrases)
            session.phrases_verified = verified_phrases

            # 3. Verify face (if embeddings provided)
            face_match = False
            if face_embedding and reference_face_embedding:
                face_match = self._compare_embeddings(face_embedding, reference_face_embedding)
            session.face_verified = face_match

            # 4. Liveness check
            # In production, analyze video frames for liveness
            liveness_result = await self._check_video_liveness(video_base64)
            session.liveness_verified = liveness_result["is_live"]

            # 5. Store video reference
            # In production, upload to secure storage
            video_hash = hashlib.sha256(video_base64.encode()).hexdigest()
            session.video_url = f"consent/{session_id}/{video_hash}"

            # 6. Determine overall result
            all_phrases_verified = len(verified_phrases) == len(session.required_phrases)

            if all_phrases_verified and session.liveness_verified:
                if face_embedding and not face_match:
                    session.status = ConsentStatus.FAILED.value
                    return {
                        "success": False,
                        "session_id": session_id,
                        "error": "Face verification failed",
                        "phrases_verified": verified_phrases,
                        "phrases_missing": [p for p in session.required_phrases if p not in verified_phrases],
                    }

                session.status = ConsentStatus.VERIFIED.value
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "verified",
                    "consent_proof": self._generate_consent_proof(session),
                    "verification": {
                        "face_verified": session.face_verified,
                        "liveness_verified": session.liveness_verified,
                        "phrases_verified": verified_phrases,
                        "transcript": transcript,
                    },
                }
            else:
                session.status = ConsentStatus.FAILED.value
                return {
                    "success": False,
                    "session_id": session_id,
                    "error": "Consent verification failed",
                    "phrases_verified": verified_phrases,
                    "phrases_missing": [p for p in session.required_phrases if p not in verified_phrases],
                    "liveness_verified": session.liveness_verified,
                }

        except Exception as e:
            logger.error("consent.processing_failed", session_id=session_id, error=str(e))
            session.status = ConsentStatus.FAILED.value
            return {"success": False, "error": str(e)}

    async def revoke_consent(
        self,
        session_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Revoke a previously given consent.

        Args:
            session_id: Consent session ID
            reason: Reason for revocation

        Returns:
            Revocation confirmation
        """
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        if session.status != ConsentStatus.VERIFIED.value:
            return {"success": False, "error": "Only verified consent can be revoked"}

        session.status = ConsentStatus.REVOKED.value

        logger.info(
            "consent.revoked",
            session_id=session_id,
            reason=reason
        )

        return {
            "success": True,
            "session_id": session_id,
            "status": "revoked",
            "revoked_at": datetime.utcnow().isoformat(),
            "reason": reason,
        }

    async def get_consent_proof(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get consent proof for a verified session.

        Args:
            session_id: Consent session ID

        Returns:
            Consent proof document
        """
        session = self.sessions.get(session_id)
        if not session:
            return None

        if session.status != ConsentStatus.VERIFIED.value:
            return None

        return self._generate_consent_proof(session)

    # ============= Private Methods =============

    async def _transcribe_audio(self, video_base64: str) -> str:
        """
        Transcribe audio from video.
        In production, use speech-to-text API.
        """
        # Placeholder - in production use Google/AWS/Azure Speech-to-Text
        # For now, return empty transcript
        return ""

    def _verify_phrases(self, transcript: str, required_phrases: List[str]) -> List[str]:
        """Check which required phrases are present in transcript"""
        verified = []
        transcript_lower = transcript.lower()

        for phrase in required_phrases:
            if phrase.lower() in transcript_lower:
                verified.append(phrase)

        return verified

    def _compare_embeddings(self, emb1: List[float], emb2: List[float]) -> bool:
        """Compare two face embeddings"""
        import numpy as np
        e1 = np.array(emb1)
        e2 = np.array(emb2)

        # Cosine similarity
        similarity = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
        return similarity > 0.85

    async def _check_video_liveness(self, video_base64: str) -> Dict[str, Any]:
        """
        Check liveness from video frames.
        In production, analyze multiple frames for blink detection, head movement, etc.
        """
        # Placeholder - in production analyze video frames
        return {"is_live": True, "confidence": 0.8}

    def _get_instructions(self, consent_type: ConsentType) -> List[str]:
        """Get recording instructions for consent type"""
        return [
            "Position your face clearly in the camera frame",
            "Ensure good lighting and minimal background noise",
            "Read the consent text clearly and audibly",
            "Speak each required phrase clearly",
            "Keep looking at the camera throughout",
            "Recording should be between 10-60 seconds",
        ]

    def _generate_consent_proof(self, session: ConsentSession) -> Dict[str, Any]:
        """Generate a consent proof document"""
        proof_data = {
            "consent_id": session.id,
            "consent_type": session.consent_type,
            "document_id": session.document_id,
            "document_hash": session.document_hash,
            "consent_text_hash": hashlib.sha256(session.consent_text.encode()).hexdigest(),
            "verification": {
                "face_verified": session.face_verified,
                "liveness_verified": session.liveness_verified,
                "phrases_verified": session.phrases_verified,
            },
            "metadata": {
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "recorded_at": session.created_at.isoformat(),
                "geolocation": session.geolocation,
            },
            "video_reference": session.video_url,
            "transcript_hash": hashlib.sha256(
                (session.audio_transcript or "").encode()
            ).hexdigest(),
        }

        # Generate proof hash
        proof_string = json.dumps(proof_data, sort_keys=True, default=str)
        proof_hash = hashlib.sha256(proof_string.encode()).hexdigest()

        return {
            **proof_data,
            "proof_hash": proof_hash,
            "generated_at": datetime.utcnow().isoformat(),
        }


# Import needed for _generate_consent_proof
import json
from datetime import timedelta

# Singleton
_consent_service: Optional[ConsentRecordingService] = None


def get_consent_service() -> ConsentRecordingService:
    """Get consent recording service instance"""
    global _consent_service
    if _consent_service is None:
        _consent_service = ConsentRecordingService()
    return _consent_service
