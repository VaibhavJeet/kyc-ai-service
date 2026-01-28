"""
TrustVault - Universal Trust Verification Platform
API-First SaaS for Identity and Business Verification

Features:
- Face verification with liveness detection
- Document OCR and extraction
- Unified Trust Score calculation
- Business verification (Reverse KYC)
- Webhook notifications
- Multi-tenant support (coming soon)

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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.api.v1.router import router as v1_router
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
    """Check for ML models and download if missing."""
    settings = get_settings()
    models_dir = Path(settings.model_cache_dir)

    required_models = [
        "gemma-3-270m-it-q4_k_m.gguf",
    ]

    missing = [m for m in required_models if not (models_dir / m).exists()]

    if missing:
        logger.info(f"Missing {len(missing)} models, attempting download...")
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
            from download_models import ModelDownloader

            downloader = ModelDownloader(str(models_dir))
            await downloader.download_all()
        except Exception as e:
            logger.warning(f"Auto-download failed: {e}. Run 'python scripts/download_models.py' manually.")
    else:
        logger.info("All models present. InsightFace will download automatically on first use.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup services"""
    settings = get_settings()

    logger.info(
        "trustvault.starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment
    )

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
        "trustvault.services_initialized",
        llm=llm_ok,
        face=face_ok,
        ocr=ocr_ok
    )

    yield

    # Cleanup
    logger.info("trustvault.shutting_down")
    llm.unload()
    face.unload()


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title="TrustVault",
    description="""
## Universal Trust Verification Platform

TrustVault provides comprehensive identity and business verification services.

### Features
- **Face Verification**: Compare selfie with document photo
- **Liveness Detection**: Anti-spoof protection
- **Document OCR**: Extract data from ID documents
- **Trust Score**: Unified verification confidence score
- **Business Verification**: Verify businesses (Reverse KYC)
- **Webhooks**: Real-time event notifications

### Authentication
All API endpoints require an `X-API-Key` header.

### Rate Limits
- 100 requests per minute per API key
- 10 concurrent requests per API key

### Support
For API support, contact: support@trustvault.io
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else "/docs",
    redoc_url="/redoc" if settings.debug else "/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Verification", "description": "Identity verification services"},
        {"name": "Trust Score", "description": "Trust score calculation"},
        {"name": "Protection", "description": "Fraud protection services"},
        {"name": "Webhooks", "description": "Webhook management"},
    ]
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
allowed_origins = settings.allowed_origins

if settings.debug:
    allowed_origins = ["*"]  # Allow all in debug mode

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=3600,
)

# Include API routers
app.include_router(v1_router, prefix="/api")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    TrustVault API root endpoint.
    Returns API information and available endpoints.
    """
    return {
        "name": "TrustVault",
        "version": settings.app_version,
        "description": "Universal Trust Verification Platform",
        "tagline": "Trust, Verified. Everywhere.",
        "documentation": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "verify": {
                "face": "/api/v1/verify/face",
                "liveness": "/api/v1/verify/liveness",
                "document": "/api/v1/verify/document",
                "kyc": "/api/v1/verify/kyc",
                "business": "/api/v1/verify/business",
            },
            "trust": {
                "score": "/api/v1/trust/score",
                "decision": "/api/v1/trust/decision",
            },
            "protect": {
                "scam_check": "/api/v1/protect/scam-check",
                "alert": "/api/v1/protect/alert",
            },
            "webhooks": "/api/v1/webhooks",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers
    )
