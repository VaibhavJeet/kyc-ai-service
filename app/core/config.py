"""
TrustVault Configuration
Universal Trust Verification Platform
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import structlog

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # =============  Application Settings =============
    app_name: str = "TrustVault"
    app_version: str = "1.0.0"
    app_description: str = "Universal Trust Verification Platform"
    debug: bool = False
    environment: str = "development"

    # =============  Server Settings =============
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # =============  Security Settings =============
    api_key: str = ""
    jwt_secret: str = ""
    allowed_origins: List[str] = ["*"]

    # =============  ML Model Settings =============
    model_cache_dir: str = "./models"

    # LLM - Gemma 3 270M Q4
    llm_model_path: str = "./models/gemma-3-270m-it-q4_k_m.gguf"
    llm_context_size: int = 2048
    llm_max_tokens: int = 512
    llm_temperature: float = 0.7
    llm_threads: int = 8

    # =============  Face Verification Settings =============
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
        description="Face match threshold. 0.85 = 85% similarity."
    )
    face_match_threshold_warning_low: float = 0.70
    face_match_threshold_warning_high: float = 0.90
    face_embedding_dim: int = 512
    enable_age_adjustment: bool = False

    # =============  Liveness Settings =============
    liveness_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    liveness_min_blur_variance: float = 50.0
    liveness_min_saturation: float = 0.05
    liveness_min_face_ratio: float = 0.1
    liveness_max_face_ratio: float = 0.8
    min_face_size: int = 80

    # =============  OCR Settings =============
    tesseract_lang: str = "eng"
    tesseract_config: str = "--oem 3 --psm 6"

    # =============  Trust Score Settings =============
    trust_auto_approve_threshold: float = 0.85
    trust_manual_review_threshold: float = 0.50
    trust_rejection_threshold: float = 0.50

    # =============  Rate Limiting =============
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # =============  Webhook Settings =============
    webhook_timeout: int = 30
    webhook_retry_count: int = 3
    webhook_retry_delay: int = 60

    # =============  Feature Flags =============
    enable_business_verification: bool = True
    enable_consent_recording: bool = True
    enable_scam_detection: bool = False
    enable_deepfake_detection: bool = False

    # =============  Database (Optional) =============
    database_url: str = "sqlite:///./trustvault.db"
    redis_url: Optional[str] = None

    # =============  Storage (Optional) =============
    storage_backend: str = "local"
    storage_path: str = "./storage"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None

    @field_validator('face_match_threshold')
    @classmethod
    def validate_face_threshold(cls, v: float) -> float:
        """Validate face match threshold"""
        if v < 0.70:
            logger.warning(
                "face_match_threshold.too_low",
                threshold=v,
                recommendation="Use threshold >= 0.75 for production"
            )
        if v > 0.90:
            logger.warning(
                "face_match_threshold.too_high",
                threshold=v,
                recommendation="Use threshold <= 0.90"
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
