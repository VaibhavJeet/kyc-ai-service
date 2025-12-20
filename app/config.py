"""
Configuration settings for KYC AI Microservice
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    WORKERS: int = 2
    DEBUG: bool = False

    # API settings
    API_KEY: Optional[str] = None  # Optional API key for authentication
    ALLOWED_ORIGINS: str = "*"  # CORS origins (comma-separated)

    # Model settings
    MODEL_CACHE_DIR: str = "/app/model_cache"
    USE_GPU: bool = False  # Set to True if CUDA available

    # Thresholds
    FACE_MATCH_THRESHOLD: float = 0.45  # ArcFace cosine similarity threshold
    FACE_MATCH_HIGH_CONFIDENCE: float = 0.55  # High confidence match
    LIVENESS_THRESHOLD: float = 0.7  # Anti-spoof threshold
    AGE_TOLERANCE: int = 10  # Years tolerance for age-DOB check

    # Logging
    LOG_LEVEL: str = "INFO"

    # Backend integration
    BACKEND_URL: Optional[str] = None  # NestJS backend URL for callbacks
    BACKEND_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
