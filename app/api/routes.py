"""
API Routes - FastAPI endpoints for all AI services
Single unified API for: Chat, Content Generation, KYC
"""

import base64
import cv2
import numpy as np
import structlog
import time
import secrets
import hashlib
import asyncio
from typing import Optional, Dict, List
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Depends, Header, Request

from app.core.config import get_settings, Settings
from app.services.llm_service import get_llm_service, LLMService
from app.services.face_service import get_face_service, FaceService
from app.services.ocr_service import get_ocr_service, OCRService
from app.services.anti_spoof_service import get_anti_spoof_service
from app.services.identity_scoring_service import get_identity_scoring_service
from app.services.hash_service import get_hash_service
from app.agents.router import get_router
from app.api.schemas import (
    ChatRequest, ChatResponse,
    TitleRequest, TitleResponse,
    DescriptionRequest, DescriptionResponse,
    BudgetRequest, BudgetResponse,
    FaceCompareRequest, FaceCompareResponse,
    LivenessCheckResponse,
    DocumentOCRRequest, DocumentOCRResponse,
    KYCVerifyRequest, KYCVerifyResponse,
    HealthResponse, ServiceStatus,
    # New schemas
    AntiSpoofRequest, AntiSpoofResponse,
    IdentityScoreRequest, IdentityScoreResponse,
    GenerateHashRequest, GenerateHashResponse,
    CompareHashesRequest, CompareHashesResponse,
    CompleteVerifyRequest, CompleteVerifyResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["AI Service"])


# ============= Dependencies =============

def get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    return x_api_key


# Rate limiting storage for failed auth attempts
_failed_auth_attempts: Dict[str, List[float]] = {}
MAX_AUTH_ATTEMPTS = 5
AUTH_ATTEMPT_WINDOW = 300  # 5 minutes


@lru_cache(maxsize=1000)
def hash_key(key: str) -> str:
    """Hash API key using SHA256 for constant-time comparison"""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


async def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded auth rate limit"""
    now = time.time()

    if ip not in _failed_auth_attempts:
        _failed_auth_attempts[ip] = []

    # Remove old attempts outside the time window
    _failed_auth_attempts[ip] = [
        timestamp for timestamp in _failed_auth_attempts[ip]
        if now - timestamp < AUTH_ATTEMPT_WINDOW
    ]

    # Check if limit exceeded
    return len(_failed_auth_attempts[ip]) >= MAX_AUTH_ATTEMPTS


def record_failed_auth(ip: str):
    """Record failed authentication attempt"""
    if ip not in _failed_auth_attempts:
        _failed_auth_attempts[ip] = []
    _failed_auth_attempts[ip].append(time.time())


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key),
    settings: Settings = Depends(get_settings)
):
    """
    Verify API key with constant-time comparison and rate limiting.
    Prevents timing attacks and brute force attempts.
    """
    client_ip = request.client.host

    # Check rate limit
    if await check_rate_limit(client_ip):
        logger.warning(
            "Rate limit exceeded for API key authentication",
            ip=client_ip,
            attempts=len(_failed_auth_attempts.get(client_ip, []))
        )
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Try again later."
        )

    # Require API key to be configured
    if not settings.api_key or settings.api_key == "":
        logger.error("API key not configured in settings")
        raise HTTPException(
            status_code=500,
            detail="Authentication not configured"
        )

    # Require API key in request
    if not api_key or api_key == "":
        record_failed_auth(client_ip)
        logger.warning("Missing API key in request", ip=client_ip)
        await asyncio.sleep(1)  # Rate limit failed attempts
        raise HTTPException(
            status_code=401,
            detail="API key required"
        )

    # Constant-time comparison to prevent timing attacks
    expected_hash = hash_key(settings.api_key)
    provided_hash = hash_key(api_key)

    if not secrets.compare_digest(expected_hash, provided_hash):
        record_failed_auth(client_ip)
        logger.warning(
            "Invalid API key attempt",
            ip=client_ip,
            attempts=len(_failed_auth_attempts.get(client_ip, []))
        )
        await asyncio.sleep(1)  # Prevent timing attacks
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    # Clear failed attempts on successful authentication
    if client_ip in _failed_auth_attempts:
        _failed_auth_attempts[client_ip] = []


# Image validation constants
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_DIMENSION = 4096  # 4K resolution max
MIN_IMAGE_DIMENSION = 100  # Minimum size


def validate_base64_size(base64_str: str) -> None:
    """Validate base64 string size before decoding"""
    # Base64 encoding increases size by ~37%
    max_encoded_size = int(MAX_IMAGE_SIZE * 1.37)
    if len(base64_str) > max_encoded_size:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum size: {MAX_IMAGE_SIZE / (1024*1024):.0f}MB"
        )


def decode_base64_image(base64_str: str) -> np.ndarray:
    """Decode base64 string to numpy array image with validation"""
    try:
        # Remove data URL prefix if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        # Validate encoded size
        validate_base64_size(base64_str)

        # Decode
        img_bytes = base64.b64decode(base64_str)

        # Validate decoded size
        if len(img_bytes) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Decoded image exceeds {MAX_IMAGE_SIZE / (1024*1024):.0f}MB limit"
            )

        # Convert to numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image. Invalid format.")

        # Validate dimensions
        height, width = img.shape[:2]
        if height < MIN_IMAGE_DIMENSION or width < MIN_IMAGE_DIMENSION:
            raise HTTPException(
                status_code=400,
                detail=f"Image too small. Minimum dimensions: {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}px"
            )

        if height > MAX_IMAGE_DIMENSION or width > MAX_IMAGE_DIMENSION:
            raise HTTPException(
                status_code=413,
                detail=f"Image too large. Maximum dimensions: {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}px"
            )

        # Validate image has content
        if img.size == 0:
            raise ValueError("Empty image")

        return img

    except base64.binascii.Error as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 encoding: {str(e)}")
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Image decode error: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to process image")


# ============= Health Check =============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health of all services"""
    llm = get_llm_service()
    face = get_face_service()
    ocr = get_ocr_service()

    services = [
        ServiceStatus(
            name="llm",
            available=llm.is_available(),
            details="Gemma 3 270M Q4 via llama.cpp"
        ),
        ServiceStatus(
            name="face",
            available=face.is_available(),
            details="InsightFace buffalo_l ArcFace ResNet100 (512-dim)"
        ),
        ServiceStatus(
            name="ocr",
            available=ocr.is_available(),
            details="Tesseract OCR"
        ),
    ]

    status = "healthy" if any(s.available for s in services) else "degraded"

    return HealthResponse(status=status, services=services)


# ============= Chat Endpoints =============

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest):
    """Chat with AI assistant"""
    llm = get_llm_service()

    if not llm.is_available():
        return ChatResponse(response="", success=False, error="LLM not available")

    try:
        messages = [{"role": m.role, "content": m.content} for m in request.history]
        messages.append({"role": "user", "content": request.message})

        response = await llm.chat(messages)
        return ChatResponse(response=response)

    except Exception as e:
        logger.error("Chat failed", error=str(e))
        return ChatResponse(response="", success=False, error=str(e))


# ============= Content Generation Endpoints =============

@router.post("/generate/title", response_model=TitleResponse, dependencies=[Depends(verify_api_key)])
async def generate_title(request: TitleRequest):
    """Generate a title from description"""
    llm = get_llm_service()

    if not llm.is_available():
        return TitleResponse(title="", success=False)

    try:
        title = await llm.generate_title(request.description)
        return TitleResponse(title=title)
    except Exception as e:
        logger.error("Title generation failed", error=str(e))
        return TitleResponse(title="", success=False)


@router.post("/generate/description", response_model=DescriptionResponse, dependencies=[Depends(verify_api_key)])
async def generate_description(request: DescriptionRequest):
    """Generate a description from title"""
    llm = get_llm_service()

    if not llm.is_available():
        return DescriptionResponse(description="", success=False)

    try:
        description = await llm.generate_description(request.title, request.context or "")
        return DescriptionResponse(description=description)
    except Exception as e:
        logger.error("Description generation failed", error=str(e))
        return DescriptionResponse(description="", success=False)


@router.post("/generate/budget", response_model=BudgetResponse, dependencies=[Depends(verify_api_key)])
async def suggest_budget(request: BudgetRequest):
    """Suggest budget for a task"""
    llm = get_llm_service()

    if not llm.is_available():
        return BudgetResponse(min=500, max=5000, recommended=1500, currency=request.currency or "INR", success=False)

    try:
        budget = await llm.suggest_budget(
            request.title,
            request.description,
            request.category or "",
            request.currency or "INR"
        )
        return BudgetResponse(
            min=budget.get("min", 500),
            max=budget.get("max", 5000),
            recommended=budget.get("recommended", 1500),
            currency=request.currency or "INR"
        )
    except Exception as e:
        logger.error("Budget suggestion failed", error=str(e))
        return BudgetResponse(min=500, max=5000, recommended=1500, currency=request.currency or "INR", success=False)


# ============= KYC Endpoints =============

@router.post("/kyc/compare-faces", response_model=FaceCompareResponse, dependencies=[Depends(verify_api_key)])
async def compare_faces(request: FaceCompareRequest):
    """Compare two face images (selfie vs document photo)"""
    face = get_face_service()

    if not face.is_available():
        return FaceCompareResponse(match=False, similarity=0, threshold=0, success=False, error="Face service not available")

    try:
        selfie = decode_base64_image(request.selfie_base64)
        document = decode_base64_image(request.document_base64)

        result = await face.compare_faces(selfie, document)

        return FaceCompareResponse(
            match=result["match"],
            similarity=result["similarity"],
            threshold=result.get("threshold", 0.45),
            error=result.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Face comparison failed", error=str(e))
        return FaceCompareResponse(match=False, similarity=0, threshold=0, success=False, error=str(e))


@router.post("/kyc/liveness", response_model=LivenessCheckResponse, dependencies=[Depends(verify_api_key)])
async def check_liveness(selfie_base64: str):
    """Check if image is a live capture (not a photo of photo)"""
    face = get_face_service()

    if not face.is_available():
        return LivenessCheckResponse(is_live=False, score=0, success=False, error="Face service not available")

    try:
        image = decode_base64_image(selfie_base64)
        result = await face.check_liveness(image)

        return LivenessCheckResponse(
            is_live=result["is_live"],
            score=result["score"],
            details=result.get("details"),
            error=result.get("reason")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Liveness check failed", error=str(e))
        return LivenessCheckResponse(is_live=False, score=0, success=False, error=str(e))


@router.post("/kyc/ocr", response_model=DocumentOCRResponse, dependencies=[Depends(verify_api_key)])
async def extract_document(request: DocumentOCRRequest):
    """Extract text and info from ID document"""
    ocr = get_ocr_service()

    if not ocr.is_available():
        return DocumentOCRResponse(text="", confidence=0, success=False, error="OCR service not available")

    try:
        image = decode_base64_image(request.image_base64)
        result = await ocr.extract_document_info(image, request.document_type or "auto")

        return DocumentOCRResponse(
            text=result.get("raw_text", ""),
            document_type=result.get("document_type"),
            document_number=result.get("document_number"),
            name=result.get("name"),
            dob=result.get("dob"),
            confidence=result.get("confidence", 0),
            error=result.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OCR extraction failed", error=str(e))
        return DocumentOCRResponse(text="", confidence=0, success=False, error=str(e))


@router.post("/kyc/verify", response_model=KYCVerifyResponse, dependencies=[Depends(verify_api_key)])
async def verify_kyc(request: KYCVerifyRequest):
    """
    Complete KYC verification:
    1. Face comparison (selfie vs document photo)
    2. Liveness check
    3. Document OCR and verification
    """
    face = get_face_service()
    ocr = get_ocr_service()

    try:
        selfie = decode_base64_image(request.selfie_base64)
        document = decode_base64_image(request.document_base64)

        # 1. Face comparison
        face_result = {"match": False, "similarity": 0.0}
        if face.is_available():
            face_result = await face.compare_faces(selfie, document)

        # 2. Liveness check
        liveness_result = {"is_live": False, "score": 0.0}
        if face.is_available():
            liveness_result = await face.check_liveness(selfie)

        # 3. Document OCR
        doc_result = {}
        if ocr.is_available():
            doc_result = await ocr.verify_document(
                document,
                expected_name=request.expected_name,
                expected_dob=request.expected_dob
            )

        # Calculate overall pass
        face_pass = face_result.get("match", False)
        liveness_pass = liveness_result.get("is_live", False)
        doc_pass = doc_result.get("document_detected", False)

        overall_pass = face_pass and liveness_pass and doc_pass

        # Confidence based on all factors
        confidence = (
            (face_result.get("similarity", 0) * 0.4) +
            (liveness_result.get("score", 0) * 0.3) +
            (doc_result.get("confidence", 0) / 100 * 0.3)
        )

        return KYCVerifyResponse(
            face_match=face_result.get("match", False),
            face_similarity=face_result.get("similarity", 0),
            liveness_score=liveness_result.get("score", 0),
            is_live=liveness_result.get("is_live", False),
            document_type=doc_result.get("document_type"),
            document_number=doc_result.get("document_number"),
            name_match=doc_result.get("name_match"),
            dob_match=doc_result.get("dob_match"),
            overall_pass=overall_pass,
            confidence=confidence
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("KYC verification failed", error=str(e))
        return KYCVerifyResponse(
            face_match=False,
            face_similarity=0,
            liveness_score=0,
            is_live=False,
            overall_pass=False,
            confidence=0,
            success=False,
            error=str(e)
        )


# ============= Advanced KYC Endpoints (Server-Side) =============
# NOTE: These are for enhanced verification. Flutter app does on-device processing.

@router.post("/kyc/anti-spoof", response_model=AntiSpoofResponse, dependencies=[Depends(verify_api_key)])
async def anti_spoof_check(request: AntiSpoofRequest):
    """
    Multi-layer anti-spoofing analysis.
    Detects printed photos, screen displays, and other spoofing attempts.

    NOTE: Flutter app already does this on-device. Use this for:
    - Server-side verification of borderline cases
    - When on-device liveness failed but face match passed
    """
    anti_spoof = get_anti_spoof_service()

    try:
        image = decode_base64_image(request.image_base64)

        # Prepare eye positions if provided
        eye_positions = None
        if request.left_eye and request.right_eye:
            eye_positions = (
                tuple(request.left_eye),
                tuple(request.right_eye)
            )

        result = await anti_spoof.analyze(image, eye_positions)

        return AntiSpoofResponse(
            is_live=result["is_live"],
            confidence=result["confidence"],
            reason=result["reason"],
            scores=result["scores"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Anti-spoof check failed", error=str(e))
        return AntiSpoofResponse(
            is_live=True,  # Don't block on error
            confidence=0.5,
            reason="Analysis failed",
            scores={},
            success=False,
            error=str(e)
        )


@router.post("/kyc/identity-score", response_model=IdentityScoreResponse, dependencies=[Depends(verify_api_key)])
async def calculate_identity_score(request: IdentityScoreRequest):
    """
    Calculate unified identity score from verification signals.
    Use this to get a final decision based on all verification factors.

    NOTE: Flutter app sends on-device results. This calculates the final score.
    """
    scoring = get_identity_scoring_service()

    try:
        result = await scoring.calculate_score(
            face_similarity=request.face_similarity,
            liveness_score=request.liveness_score,
            liveness_passed=request.liveness_passed,
            document_confidence=request.document_confidence,
            ocr_confidence=request.ocr_confidence,
            document_type_verified=request.document_type_verified,
            dob=request.dob,
            estimated_age=request.estimated_age,
            is_unique_document=request.is_unique_document,
            is_unique_face=request.is_unique_face,
            fuzzy_match_found=request.fuzzy_match_found,
            device_fingerprint=request.device_fingerprint,
            previous_rejections=request.previous_rejections,
        )

        return IdentityScoreResponse(
            score=result["score"],
            decision=result["decision"],
            confidence=result["confidence"],
            breakdown=result["breakdown"],
            reasons=result["reasons"],
            flags=result["flags"]
        )
    except Exception as e:
        logger.error("Identity scoring failed", error=str(e))
        return IdentityScoreResponse(
            score=0,
            decision="manual_review",
            confidence="low",
            breakdown={},
            reasons=["Scoring failed"],
            flags=["ERROR"],
            success=False,
            error=str(e)
        )


@router.post("/kyc/generate-hashes", response_model=GenerateHashResponse, dependencies=[Depends(verify_api_key)])
async def generate_face_hashes(request: GenerateHashRequest):
    """
    Generate privacy-preserving hashes from face embedding.
    Returns SHA256 hash and fuzzy hashes for duplicate detection.

    NOTE: Flutter app already generates these on-device and sends them.
    This is for server-side processing when images are verified server-side.
    """
    hash_service = get_hash_service()

    try:
        embedding = np.array(request.embedding)

        embedding_hash = hash_service.generate_embedding_hash(embedding)
        fuzzy_hashes = hash_service.generate_fuzzy_hashes(embedding)

        return GenerateHashResponse(
            embedding_hash=embedding_hash,
            fuzzy_hashes=fuzzy_hashes
        )
    except Exception as e:
        logger.error("Hash generation failed", error=str(e))
        return GenerateHashResponse(
            embedding_hash="",
            fuzzy_hashes=[],
            success=False
        )


@router.post("/kyc/compare-hashes", response_model=CompareHashesResponse, dependencies=[Depends(verify_api_key)])
async def compare_fuzzy_hashes(request: CompareHashesRequest):
    """
    Compare two sets of fuzzy hashes to detect potential duplicates.
    Returns match confidence and number of matching levels.
    """
    hash_service = get_hash_service()

    try:
        matching_levels, confidence = hash_service.compare_fuzzy_hashes(
            request.hashes1,
            request.hashes2
        )

        # Consider a match if 2+ levels match (L2 or L3 matches are significant)
        is_match = matching_levels >= 2 or confidence >= 0.5

        return CompareHashesResponse(
            matching_levels=matching_levels,
            confidence=confidence,
            is_match=is_match
        )
    except Exception as e:
        logger.error("Hash comparison failed", error=str(e))
        return CompareHashesResponse(
            matching_levels=0,
            confidence=0,
            is_match=False,
            success=False
        )


@router.post("/verify/complete", response_model=CompleteVerifyResponse, dependencies=[Depends(verify_api_key)])
async def complete_verification(request: CompleteVerifyRequest):
    """
    Complete server-side KYC verification.
    Performs all checks: face comparison, liveness, OCR, scoring, hash generation.

    NOTE: This is the full server-side pipeline. Use when:
    - On-device verification failed or was skipped
    - Manual review escalation with server-side re-verification
    - Enhanced verification for high-risk transactions
    """
    face = get_face_service()
    ocr = get_ocr_service()
    anti_spoof = get_anti_spoof_service()
    scoring = get_identity_scoring_service()
    hash_service = get_hash_service()

    try:
        document = decode_base64_image(request.document_base64)
        selfie = decode_base64_image(request.selfie_base64)

        # 1. Face Detection & Comparison
        face_result = {"match": False, "similarity": 0.0}
        embedding_hash = None
        fuzzy_hashes = None
        estimated_age = None

        if face.is_available():
            face_result = await face.compare_faces(selfie, document)

            # Get embedding for hash generation
            faces = await face.detect_faces(selfie)
            if faces:
                box = faces[0]["box"]
                face_crop = selfie[box[1]:box[3], box[0]:box[2]]
                embedding = await face.get_embedding(face_crop)
                if embedding is not None:
                    embedding_hash = hash_service.generate_embedding_hash(embedding)
                    fuzzy_hashes = hash_service.generate_fuzzy_hashes(embedding)

                # Age estimation
                age_result = await face.estimate_age_gender(face_crop)
                estimated_age = age_result.get("age")

        # 2. Anti-Spoof / Liveness
        liveness_result = await anti_spoof.analyze(selfie)

        # 3. Document OCR
        doc_result = {}
        if ocr.is_available():
            doc_result = await ocr.extract_document_info(document, request.expected_document_type or "auto")

        # 4. Calculate Identity Score
        score_result = await scoring.calculate_score(
            face_similarity=face_result.get("similarity", 0),
            liveness_score=liveness_result.get("confidence", 0),
            liveness_passed=liveness_result.get("is_live", False),
            document_confidence=doc_result.get("confidence", 0) / 100,
            ocr_confidence=doc_result.get("confidence", 0),
            document_type_verified=doc_result.get("document_type") is not None,
            dob=request.dob or doc_result.get("dob"),
            estimated_age=estimated_age,
            is_unique_document=True,  # Would need DB check
            is_unique_face=True,  # Would need DB check
            fuzzy_match_found=False,  # Would need DB check
            device_fingerprint=request.device_fingerprint,
            previous_rejections=0,  # Would need DB check
        )

        return CompleteVerifyResponse(
            score=score_result["score"],
            decision=score_result["decision"],
            confidence=score_result["confidence"],
            face_similarity=face_result.get("similarity", 0),
            is_face_match=face_result.get("match", False),
            is_live=liveness_result.get("is_live", False),
            liveness_confidence=liveness_result.get("confidence", 0),
            document_type=doc_result.get("document_type"),
            document_fields={
                "name": doc_result.get("name"),
                "dob": doc_result.get("dob"),
                "document_number": doc_result.get("document_number"),
            },
            estimated_age=estimated_age,
            embedding_hash=embedding_hash,
            fuzzy_hashes=fuzzy_hashes,
            breakdown=score_result["breakdown"],
            reasons=score_result["reasons"],
            flags=score_result["flags"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Complete verification failed", error=str(e))
        return CompleteVerifyResponse(
            score=0,
            decision="manual_review",
            confidence="low",
            face_similarity=0,
            is_face_match=False,
            is_live=False,
            liveness_confidence=0,
            success=False,
            error=str(e)
        )


# ============= Agent Router Endpoint =============

@router.post("/agent/route", dependencies=[Depends(verify_api_key)])
async def route_query(query: str, context: Optional[dict] = None):
    """
    Route a query to appropriate handler using intent classification.
    Useful for generic/ambiguous requests.
    """
    agent_router = get_router()
    result = await agent_router.route(query, context)
    return result
