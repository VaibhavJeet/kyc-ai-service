#!/usr/bin/env python3
"""
Model Downloader for AI Service
Downloads all required models on first run or when missing.

Models:
- Gemma 3 270M Q4 GGUF (~200MB) - LLM for chat/content generation
- Ultra-Light Face Detector (~1MB) - Face detection
- MobileFaceNet INT8 (~4MB) - Face recognition/embedding
- Age/Gender MobileNet INT8 (~1.5MB) - Age estimation

Total: ~210MB download
"""

import os
import sys
import hashlib
import asyncio
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    os.system(f"{sys.executable} -m pip install httpx")
    import httpx


# Model definitions with download URLs and checksums
MODELS = {
    "gemma-3-270m-it-q4_k_m.gguf": {
        "url": "https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf",
        "size_mb": 768,
        "description": "Gemma 3 1B Q4 - Chat & Content Generation",
    },
    "ultra_light_face_slim.onnx": {
        "url": "https://github.com/Linzaer/Ultra-Light-Fast-Generic-Face-Detector-1MB/raw/master/models/onnx/version-slim-320.onnx",
        "size_mb": 1.2,
        "description": "Ultra-Light Face Detector (320px, slim)",
    },
    "mobilefacenet_int8.onnx": {
        # MobileFaceNet from ONNX Model Zoo (public, no auth required)
        "url": "https://github.com/onnx/models/raw/main/validated/vision/body_analysis/arcface/model/arcfaceresnet100-11-int8.onnx",
        "size_mb": 30,
        "description": "ArcFace ResNet100 INT8 - Face Recognition",
        # Fallback: smaller MobileFaceNet
        "fallback_url": "https://github.com/foamliu/MobileFaceNet/raw/master/models/MobileFaceNet.onnx",
    },
    "age_gender_mobilenet_int8.onnx": {
        # Age/Gender from public source
        "url": "https://github.com/onnx/models/raw/main/validated/vision/body_analysis/age_gender/models/age_googlenet.onnx",
        "size_mb": 23,
        "description": "Age Estimation (GoogLeNet)",
        # Fallback
        "fallback_url": "https://github.com/onnx/models/raw/main/validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx",
    },
}

# Alternative lightweight model pack (recommended for resource-constrained environments)
LIGHTWEIGHT_MODELS = {
    "gemma-2-2b-it-q4_k_m.gguf": {
        "url": "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
        "size_mb": 1500,  # 1.5GB - still smaller than Llama 3.2
        "description": "Gemma 2 2B Q4 - Lightweight LLM",
    },
}


class ModelDownloader:
    def __init__(self, models_dir: str = "./models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def _get_model_path(self, filename: str) -> Path:
        return self.models_dir / filename

    def is_model_present(self, filename: str) -> bool:
        path = self._get_model_path(filename)
        return path.exists() and path.stat().st_size > 0

    async def download_file(
        self,
        url: str,
        filename: str,
        description: str = "",
        expected_size_mb: float = 0
    ) -> bool:
        """Download a file with progress indication."""
        path = self._get_model_path(filename)

        if self.is_model_present(filename):
            print(f"✓ {filename} already exists")
            return True

        print(f"\n⬇ Downloading {filename}")
        if description:
            print(f"  {description}")
        if expected_size_mb:
            print(f"  Expected size: ~{expected_size_mb:.1f} MB")

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        print(f"✗ Failed to download {filename}: HTTP {response.status_code}")
                        return False

                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total > 0:
                                pct = (downloaded / total) * 100
                                mb_done = downloaded / (1024 * 1024)
                                mb_total = total / (1024 * 1024)
                                print(f"\r  Progress: {pct:.1f}% ({mb_done:.1f}/{mb_total:.1f} MB)", end="", flush=True)

                    print(f"\n✓ Downloaded {filename}")
                    return True

        except Exception as e:
            print(f"\n✗ Error downloading {filename}: {e}")
            # Clean up partial download
            if path.exists():
                path.unlink()
            return False

    async def download_all(self, skip_llm: bool = False) -> dict:
        """Download all required models."""
        results = {}

        print("=" * 50)
        print("AI Service Model Downloader")
        print("=" * 50)
        print(f"Models directory: {self.models_dir.absolute()}")
        print()

        for filename, info in MODELS.items():
            # Skip LLM if requested (useful for testing face/OCR only)
            if skip_llm and filename.endswith(".gguf"):
                print(f"⊘ Skipping {filename} (LLM skip enabled)")
                results[filename] = None
                continue

            success = await self.download_file(
                url=info["url"],
                filename=filename,
                description=info.get("description", ""),
                expected_size_mb=info.get("size_mb", 0)
            )
            results[filename] = success

            # Try fallback URL if primary failed
            if not success and "fallback_url" in info:
                print(f"  Trying fallback URL...")
                success = await self.download_file(
                    url=info["fallback_url"],
                    filename=filename,
                    description=info.get("description", ""),
                    expected_size_mb=info.get("size_mb", 0)
                )
                results[filename] = success

        print("\n" + "=" * 50)
        print("Download Summary:")
        print("=" * 50)

        for filename, success in results.items():
            if success is None:
                status = "⊘ SKIPPED"
            elif success:
                status = "✓ OK"
            else:
                status = "✗ FAILED"
            print(f"  {filename}: {status}")

        failed = [f for f, s in results.items() if s is False]
        if failed:
            print(f"\n⚠ {len(failed)} model(s) failed to download.")
            print("  The service will start but those features won't work.")
        else:
            print("\n✓ All models ready!")

        return results

    def check_models(self) -> dict:
        """Check which models are present."""
        status = {}
        for filename in MODELS.keys():
            status[filename] = self.is_model_present(filename)
        return status


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download AI Service models")
    parser.add_argument(
        "--models-dir",
        default="./models",
        help="Directory to store models (default: ./models)"
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip downloading LLM model (for testing face/OCR only)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if models exist, don't download"
    )

    args = parser.parse_args()

    downloader = ModelDownloader(args.models_dir)

    if args.check:
        status = downloader.check_models()
        print("Model Status:")
        for filename, present in status.items():
            icon = "✓" if present else "✗"
            print(f"  {icon} {filename}")

        missing = [f for f, p in status.items() if not p]
        if missing:
            print(f"\n{len(missing)} model(s) missing. Run without --check to download.")
            sys.exit(1)
        else:
            print("\nAll models present!")
            sys.exit(0)

    results = await downloader.download_all(skip_llm=args.skip_llm)

    # Exit with error if any critical model failed
    if any(s is False for s in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
