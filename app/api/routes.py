"""
FastAPI routes for KYC AI Microservice
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from datetime import date, datetime
import numpy as np
import structlog

from .schemas import (
    FaceCompareRequest,
    FaceCompareResponse,
    FaceEmbeddingRequest,
    FaceEmbeddingResponse,
    LivenessRequest,
    LivenessResponse,
    DocumentOCRRequest,
    DocumentOCRResponse,
    UnifiedVerifyRequest,
    UnifiedVerifyResponse,
    IdentityScoreRequest,
    IdentityScoreResponse,
    HealthResponse,
)
from ..services.face_recognition import face_recognition_service
from ..services.anti_spoof import anti_spoof_service
from ..services.document_ocr import document_ocr_service
from ..services.identity_scoring import identity_scoring_service, VerificationInput
from ..config import settings

logger = structlog.get_logger()

router = APIRouter()

# Track service start time
_start_time = datetime.now()


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify API key if configured"""
    if settings.API_KEY is None:
        return True
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# ============= Health Check =============


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check service health and model status"""
    uptime = (datetime.now() - _start_time).total_seconds()

    models_status = {
        "face_recognition": face_recognition_service.is_initialized,
        "anti_spoof": anti_spoof_service.is_initialized,
        "document_ocr": document_ocr_service.is_initialized,
    }

    all_healthy = all(models_status.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version="1.0.0",
        models=models_status,
        uptime_seconds=uptime,
    )


# ============= Face Verification =============


@router.post("/verify/face", response_model=FaceCompareResponse, tags=["Face"])
async def compare_faces(
    request: FaceCompareRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Compare faces between document photo and selfie.
    Returns similarity score and match decision.
    """
    logger.info("Face comparison request received")

    if not face_recognition_service.is_initialized:
        raise HTTPException(status_code=503, detail="Face recognition service not ready")

    result = face_recognition_service.compare_faces(
        request.document_image,
        request.selfie_image,
    )

    if result.get("error"):
        return FaceCompareResponse(
            similarity=0.0,
            is_match=False,
            confidence="low",
            error=result["error"],
        )

    # Generate embedding hash for deduplication
    selfie_analysis = face_recognition_service.get_face_analysis(request.selfie_image)
    embedding_hash = None
    fuzzy_hashes = None

    if selfie_analysis:
        embedding = np.array(selfie_analysis["embedding"])
        embedding_hash = face_recognition_service.generate_embedding_hash(embedding)
        fuzzy_hashes = face_recognition_service.generate_fuzzy_hashes(embedding)

    return FaceCompareResponse(
        similarity=result["similarity"],
        is_match=result["is_match"],
        confidence=result["confidence"],
        document_age=result.get("face1_age"),
        selfie_age=result.get("face2_age"),
        embedding_hash=embedding_hash,
        fuzzy_hashes=fuzzy_hashes,
    )


@router.post("/verify/embedding", response_model=FaceEmbeddingResponse, tags=["Face"])
async def get_face_embedding(
    request: FaceEmbeddingRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Extract face embedding from image.
    Returns 512-dimensional ArcFace embedding.
    """
    if not face_recognition_service.is_initialized:
        raise HTTPException(status_code=503, detail="Face recognition service not ready")

    analysis = face_recognition_service.get_face_analysis(request.image)

    if not analysis:
        return FaceEmbeddingResponse(error="No face detected in image")

    embedding = np.array(analysis["embedding"])
    embedding_hash = face_recognition_service.generate_embedding_hash(embedding)
    fuzzy_hashes = face_recognition_service.generate_fuzzy_hashes(embedding)

    return FaceEmbeddingResponse(
        embedding=analysis["embedding"],
        embedding_hash=embedding_hash,
        fuzzy_hashes=fuzzy_hashes,
        age=analysis.get("age"),
        gender=analysis.get("gender"),
        det_score=analysis.get("det_score"),
    )


# ============= Liveness Detection =============


@router.post("/verify/liveness", response_model=LivenessResponse, tags=["Liveness"])
async def check_liveness(
    request: LivenessRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Perform passive liveness detection on selfie.
    Detects presentation attacks (print, screen, mask).
    """
    if not anti_spoof_service.is_initialized:
        raise HTTPException(status_code=503, detail="Anti-spoof service not ready")

    result = anti_spoof_service.analyze(request.image)

    if result.get("error"):
        return LivenessResponse(
            is_live=False,
            confidence=0.0,
            scores={},
            reason=result["error"],
            error=result["error"],
        )

    return LivenessResponse(
        is_live=result["is_live"],
        confidence=result["confidence"],
        scores=result["scores"],
        reason=result["reason"],
    )


# ============= Document Verification =============


@router.post("/verify/document", response_model=DocumentOCRResponse, tags=["Document"])
async def verify_document(
    request: DocumentOCRRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Extract text and verify document type.
    Supports Aadhaar, PAN, Passport, Driving License, Voter ID.
    """
    if not document_ocr_service.is_initialized:
        raise HTTPException(status_code=503, detail="OCR service not ready")

    # Detect document type
    type_result = document_ocr_service.detect_document_type(request.image)

    if type_result.get("error"):
        return DocumentOCRResponse(error=type_result["error"])

    detected_type = type_result["document_type"]
    type_match = detected_type == request.expected_type if request.expected_type else True

    # Extract fields
    fields_result = document_ocr_service.extract_fields(request.image, detected_type)

    return DocumentOCRResponse(
        document_type=detected_type,
        type_confidence=type_result["confidence"],
        type_match=type_match,
        fields=fields_result.get("fields", {}),
        raw_text=fields_result.get("raw_text"),
        ocr_confidence=0.8 if fields_result.get("fields") else 0.5,
    )


# ============= Unified Verification =============


@router.post("/verify/complete", response_model=UnifiedVerifyResponse, tags=["Unified"])
async def complete_verification(
    request: UnifiedVerifyRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Perform complete KYC verification in one call.
    Combines face matching, liveness, document OCR, and scoring.
    """
    logger.info("Complete verification request received")

    errors = []

    # 1. Face comparison
    face_result = {"similarity": 0.0, "is_match": False, "confidence": "low"}
    selfie_age = None
    embedding_hash = None
    fuzzy_hashes = None

    if face_recognition_service.is_initialized:
        face_result = face_recognition_service.compare_faces(
            request.document_image,
            request.selfie_image,
        )

        # Get selfie analysis for age and hashes
        selfie_analysis = face_recognition_service.get_face_analysis(request.selfie_image)
        if selfie_analysis:
            selfie_age = selfie_analysis.get("age")
            embedding = np.array(selfie_analysis["embedding"])
            embedding_hash = face_recognition_service.generate_embedding_hash(embedding)
            fuzzy_hashes = face_recognition_service.generate_fuzzy_hashes(embedding)
    else:
        errors.append("Face recognition service not available")

    # 2. Liveness detection
    liveness_result = {"is_live": False, "confidence": 0.5}
    if anti_spoof_service.is_initialized:
        liveness_result = anti_spoof_service.analyze(request.selfie_image)
    else:
        errors.append("Liveness service not available")

    # 3. Document verification
    doc_type = None
    doc_fields = {}
    doc_confidence = 0.5

    if document_ocr_service.is_initialized:
        type_result = document_ocr_service.detect_document_type(request.document_image)
        doc_type = type_result.get("document_type")
        doc_confidence = type_result.get("confidence", 0.5)

        if doc_type:
            fields_result = document_ocr_service.extract_fields(
                request.document_image, doc_type
            )
            doc_fields = fields_result.get("fields", {})
    else:
        errors.append("OCR service not available")

    # 4. Parse DOB
    dob = None
    if request.dob:
        try:
            dob = datetime.strptime(request.dob, "%Y-%m-%d").date()
        except ValueError:
            pass

    # 5. Calculate identity score
    verification_input = VerificationInput(
        face_similarity=face_result.get("similarity", 0.0),
        face_match_source="arcface" if face_recognition_service.is_initialized else "unavailable",
        liveness_score=liveness_result.get("confidence", 0.5),
        liveness_passed=liveness_result.get("is_live", False),
        document_confidence=doc_confidence,
        document_type_verified=(doc_type == request.expected_document_type)
        if request.expected_document_type
        else True,
        ocr_confidence=0.8 if doc_fields else 0.5,
        dob=dob,
        estimated_age=selfie_age,
        device_fingerprint=request.device_fingerprint,
        ip_address=request.ip_address,
    )

    scoring_result = identity_scoring_service.score(verification_input)

    # Add age consistency to breakdown if available
    age_consistency = None
    if dob and selfie_age:
        age_consistency = identity_scoring_service.calculate_age_consistency(dob, selfie_age)

    return UnifiedVerifyResponse(
        score=scoring_result.score,
        decision=scoring_result.decision,
        confidence=scoring_result.confidence,
        breakdown=scoring_result.breakdown,
        reasons=scoring_result.reasons + errors,
        flags=scoring_result.flags,
        face_similarity=face_result.get("similarity", 0.0),
        is_face_match=face_result.get("is_match", False),
        is_live=liveness_result.get("is_live", False),
        liveness_confidence=liveness_result.get("confidence", 0.5),
        document_type=doc_type,
        document_fields=doc_fields,
        estimated_age=selfie_age,
        age_consistency=age_consistency,
        embedding_hash=embedding_hash,
        fuzzy_hashes=fuzzy_hashes,
        error="; ".join(errors) if errors else None,
    )


# ============= Identity Scoring =============


@router.post("/score/identity", response_model=IdentityScoreResponse, tags=["Scoring"])
async def calculate_identity_score(
    request: IdentityScoreRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Calculate identity verification score from provided signals.
    Used when face matching and liveness are done on-device.
    """
    # Parse DOB
    dob = None
    if request.dob:
        try:
            dob = datetime.strptime(request.dob, "%Y-%m-%d").date()
        except ValueError:
            pass

    verification_input = VerificationInput(
        face_similarity=request.face_similarity,
        face_match_source="client",
        liveness_score=request.liveness_score,
        liveness_passed=request.liveness_passed,
        document_confidence=request.document_confidence,
        document_type_verified=request.document_type_verified,
        ocr_confidence=request.ocr_confidence,
        dob=dob,
        estimated_age=request.estimated_age,
        is_unique_document=request.is_unique_document,
        is_unique_face=request.is_unique_face,
        fuzzy_match_found=request.fuzzy_match_found,
        device_fingerprint=request.device_fingerprint,
        previous_rejections=request.previous_rejections,
    )

    scoring_result = identity_scoring_service.score(verification_input)

    return IdentityScoreResponse(
        score=scoring_result.score,
        decision=scoring_result.decision,
        confidence=scoring_result.confidence,
        breakdown=scoring_result.breakdown,
        reasons=scoring_result.reasons,
        flags=scoring_result.flags,
    )
