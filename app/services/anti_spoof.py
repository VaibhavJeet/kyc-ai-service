"""
Anti-Spoofing Service for Liveness Detection
Detects presentation attacks: printed photos, screen replays, 3D masks
"""

import numpy as np
from typing import Optional, Dict, Any, Tuple
import cv2
from PIL import Image
import io
import base64
import structlog
from skimage import feature as skimage_feature

from ..config import settings

logger = structlog.get_logger()


class AntiSpoofService:
    """
    Multi-layer anti-spoofing detection.
    Combines multiple signals for robust liveness verification:
    1. Texture analysis (LBP patterns)
    2. Frequency domain analysis (FFT)
    3. Color space analysis
    4. Moiré pattern detection
    5. Reflection analysis
    """

    def __init__(self):
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize anti-spoof models"""
        try:
            logger.info("Initializing Anti-Spoof service...")
            self._initialized = True
            logger.info("Anti-Spoof service initialized")
            return True
        except Exception as e:
            logger.error("Failed to initialize Anti-Spoof", error=str(e))
            return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _decode_image(self, image_data: str) -> Optional[np.ndarray]:
        """Decode base64 image to numpy array"""
        try:
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)
            pil_image = Image.open(io.BytesIO(image_bytes))
            rgb_array = np.array(pil_image.convert("RGB"))
            return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error("Failed to decode image", error=str(e))
            return None

    def _analyze_texture(self, gray_image: np.ndarray) -> float:
        """
        Analyze texture using Local Binary Patterns (LBP).
        Real faces have more natural texture variation than printed/screen.
        """
        try:
            # Compute LBP
            radius = 3
            n_points = 8 * radius

            lbp = skimage_feature.local_binary_pattern(
                gray_image, n_points, radius, method="uniform"
            )

            # Calculate histogram
            n_bins = int(lbp.max() + 1)
            hist, _ = np.histogram(lbp.ravel(), bins=n_bins, range=(0, n_bins), density=True)

            # Real faces have more uniform LBP distribution
            # Printed/screen images have peaked distributions
            entropy = -np.sum(hist * np.log2(hist + 1e-10))
            max_entropy = np.log2(n_bins)

            # Normalize to 0-1 (higher = more likely real)
            texture_score = entropy / max_entropy

            return float(texture_score)
        except Exception as e:
            logger.error("Texture analysis failed", error=str(e))
            return 0.5

    def _analyze_frequency(self, gray_image: np.ndarray) -> float:
        """
        Analyze frequency domain using FFT.
        Screen replays have distinct high-frequency patterns from pixel grid.
        """
        try:
            # Apply FFT
            f_transform = np.fft.fft2(gray_image)
            f_shift = np.fft.fftshift(f_transform)
            magnitude = np.abs(f_shift)

            # Get image dimensions
            rows, cols = gray_image.shape
            crow, ccol = rows // 2, cols // 2

            # Analyze high-frequency content
            mask_size = min(rows, cols) // 4
            high_freq_mask = np.ones((rows, cols), dtype=bool)
            high_freq_mask[crow - mask_size:crow + mask_size, ccol - mask_size:ccol + mask_size] = False

            high_freq_energy = np.mean(magnitude[high_freq_mask])
            total_energy = np.mean(magnitude)

            # Real images have more balanced frequency distribution
            ratio = high_freq_energy / (total_energy + 1e-10)

            # Screens have abnormally high or low high-frequency content
            # Normal range is roughly 0.3-0.7
            if 0.2 < ratio < 0.8:
                freq_score = 1.0 - abs(ratio - 0.5)
            else:
                freq_score = 0.3

            return float(freq_score)
        except Exception as e:
            logger.error("Frequency analysis failed", error=str(e))
            return 0.5

    def _analyze_color_distribution(self, bgr_image: np.ndarray) -> float:
        """
        Analyze color distribution.
        Real skin has characteristic color distribution in YCrCb space.
        """
        try:
            # Convert to YCrCb
            ycrcb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2YCrCb)

            # Skin color range in YCrCb
            # Cr: 133-173, Cb: 77-127 (typical skin tones)
            cr_channel = ycrcb[:, :, 1]
            cb_channel = ycrcb[:, :, 2]

            # Check if color distribution matches skin
            cr_mean = np.mean(cr_channel)
            cb_mean = np.mean(cb_channel)
            cr_std = np.std(cr_channel)
            cb_std = np.std(cb_channel)

            # Real skin has specific range and variance
            cr_score = 1.0 if 133 <= cr_mean <= 173 else 0.5
            cb_score = 1.0 if 77 <= cb_mean <= 127 else 0.5

            # Real skin has natural variance
            variance_score = min(1.0, (cr_std + cb_std) / 40)

            color_score = (cr_score + cb_score + variance_score) / 3

            return float(color_score)
        except Exception as e:
            logger.error("Color analysis failed", error=str(e))
            return 0.5

    def _detect_moire(self, gray_image: np.ndarray) -> float:
        """
        Detect moiré patterns (indicates screen capture).
        Moiré appears as regular wave patterns from screen pixel grid.
        """
        try:
            # Apply Gabor filter at multiple orientations
            moire_detected = False
            orientations = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]

            for theta in orientations:
                kernel = cv2.getGaborKernel(
                    (21, 21), 5.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F
                )
                filtered = cv2.filter2D(gray_image, cv2.CV_32F, kernel)

                # Check for periodic patterns
                autocorr = cv2.matchTemplate(filtered, filtered, cv2.TM_CCORR_NORMED)
                peaks = np.sum(autocorr > 0.9)

                if peaks > 10:  # Multiple correlation peaks = periodic pattern
                    moire_detected = True
                    break

            # No moiré = likely real (score 1.0)
            return 0.2 if moire_detected else 1.0
        except Exception as e:
            logger.error("Moiré detection failed", error=str(e))
            return 0.5

    def _analyze_reflection(self, bgr_image: np.ndarray) -> float:
        """
        Analyze specular reflections (eye reflections indicate live person).
        Real eyes have characteristic catchlight patterns.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)

            # Detect bright spots (potential reflections)
            _, bright_spots = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)

            # Count bright regions
            contours, _ = cv2.findContours(
                bright_spots, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            # Real eyes typically have 1-4 small bright reflections
            valid_reflections = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 5 < area < 500:  # Small bright spots
                    valid_reflections += 1

            # Score based on reflection count
            if 1 <= valid_reflections <= 6:
                reflection_score = 0.8 + min(valid_reflections, 4) * 0.05
            elif valid_reflections > 6:
                reflection_score = 0.6  # Too many might be screen glare
            else:
                reflection_score = 0.3  # No reflections suspicious

            return float(min(1.0, reflection_score))
        except Exception as e:
            logger.error("Reflection analysis failed", error=str(e))
            return 0.5

    def analyze(self, image_data: str) -> Dict[str, Any]:
        """
        Perform comprehensive anti-spoof analysis.
        Returns liveness score and breakdown of individual checks.
        """
        result = {
            "is_live": False,
            "confidence": 0.0,
            "scores": {},
            "reason": "",
            "error": None,
        }

        if not self._initialized:
            result["error"] = "Service not initialized"
            return result

        image = self._decode_image(image_data)
        if image is None:
            result["error"] = "Failed to decode image"
            return result

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Run all analyses
            scores = {
                "texture": self._analyze_texture(gray),
                "frequency": self._analyze_frequency(gray),
                "color": self._analyze_color_distribution(image),
                "moire": self._detect_moire(gray),
                "reflection": self._analyze_reflection(image),
            }

            result["scores"] = scores

            # Weighted combination
            weights = {
                "texture": 0.25,
                "frequency": 0.20,
                "color": 0.15,
                "moire": 0.25,
                "reflection": 0.15,
            }

            overall_score = sum(scores[k] * weights[k] for k in scores)
            result["confidence"] = round(overall_score, 3)

            # Determine liveness
            if overall_score >= settings.LIVENESS_THRESHOLD:
                result["is_live"] = True
                result["reason"] = "All liveness checks passed"
            else:
                result["is_live"] = False

                # Identify failing checks
                failing_checks = [k for k, v in scores.items() if v < 0.5]
                if failing_checks:
                    result["reason"] = f"Failed checks: {', '.join(failing_checks)}"
                else:
                    result["reason"] = "Overall confidence too low"

            return result
        except Exception as e:
            logger.error("Anti-spoof analysis failed", error=str(e))
            result["error"] = str(e)
            return result


# Singleton instance
anti_spoof_service = AntiSpoofService()
