"""
TrustVault Verification Endpoints
Core verification services: Face, Liveness, Document, KYC, Business
"""

import base64
import cv2
import numpy as np
import structlog
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from app.api.schemas.verify import (
    FaceVerifyRequest, FaceVerifyResponse,
    LivenessRequest, LivenessResponse,
    DocumentVerifyRequest, DocumentVerifyResponse,
    KYCVerifyRequest, KYCVerifyResponse,
    BusinessVerifyRequest, BusinessVerifyResponse,
)
from app.api.schemas.common import BaseResponse
from app.middleware.auth import verify_api_key
from app.services.face_service import get_face_service
from app.services.ocr_service import get_ocr_service
from app.core.trust.score import TrustScoreEngine

logger = structlog.get_logger(__name__)
router = APIRouter()


# ============= Image Helpers =============

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_DIMENSION = 4096
MIN_IMAGE_DIMENSION = 100


def decode_base64_image(base64_str: str) -> np.ndarray:
    """Decode base64 string to numpy array image with validation"""
    try:
        # Remove data URL prefix if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        # Validate size
        if len(base64_str) > int(MAX_IMAGE_SIZE * 1.37):
            raise HTTPException(status_code=413, detail="Image too large")

        # Decode
        img_bytes = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image")

        # Validate dimensions
        height, width = img.shape[:2]
        if height < MIN_IMAGE_DIMENSION or width < MIN_IMAGE_DIMENSION:
            raise HTTPException(status_code=400, detail=f"Image too small. Min: {MIN_IMAGE_DIMENSION}px")
        if height > MAX_IMAGE_DIMENSION or width > MAX_IMAGE_DIMENSION:
            raise HTTPException(status_code=413, detail=f"Image too large. Max: {MAX_IMAGE_DIMENSION}px")

        return img

    except HTTPException:
        raise
    except Exception as e:
        logger.error("image.decode_failed", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid image")


# ============= Verification Endpoints =============

@router.post("/face", response_model=FaceVerifyResponse, dependencies=[Depends(verify_api_key)])
async def verify_face(request: FaceVerifyRequest):
    """
    Compare two face images (selfie vs document photo).

    - **selfie_base64**: Base64 encoded selfie image
    - **document_base64**: Base64 encoded ID document photo

    Returns face match result with similarity score.
    """
    face = get_face_service()

    if not face.is_available():
        raise HTTPException(status_code=503, detail="Face service unavailable")

    try:
        selfie = decode_base64_image(request.selfie_base64)
        document = decode_base64_image(request.document_base64)

        result = await face.compare_faces(selfie, document)

        return FaceVerifyResponse(
            match=result["match"],
            similarity=result["similarity"],
            threshold=result.get("threshold", 0.85),
            confidence=result.get("confidence", "medium"),
            recommendation=result.get("recommendation", "MANUAL_REVIEW"),
            face_detected_selfie=True,
            face_detected_document=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("verify.face.failed", error=str(e))
        raise HTTPException(status_code=500, detail="Face verification failed")


@router.post("/liveness", response_model=LivenessResponse, dependencies=[Depends(verify_api_key)])
async def verify_liveness(request: LivenessRequest):
    """
    Check if image is a live capture (anti-spoof detection).

    - **image_base64**: Base64 encoded face image

    Returns liveness score and detection result.
    """
    face = get_face_service()

    if not face.is_available():
        raise HTTPException(status_code=503, detail="Face service unavailable")

    try:
        image = decode_base64_image(request.image_base64)
        result = await face.check_liveness(image)

        return LivenessResponse(
            is_live=result["is_live"],
            score=result["score"],
            details=result.get("details"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("verify.liveness.failed", error=str(e))
        raise HTTPException(status_code=500, detail="Liveness check failed")


@router.post("/document", response_model=DocumentVerifyResponse, dependencies=[Depends(verify_api_key)])
async def verify_document(request: DocumentVerifyRequest):
    """
    Extract and verify information from ID document.

    - **image_base64**: Base64 encoded document image
    - **document_type**: Expected document type (optional)

    Returns extracted document data (name, DOB, document number, etc.)
    """
    ocr = get_ocr_service()

    if not ocr.is_available():
        raise HTTPException(status_code=503, detail="OCR service unavailable")

    try:
        image = decode_base64_image(request.image_base64)
        result = await ocr.extract_document_info(image, request.document_type or "auto")

        return DocumentVerifyResponse(
            document_type=result.get("document_type"),
            document_number=result.get("document_number"),
            name=result.get("name"),
            dob=result.get("dob"),
            raw_text=result.get("raw_text", ""),
            confidence=result.get("confidence", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("verify.document.failed", error=str(e))
        raise HTTPException(status_code=500, detail="Document verification failed")


@router.post("/kyc", response_model=KYCVerifyResponse, dependencies=[Depends(verify_api_key)])
async def verify_kyc(request: KYCVerifyRequest):
    """
    Complete KYC verification flow:
    1. Face comparison (selfie vs document)
    2. Liveness check
    3. Document OCR and extraction
    4. Trust score calculation

    Returns comprehensive verification result with trust score.
    """
    face = get_face_service()
    ocr = get_ocr_service()
    trust_engine = TrustScoreEngine()

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
            doc_result = await ocr.extract_document_info(document, request.document_type or "auto")

        # 4. Calculate trust score
        trust_result = await trust_engine.calculate(
            face_similarity=face_result.get("similarity", 0),
            liveness_score=liveness_result.get("score", 0),
            liveness_passed=liveness_result.get("is_live", False),
            document_confidence=doc_result.get("confidence", 0) / 100,
            ocr_confidence=doc_result.get("confidence", 0),
        )

        # Overall decision
        face_pass = face_result.get("match", False)
        liveness_pass = liveness_result.get("is_live", False)
        overall_pass = face_pass and liveness_pass

        return KYCVerifyResponse(
            # Face results
            face_match=face_result.get("match", False),
            face_similarity=face_result.get("similarity", 0),

            # Liveness results
            is_live=liveness_result.get("is_live", False),
            liveness_score=liveness_result.get("score", 0),

            # Document results
            document_type=doc_result.get("document_type"),
            document_number=doc_result.get("document_number"),
            extracted_name=doc_result.get("name"),
            extracted_dob=doc_result.get("dob"),

            # Trust score
            trust_score=trust_result["score"],
            decision=trust_result["decision"],
            confidence=trust_result["confidence"],

            # Overall
            overall_pass=overall_pass,
            reasons=trust_result.get("reasons", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("verify.kyc.failed", error=str(e))
        raise HTTPException(status_code=500, detail="KYC verification failed")


@router.post("/business", response_model=BusinessVerifyResponse, dependencies=[Depends(verify_api_key)])
async def verify_business(request: BusinessVerifyRequest):
    """
    Reverse KYC - Verify a business/caller identity.

    Use this to verify if a business or caller is legitimate
    (e.g., "Is this really my bank calling?")

    - **business_name**: Name of the business to verify
    - **phone_number**: Phone number claiming to be from the business
    - **registration_number**: Business registration number (optional)
    """
    # TODO: Implement business verification logic
    # This would integrate with:
    # - Business registry APIs
    # - Phone number databases
    # - Known scam databases

    return BusinessVerifyResponse(
        is_verified=False,
        business_name=request.business_name,
        verification_status="pending",
        risk_level="unknown",
        message="Business verification coming soon. This is a placeholder.",
    )
