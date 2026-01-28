"""
TrustVault Trust Score Endpoints
Unified trust scoring and decision engine
"""

import structlog
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends

from app.api.schemas.trust import (
    TrustScoreRequest, TrustScoreResponse,
    TrustDecisionRequest, TrustDecisionResponse,
)
from app.middleware.auth import verify_api_key
from app.core.trust.score import TrustScoreEngine

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/score", response_model=TrustScoreResponse, dependencies=[Depends(verify_api_key)])
async def calculate_trust_score(request: TrustScoreRequest):
    """
    Calculate unified trust score from verification signals.

    Combines multiple factors:
    - Face similarity score
    - Liveness detection score
    - Document verification confidence
    - Age consistency
    - Uniqueness checks

    Returns a score (0-100) with decision recommendation.
    """
    trust_engine = TrustScoreEngine()

    try:
        result = await trust_engine.calculate(
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

        return TrustScoreResponse(
            score=result["score"],
            decision=result["decision"],
            confidence=result["confidence"],
            breakdown=result["breakdown"],
            reasons=result["reasons"],
            flags=result["flags"],
        )

    except Exception as e:
        logger.error("trust.score.failed", error=str(e))
        raise HTTPException(status_code=500, detail="Trust score calculation failed")


@router.post("/decision", response_model=TrustDecisionResponse, dependencies=[Depends(verify_api_key)])
async def get_trust_decision(request: TrustDecisionRequest):
    """
    Get verification decision based on trust score.

    Decisions:
    - **auto_verified**: Score >= 85, automatically approved
    - **manual_review**: Score 50-84, needs human review
    - **rejected**: Score < 50, automatically rejected

    Custom thresholds can be configured per tenant.
    """
    trust_engine = TrustScoreEngine()

    try:
        decision = trust_engine.get_decision(
            score=request.score,
            custom_thresholds=request.custom_thresholds,
        )

        return TrustDecisionResponse(
            decision=decision["decision"],
            confidence=decision["confidence"],
            recommended_action=decision["recommended_action"],
            next_steps=decision["next_steps"],
        )

    except Exception as e:
        logger.error("trust.decision.failed", error=str(e))
        raise HTTPException(status_code=500, detail="Decision calculation failed")


@router.get("/score/{verification_id}", response_model=TrustScoreResponse, dependencies=[Depends(verify_api_key)])
async def get_trust_score(verification_id: str):
    """
    Retrieve trust score for a previous verification.

    - **verification_id**: ID of the verification to retrieve
    """
    # TODO: Implement database lookup
    raise HTTPException(status_code=501, detail="Not implemented - requires database")
