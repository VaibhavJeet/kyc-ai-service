"""
KYC AI Microservice - Main Application
FastAPI server for identity verification with AI models
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .api.routes import router
from .services.face_recognition import face_recognition_service
from .services.anti_spoof import anti_spoof_service
from .services.document_ocr import document_ocr_service

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - initialize models on startup"""
    logger.info("Starting KYC AI Microservice...")

    # Initialize models in order of importance
    models_status = {}

    # 1. Face recognition (most critical)
    try:
        success = face_recognition_service.initialize()
        models_status["face_recognition"] = success
        if success:
            logger.info("Face recognition service initialized")
        else:
            logger.warning("Face recognition service failed to initialize")
    except Exception as e:
        logger.error("Face recognition initialization error", error=str(e))
        models_status["face_recognition"] = False

    # 2. Anti-spoof
    try:
        success = anti_spoof_service.initialize()
        models_status["anti_spoof"] = success
        if success:
            logger.info("Anti-spoof service initialized")
    except Exception as e:
        logger.error("Anti-spoof initialization error", error=str(e))
        models_status["anti_spoof"] = False

    # 3. Document OCR
    try:
        success = document_ocr_service.initialize()
        models_status["document_ocr"] = success
        if success:
            logger.info("Document OCR service initialized")
    except Exception as e:
        logger.error("Document OCR initialization error", error=str(e))
        models_status["document_ocr"] = False

    logger.info("Model initialization complete", status=models_status)

    yield

    # Cleanup on shutdown
    logger.info("Shutting down KYC AI Microservice...")


# Create FastAPI app
app = FastAPI(
    title="KYC AI Microservice",
    description="""
    AI-powered identity verification service for KYC processing.

    ## Features
    - **Face Recognition**: ArcFace-based 512-dim embeddings for accurate face matching
    - **Liveness Detection**: Multi-layer anti-spoofing (texture, frequency, color, moiré)
    - **Document OCR**: PaddleOCR for extracting text from identity documents
    - **Identity Scoring**: Unified scoring combining all verification signals

    ## Document Types Supported
    - Aadhaar Card
    - PAN Card
    - Passport (with MRZ parsing)
    - Driving License
    - Voter ID

    ## Privacy
    - No images are stored
    - Only privacy-preserving hashes are used for deduplication
    - All processing happens in-memory
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Include API routes
app.include_router(router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "KYC AI Microservice",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.DEBUG,
    )
