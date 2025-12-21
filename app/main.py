"""
AI Service - Ultra-Lightweight FastAPI Microservice
Handles: Chat, Content Generation, KYC Verification
Total footprint: ~325MB disk, ~750MB RAM peak
"""

import os
import sys
import asyncio
import structlog
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import router
from app.services.llm_service import get_llm_service
from app.services.face_service import get_face_service
from app.services.ocr_service import get_ocr_service

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def check_and_download_models():
    """Check for models and download if missing."""
    settings = get_settings()
    models_dir = Path(settings.model_cache_dir)

    # Required models
    required_models = [
        "gemma-3-270m-it-q4_k_m.gguf",
        "ultra_light_face_slim.onnx",
        "mobilefacenet_int8.onnx",
        "age_gender_mobilenet_int8.onnx",
    ]

    missing = [m for m in required_models if not (models_dir / m).exists()]

    if missing:
        logger.info(f"Missing {len(missing)} models, attempting download...")
        try:
            # Import and run downloader
            sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
            from download_models import ModelDownloader

            downloader = ModelDownloader(str(models_dir))
            await downloader.download_all()
        except Exception as e:
            logger.warning(f"Auto-download failed: {e}. Run 'python scripts/download_models.py' manually.")
    else:
        logger.info("All models present")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup services"""
    logger.info("Starting AI Service...")

    # Check and download models if missing
    await check_and_download_models()

    # Initialize services
    llm = get_llm_service()
    face = get_face_service()
    ocr = get_ocr_service()

    # Initialize in order of importance
    llm_ok = await llm.initialize()
    face_ok = await face.initialize()
    ocr_ok = await ocr.initialize()

    logger.info(
        "Services initialized",
        llm=llm_ok,
        face=face_ok,
        ocr=ocr_ok
    )

    yield

    # Cleanup
    logger.info("Shutting down AI Service...")
    llm.unload()
    face.unload()


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title="AI Service",
    description="Ultra-lightweight AI microservice for Chat, Content Generation, and KYC",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "AI Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/health",
            "chat": "/api/v1/chat",
            "title": "/api/v1/generate/title",
            "description": "/api/v1/generate/description",
            "budget": "/api/v1/generate/budget",
            "kyc_compare": "/api/v1/kyc/compare-faces",
            "kyc_liveness": "/api/v1/kyc/liveness",
            "kyc_ocr": "/api/v1/kyc/ocr",
            "kyc_verify": "/api/v1/kyc/verify",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
