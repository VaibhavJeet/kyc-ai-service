"""
TrustVault Health Check Endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.face_service import get_face_service
from app.services.ocr_service import get_ocr_service
from app.services.llm_service import get_llm_service

router = APIRouter()


class ServiceStatus(BaseModel):
    name: str
    available: bool
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: List[ServiceStatus]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of all TrustVault services.

    Returns:
        HealthResponse with status of each service
    """
    face = get_face_service()
    ocr = get_ocr_service()
    llm = get_llm_service()

    services = [
        ServiceStatus(
            name="face_verification",
            available=face.is_available(),
            details="InsightFace ArcFace (512-dim embeddings)"
        ),
        ServiceStatus(
            name="ocr",
            available=ocr.is_available(),
            details="Tesseract OCR"
        ),
        ServiceStatus(
            name="llm",
            available=llm.is_available(),
            details="Gemma 3 270M"
        ),
    ]

    all_healthy = all(s.available for s in services)
    any_healthy = any(s.available for s in services)

    if all_healthy:
        status = "healthy"
    elif any_healthy:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        version="1.0.0",
        services=services
    )


@router.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "TrustVault",
        "version": "1.0.0",
        "description": "Universal Trust Verification Platform",
        "docs": "/docs",
        "health": "/v1/health"
    }
