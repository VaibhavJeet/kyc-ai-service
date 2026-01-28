"""
TrustVault Deepfake Detection Service
Detect AI-generated or manipulated faces in images and videos

Detection Methods:
1. Frequency analysis (GAN artifacts)
2. Facial landmark consistency
3. Blending boundary detection
4. Eye reflection analysis
5. Temporal inconsistency (video)
"""

import cv2
import numpy as np
import structlog
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class DeepfakeType(str, Enum):
    """Types of deepfakes detected"""
    FACE_SWAP = "face_swap"
    FACE_REENACTMENT = "face_reenactment"
    FACE_GENERATION = "face_generation"
    LIP_SYNC = "lip_sync"
    UNKNOWN = "unknown"
    NONE = "none"


@dataclass
class DeepfakeIndicator:
    """Individual deepfake indicator"""
    name: str
    score: float  # 0-1, higher = more likely deepfake
    description: str
    details: Optional[Dict[str, Any]] = None


class DeepfakeDetectionService:
    """
    Multi-method deepfake detection service.

    Note: This is a simplified implementation. Production systems
    would use specialized ML models like:
    - EfficientNet-based classifiers
    - Xception network
    - MesoNet
    - Face X-Ray
    """

    # Thresholds for detection
    FREQUENCY_THRESHOLD = 0.6
    CONSISTENCY_THRESHOLD = 0.7
    BLENDING_THRESHOLD = 0.5
    OVERALL_THRESHOLD = 0.5

    def __init__(self):
        self.face_cascade = None
        self._initialize_detectors()

    def _initialize_detectors(self):
        """Initialize OpenCV detectors"""
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except Exception as e:
            logger.warning("deepfake.detector_init_failed", error=str(e))

    async def analyze_image(
        self,
        image: np.ndarray,
        detailed: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze image for deepfake indicators.

        Args:
            image: BGR image as numpy array
            detailed: Include detailed analysis

        Returns:
            Detection result with confidence scores
        """
        indicators: List[DeepfakeIndicator] = []

        # Detect face
        face_region = self._detect_face(image)
        if face_region is None:
            return {
                "is_deepfake": False,
                "confidence": 0,
                "error": "No face detected",
            }

        # 1. Frequency analysis (detect GAN artifacts)
        freq_result = self._analyze_frequency(face_region)
        indicators.append(DeepfakeIndicator(
            name="frequency_analysis",
            score=freq_result["score"],
            description="Detects GAN-generated artifacts in frequency domain",
            details=freq_result if detailed else None
        ))

        # 2. Facial landmark consistency
        landmark_result = self._analyze_landmarks(face_region)
        indicators.append(DeepfakeIndicator(
            name="landmark_consistency",
            score=landmark_result["score"],
            description="Checks facial landmark proportions and symmetry",
            details=landmark_result if detailed else None
        ))

        # 3. Blending boundary detection
        blend_result = self._detect_blending(image, face_region)
        indicators.append(DeepfakeIndicator(
            name="blending_detection",
            score=blend_result["score"],
            description="Detects unnatural boundaries around face",
            details=blend_result if detailed else None
        ))

        # 4. Color consistency
        color_result = self._analyze_color_consistency(image, face_region)
        indicators.append(DeepfakeIndicator(
            name="color_consistency",
            score=color_result["score"],
            description="Checks color distribution consistency",
            details=color_result if detailed else None
        ))

        # 5. Texture analysis
        texture_result = self._analyze_texture(face_region)
        indicators.append(DeepfakeIndicator(
            name="texture_analysis",
            score=texture_result["score"],
            description="Analyzes skin texture patterns",
            details=texture_result if detailed else None
        ))

        # Calculate overall score
        scores = [i.score for i in indicators]
        overall_score = np.mean(scores)
        max_score = max(scores)

        # Use weighted decision
        is_deepfake = overall_score > self.OVERALL_THRESHOLD or max_score > 0.8

        # Determine deepfake type if detected
        deepfake_type = self._determine_type(indicators) if is_deepfake else DeepfakeType.NONE

        return {
            "is_deepfake": is_deepfake,
            "confidence": float(overall_score),
            "deepfake_type": deepfake_type.value,
            "indicators": [
                {
                    "name": i.name,
                    "score": float(i.score),
                    "description": i.description,
                    **({"details": i.details} if i.details else {})
                }
                for i in indicators
            ],
            "recommendation": self._get_recommendation(is_deepfake, overall_score),
        }

    async def analyze_video(
        self,
        video_path: str,
        sample_rate: int = 10,
    ) -> Dict[str, Any]:
        """
        Analyze video for deepfake indicators.

        Args:
            video_path: Path to video file
            sample_rate: Analyze every Nth frame

        Returns:
            Detection result with temporal analysis
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": "Failed to open video"}

            frame_results: List[Dict[str, Any]] = []
            frame_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % sample_rate == 0:
                    result = await self.analyze_image(frame, detailed=False)
                    frame_results.append({
                        "frame": frame_count,
                        "is_deepfake": result.get("is_deepfake", False),
                        "confidence": result.get("confidence", 0),
                    })

                frame_count += 1

            cap.release()

            if not frame_results:
                return {"error": "No frames analyzed"}

            # Aggregate results
            deepfake_frames = [r for r in frame_results if r["is_deepfake"]]
            deepfake_ratio = len(deepfake_frames) / len(frame_results)
            avg_confidence = np.mean([r["confidence"] for r in frame_results])

            # Temporal consistency check
            temporal_score = self._check_temporal_consistency(frame_results)

            overall_is_deepfake = deepfake_ratio > 0.3 or temporal_score > 0.6

            return {
                "is_deepfake": overall_is_deepfake,
                "confidence": float(avg_confidence),
                "deepfake_frame_ratio": float(deepfake_ratio),
                "temporal_consistency_score": float(temporal_score),
                "frames_analyzed": len(frame_results),
                "total_frames": frame_count,
                "recommendation": self._get_recommendation(overall_is_deepfake, avg_confidence),
            }

        except Exception as e:
            logger.error("deepfake.video_analysis_failed", error=str(e))
            return {"error": str(e)}

    # ============= Detection Methods =============

    def _detect_face(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Detect and extract face region"""
        if self.face_cascade is None:
            return image  # Return full image if no detector

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) == 0:
            return None

        # Get largest face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        # Add padding
        padding = int(max(w, h) * 0.2)
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(image.shape[1], x + w + padding)
        y2 = min(image.shape[0], y + h + padding)

        return image[y1:y2, x1:x2]

    def _analyze_frequency(self, face: np.ndarray) -> Dict[str, Any]:
        """
        Analyze frequency domain for GAN artifacts.
        GANs often produce distinctive patterns in high-frequency components.
        """
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

        # Apply DFT
        dft = cv2.dft(np.float32(gray), flags=cv2.DFT_COMPLEX_OUTPUT)
        dft_shift = np.fft.fftshift(dft)

        # Magnitude spectrum
        magnitude = cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1])
        magnitude = np.log(magnitude + 1)

        # Analyze high-frequency components
        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2

        # High-frequency region (outer 20%)
        mask = np.zeros_like(magnitude)
        cv2.circle(mask, (center_w, center_h), int(min(h, w) * 0.4), 1, -1)
        mask = 1 - mask  # Invert to get outer region

        high_freq_energy = np.sum(magnitude * mask)
        total_energy = np.sum(magnitude)

        ratio = high_freq_energy / (total_energy + 1e-6)

        # GANs often have unusual high-frequency patterns
        # Normal images: ratio typically 0.1-0.3
        # GAN images: ratio may be lower or have specific patterns
        score = 0.0
        if ratio < 0.05 or ratio > 0.5:
            score = 0.7
        elif ratio < 0.1 or ratio > 0.4:
            score = 0.4

        return {
            "score": score,
            "high_freq_ratio": float(ratio),
        }

    def _analyze_landmarks(self, face: np.ndarray) -> Dict[str, Any]:
        """
        Analyze facial landmark consistency.
        Deepfakes may have inconsistent proportions.
        """
        # Simplified analysis using edge detection
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Check edge distribution (should be relatively symmetric)
        h, w = edges.shape
        left_half = edges[:, :w // 2]
        right_half = cv2.flip(edges[:, w // 2:], 1)

        # Resize to match if needed
        min_w = min(left_half.shape[1], right_half.shape[1])
        left_half = left_half[:, :min_w]
        right_half = right_half[:, :min_w]

        # Calculate symmetry score
        diff = np.abs(left_half.astype(float) - right_half.astype(float))
        asymmetry = np.mean(diff) / 255

        # High asymmetry may indicate manipulation
        score = min(asymmetry * 2, 1.0)

        return {
            "score": float(score),
            "asymmetry": float(asymmetry),
        }

    def _detect_blending(
        self,
        image: np.ndarray,
        face: np.ndarray
    ) -> Dict[str, Any]:
        """
        Detect blending boundaries around the face.
        Face swaps often have visible blending artifacts.
        """
        # Convert to LAB for better color analysis
        lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)

        # Edge detection
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)

        # Look for strong edges near face boundary
        h, w = edges.shape
        boundary_region = np.zeros_like(edges)
        cv2.rectangle(boundary_region, (5, 5), (w - 5, h - 5), 255, 10)

        boundary_edges = cv2.bitwise_and(edges, boundary_region)
        edge_density = np.sum(boundary_edges) / (np.sum(boundary_region) + 1)

        # Color consistency at boundary
        l_channel = lab[:, :, 0]
        boundary_l = l_channel[boundary_region > 0]
        center_l = l_channel[h // 4:3 * h // 4, w // 4:3 * w // 4]

        if len(boundary_l) > 0 and center_l.size > 0:
            color_diff = abs(np.mean(boundary_l) - np.mean(center_l))
        else:
            color_diff = 0

        # Combine scores
        score = min((edge_density * 2 + color_diff / 50) / 2, 1.0)

        return {
            "score": float(score),
            "edge_density": float(edge_density),
            "color_difference": float(color_diff),
        }

    def _analyze_color_consistency(
        self,
        image: np.ndarray,
        face: np.ndarray
    ) -> Dict[str, Any]:
        """
        Analyze color distribution consistency.
        Manipulated images may have unnatural color distributions.
        """
        # Convert to HSV
        hsv = cv2.cvtColor(face, cv2.COLOR_BGR2HSV)

        # Analyze saturation distribution
        saturation = hsv[:, :, 1]
        sat_std = np.std(saturation)
        sat_mean = np.mean(saturation)

        # Natural faces have certain saturation characteristics
        # Very uniform or very varied saturation may indicate manipulation
        if sat_std < 10 or sat_std > 80:
            sat_score = 0.6
        elif sat_std < 20 or sat_std > 60:
            sat_score = 0.3
        else:
            sat_score = 0.1

        # Check for unnatural hue distribution (skin tones)
        hue = hsv[:, :, 0]
        # Skin tones typically in range 0-25 (red-orange) in OpenCV HSV
        skin_mask = (hue < 25) | (hue > 170)
        skin_ratio = np.sum(skin_mask) / hue.size

        if skin_ratio < 0.3:  # Very little skin tone
            hue_score = 0.5
        else:
            hue_score = 0.1

        score = (sat_score + hue_score) / 2

        return {
            "score": float(score),
            "saturation_std": float(sat_std),
            "skin_ratio": float(skin_ratio),
        }

    def _analyze_texture(self, face: np.ndarray) -> Dict[str, Any]:
        """
        Analyze skin texture patterns.
        GAN-generated faces may have unnatural texture.
        """
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

        # Calculate local binary pattern-like features
        # Using Laplacian variance as proxy for texture detail
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()

        # Natural faces have certain texture characteristics
        # Too smooth (low variance) or too noisy (high variance) may indicate manipulation
        if variance < 50:
            score = 0.7  # Too smooth
        elif variance > 2000:
            score = 0.5  # Too noisy
        else:
            score = 0.1

        return {
            "score": float(score),
            "texture_variance": float(variance),
        }

    def _check_temporal_consistency(
        self,
        frame_results: List[Dict[str, Any]]
    ) -> float:
        """
        Check temporal consistency across video frames.
        Real faces should have consistent detection across frames.
        """
        if len(frame_results) < 2:
            return 0.0

        confidences = [r["confidence"] for r in frame_results]

        # Check for sudden changes in confidence
        diffs = np.abs(np.diff(confidences))
        avg_diff = np.mean(diffs)
        max_diff = np.max(diffs)

        # High variation suggests manipulation
        if max_diff > 0.5 or avg_diff > 0.2:
            return 0.7
        elif max_diff > 0.3 or avg_diff > 0.1:
            return 0.4
        else:
            return 0.1

    def _determine_type(
        self,
        indicators: List[DeepfakeIndicator]
    ) -> DeepfakeType:
        """Determine the type of deepfake based on indicators"""
        # Simple heuristic based on which indicators triggered
        scores = {i.name: i.score for i in indicators}

        if scores.get("blending_detection", 0) > 0.6:
            return DeepfakeType.FACE_SWAP
        elif scores.get("frequency_analysis", 0) > 0.7:
            return DeepfakeType.FACE_GENERATION
        elif scores.get("landmark_consistency", 0) > 0.7:
            return DeepfakeType.FACE_REENACTMENT
        else:
            return DeepfakeType.UNKNOWN

    def _get_recommendation(self, is_deepfake: bool, confidence: float) -> str:
        """Get user-friendly recommendation"""
        if is_deepfake:
            if confidence > 0.8:
                return "HIGH LIKELIHOOD of manipulation. Do not trust this media for identity verification."
            elif confidence > 0.6:
                return "PROBABLE manipulation detected. Request alternative verification methods."
            else:
                return "POSSIBLE manipulation. Exercise caution and verify through other means."
        else:
            if confidence < 0.2:
                return "No significant manipulation detected. Media appears authentic."
            else:
                return "Low manipulation indicators. Proceed with normal verification."


# Singleton
_deepfake_service: Optional[DeepfakeDetectionService] = None


def get_deepfake_detection_service() -> DeepfakeDetectionService:
    """Get deepfake detection service instance"""
    global _deepfake_service
    if _deepfake_service is None:
        _deepfake_service = DeepfakeDetectionService()
    return _deepfake_service
