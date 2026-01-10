"""
Configuration for AI Service
Ultra-lightweight settings - Sub-1GB RAM, Sub-350MB disk
"""

import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import structlog

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Settings
    api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False

    # LLM Settings - Gemma 3 270M Q4 (~200MB model, ~450MB RAM)
    llm_model_path: str = "./models/gemma-3-270m-it-q4_k_m.gguf"
    llm_context_size: int = 2048  # Small context for memory efficiency
    llm_max_tokens: int = 512
    llm_temperature: float = 0.7
    llm_threads: int = 8  # CPU threads for inference (increased from 4 for better performance)

    # Face Detection & Recognition - InsightFace buffalo_l (~300MB models)
    # Production-grade face recognition with 512-dim ArcFace embeddings
    face_detection_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Face detection confidence threshold"
    )
    face_match_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Face match threshold for KYC. 0.85 = 85% similarity for production."
    )
    face_match_threshold_warning_low: float = 0.70  # Warn if threshold < 70%
    face_match_threshold_warning_high: float = 0.90  # Warn if threshold > 90%
    face_embedding_dim: int = 512  # InsightFace ArcFace ResNet100
    enable_age_adjustment: bool = False  # Disabled by default for security

    # InsightFace provides integrated age/gender estimation
    # No separate models needed - all included in buffalo_l pack

    # OCR - Tesseract (~30MB disk, ~80MB RAM)
    tesseract_lang: str = "eng"
    tesseract_config: str = "--oem 3 --psm 6"

    # KYC Settings - Liveness Detection
    liveness_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    liveness_min_blur_variance: float = 50.0  # Laplacian variance threshold
    liveness_min_saturation: float = 0.05  # Minimum color saturation (0-1)
    liveness_min_face_ratio: float = 0.1  # Min face size relative to image
    liveness_max_face_ratio: float = 0.8  # Max face size relative to image
    min_face_size: int = 80

    # Model cache directory
    model_cache_dir: str = "./models"

    @field_validator('face_match_threshold')
    @classmethod
    def validate_face_threshold(cls, v: float) -> float:
        """Validate face match threshold and log warnings"""
        if v < 0.70:
            logger.warning(
                "face_match_threshold.too_low",
                threshold=v,
                risk="May allow impersonation attacks (sibling/twin acceptance)",
                recommendation="Use threshold >= 0.75 for production KYC"
            )
        if v > 0.90:
            logger.warning(
                "face_match_threshold.too_high",
                threshold=v,
                risk="May cause false rejections of legitimate users",
                recommendation="Use threshold <= 0.90 to avoid UX issues"
            )

        logger.info(
            "face_match_threshold.configured",
            threshold=v,
            description=f"{int(v*100)}% similarity required for face match"
        )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
