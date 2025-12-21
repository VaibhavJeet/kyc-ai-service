"""
Anti-Spoof Service - Multi-Layer Liveness Detection
Detects spoofing attempts (photos, screens, printed images)

Detection methods:
1. Texture Analysis - Detects flat/smooth textures typical of screens/prints
2. Reflection Detection - Detects specular highlights in eyes
3. Moiré Pattern Detection - Detects screen capture patterns
4. Color Distribution - Real faces have natural skin color variations
5. Edge Analysis - Printed/screen faces have sharper artificial edges
6. Frequency Analysis - Screens have distinct frequency patterns

NOTE: This is SERVER-SIDE verification, disabled by default.
The Flutter app already does comprehensive on-device liveness detection.
Enable only for borderline cases or when on-device results are suspicious.
"""

import cv2
import numpy as np
import structlog
from typing import Dict, Any, Optional, Tuple
from scipy import ndimage
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class AntiSpoofService:
    """Multi-layer anti-spoofing detection service"""

    def __init__(self):
        self.settings = get_settings()
        # Thresholds (tuned for server-side analysis)
        self.liveness_threshold = 0.65
        self.texture_threshold = 0.4
        self.reflection_threshold = 0.3

    async def analyze(
        self,
        face_image: np.ndarray,
        eye_positions: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive liveness analysis on a face image.

        Args:
            face_image: Cropped face region (BGR)
            eye_positions: Optional (left_eye, right_eye) coordinates

        Returns:
            Dictionary with is_live, confidence, scores, reason
        """
        scores = {}

        try:
            # 1. Texture Analysis (LBP-like)
            scores['texture'] = self._analyze_texture(face_image)

            # 2. Color Distribution Analysis
            scores['color_variance'] = self._analyze_color_variance(face_image)

            # 3. Edge Sharpness Analysis
            scores['edge_sharpness'] = self._analyze_edge_sharpness(face_image)

            # 4. Frequency Analysis
            scores['frequency'] = self._analyze_frequency_pattern(face_image)

            # 5. Moiré Pattern Detection
            scores['moire'] = self._detect_moire_pattern(face_image)

            # 6. Eye Reflection Analysis
            if eye_positions:
                scores['eye_reflection'] = self._analyze_eye_reflection(
                    face_image, eye_positions
                )
            else:
                scores['eye_reflection'] = 0.5  # Neutral if no landmarks

            # Calculate weighted overall score
            overall_score = self._calculate_overall_score(scores)
            is_live = overall_score >= self.liveness_threshold
            reason = self._generate_reason(scores, is_live)

            logger.debug(
                "Anti-spoof analysis complete",
                scores=scores,
                overall=overall_score,
                is_live=is_live
            )

            return {
                "is_live": is_live,
                "confidence": float(overall_score),
                "reason": reason,
                "scores": {k: float(v) for k, v in scores.items()}
            }

        except Exception as e:
            logger.error("Anti-spoof analysis failed", error=str(e))
            # On error, return moderate confidence to allow manual review
            return {
                "is_live": True,  # Don't block on error
                "confidence": 0.5,
                "reason": "Analysis incomplete",
                "scores": {"error": 1.0}
            }

    def _analyze_texture(self, image: np.ndarray) -> float:
        """
        Analyze skin texture using simplified LBP-like approach.
        Real faces have natural texture variations; prints/screens are smoother.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        texture_count = 0
        total_pixels = 0

        # Sample every other pixel for performance
        for y in range(1, h - 1, 2):
            for x in range(1, w - 1, 2):
                center = int(gray[y, x])

                # Count neighbors with different luminance
                differences = 0
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dx == 0 and dy == 0:
                            continue
                        neighbor = int(gray[y + dy, x + dx])
                        if abs(center - neighbor) > 10:
                            differences += 1

                # High variation = natural texture
                if differences >= 3:
                    texture_count += 1
                total_pixels += 1

        return texture_count / total_pixels if total_pixels > 0 else 0.5

    def _analyze_color_variance(self, image: np.ndarray) -> float:
        """
        Analyze skin color variance.
        Real faces have natural color gradients; prints may have uniform colors.
        """
        h, w = image.shape[:2]
        center_x, center_y = w // 2, h // 2
        sample_radius = w // 4

        samples = []
        for y in range(center_y - sample_radius, center_y + sample_radius, 4):
            for x in range(center_x - sample_radius, center_x + sample_radius, 4):
                if 0 <= x < w and 0 <= y < h:
                    b, g, r = image[y, x]
                    # Basic skin color filter
                    if r > 60 and g > 40 and b > 20 and r > b and abs(r - g) < 100:
                        samples.append([int(r), int(g), int(b)])

        if len(samples) < 10:
            return 0.5

        samples = np.array(samples)
        mean = np.mean(samples, axis=0)
        variance = np.mean((samples - mean) ** 2)

        # Normalize to 0-1 range
        return min(1.0, variance / 500)

    def _analyze_edge_sharpness(self, image: np.ndarray) -> float:
        """
        Analyze edge sharpness.
        Printed photos often have artificially sharp edges.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate gradient using Sobel
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient = np.sqrt(gx**2 + gy**2)
        avg_gradient = np.mean(gradient)

        # Very high gradient = likely artificial
        if avg_gradient > 50:
            return 1.0 - min(1.0, (avg_gradient - 50) / 50)
        elif avg_gradient < 10:
            return 0.3  # Too blurry
        else:
            return 0.8  # Natural range

    def _analyze_frequency_pattern(self, image: np.ndarray) -> float:
        """
        Frequency analysis for screen detection.
        Screens have distinct high-frequency patterns from pixel grids.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        pattern_count = 0
        total_checks = 0

        for y in range(2, h - 2, 4):
            for x in range(2, w - 2, 4):
                current = int(gray[y, x])
                two_away = int(gray[y, min(x + 2, w - 1)])
                one_away = int(gray[y, min(x + 1, w - 1)])

                # Check for alternating pattern (typical of screens)
                if abs(current - one_away) > 10 and abs(current - two_away) < 5:
                    pattern_count += 1
                total_checks += 1

        pattern_ratio = pattern_count / total_checks if total_checks > 0 else 0

        # High pattern ratio = likely screen
        return 1.0 - min(1.0, pattern_ratio * 5)

    def _detect_moire_pattern(self, image: np.ndarray) -> float:
        """
        Detect moiré patterns (interference from screen capture).
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        moire_indicators = 0
        checks = 0

        for y in range(5, h - 5, 10):
            row_values = gray[y, ::2].astype(int)

            if len(row_values) < 10:
                continue

            # Count oscillations
            oscillations = 0
            for i in range(1, len(row_values) - 1):
                if ((row_values[i] > row_values[i-1] and row_values[i] > row_values[i+1]) or
                    (row_values[i] < row_values[i-1] and row_values[i] < row_values[i+1])):
                    oscillations += 1

            # High oscillation = moiré pattern
            if oscillations > len(row_values) * 0.4:
                moire_indicators += 1
            checks += 1

        moire_ratio = moire_indicators / checks if checks > 0 else 0
        return 1.0 - min(1.0, moire_ratio * 2)

    def _analyze_eye_reflection(
        self,
        image: np.ndarray,
        eye_positions: Tuple[Tuple[int, int], Tuple[int, int]]
    ) -> float:
        """
        Analyze eye reflections (catchlights).
        Real eyes have natural specular highlights.
        """
        h, w = image.shape[:2]
        reflection_score = 0
        eye_count = 0

        for eye_pos in eye_positions:
            if eye_pos is None:
                continue

            eye_x, eye_y = eye_pos
            if not (0 <= eye_x < w and 0 <= eye_y < h):
                continue

            # Sample area around eye
            sample_size = 10
            bright_pixels = 0
            total_pixels = 0

            for dy in range(-sample_size, sample_size + 1):
                for dx in range(-sample_size, sample_size + 1):
                    x, y = eye_x + dx, eye_y + dy
                    if not (0 <= x < w and 0 <= y < h):
                        continue

                    pixel = image[y, x]
                    brightness = np.mean(pixel)

                    if brightness > 200:
                        bright_pixels += 1
                    total_pixels += 1

            if total_pixels > 0:
                bright_ratio = bright_pixels / total_pixels
                if 0.01 < bright_ratio < 0.15:
                    reflection_score += 0.8  # Natural catchlight
                elif bright_ratio >= 0.15:
                    reflection_score += 0.4  # Too much reflection
                else:
                    reflection_score += 0.3  # No reflection (could be print)
                eye_count += 1

        return reflection_score / eye_count if eye_count > 0 else 0.5

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall liveness score"""
        weights = {
            'texture': 0.25,
            'color_variance': 0.20,
            'edge_sharpness': 0.15,
            'frequency': 0.15,
            'moire': 0.10,
            'eye_reflection': 0.15,
        }

        weighted_sum = 0
        total_weight = 0

        for key, value in scores.items():
            weight = weights.get(key, 0.1)
            weighted_sum += value * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def _generate_reason(self, scores: Dict[str, float], is_live: bool) -> str:
        """Generate human-readable reason for the result"""
        if is_live:
            return "Liveness verified"

        issues = []
        if scores.get('texture', 1.0) < self.texture_threshold:
            issues.append("Image appears flat (possible print/screen)")
        if scores.get('moire', 1.0) < 0.5:
            issues.append("Screen patterns detected")
        if scores.get('frequency', 1.0) < 0.5:
            issues.append("Unusual frequency patterns")
        if scores.get('eye_reflection', 1.0) < self.reflection_threshold:
            issues.append("No natural eye reflections")

        return "; ".join(issues) if issues else "Liveness check failed"


# Singleton
_anti_spoof_service: Optional[AntiSpoofService] = None


def get_anti_spoof_service() -> AntiSpoofService:
    """Get or create anti-spoof service instance"""
    global _anti_spoof_service
    if _anti_spoof_service is None:
        _anti_spoof_service = AntiSpoofService()
    return _anti_spoof_service
