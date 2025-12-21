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
    llm_threads: int = 4  # CPU threads for inference

    # Face Detection - Ultra-Light Face Detector (~1-2MB, ~30-50MB RAM)
    face_detector_model: str = "./models/ultra_light_face_slim.onnx"
    face_detection_threshold: float = 0.7

    # Face Recognition - MobileFaceNet INT8 (~3-5MB, ~40-60MB RAM)
    face_recognition_model: str = "./models/mobilefacenet_int8.onnx"
    face_match_threshold: float = 0.45
    face_embedding_dim: int = 128

    # Age/Gender - MobileNetV2 INT8 (~1.5MB, ~20-30MB RAM)
    age_gender_model: str = "./models/age_gender_mobilenet_int8.onnx"

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
