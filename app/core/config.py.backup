"""
Configuration for AI Service
Ultra-lightweight settings - Sub-1GB RAM, Sub-350MB disk
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


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
    face_detection_threshold: float = 0.7
    face_match_threshold: float = 0.85  # 85% similarity for production KYC
    face_embedding_dim: int = 512  # InsightFace ArcFace ResNet100

    # InsightFace provides integrated age/gender estimation
    # No separate models needed - all included in buffalo_l pack

    # OCR - Tesseract (~30MB disk, ~80MB RAM)
    tesseract_lang: str = "eng"
    tesseract_config: str = "--oem 3 --psm 6"

    # KYC Settings
    liveness_threshold: float = 0.6
    min_face_size: int = 80

    # Model cache directory
    model_cache_dir: str = "./models"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
