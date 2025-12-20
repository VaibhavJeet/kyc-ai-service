"""
Face Recognition Service using InsightFace/ArcFace
Provides 512-dimensional face embeddings for accurate matching
"""

import numpy as np
from typing import Optional, Tuple, List, Dict, Any
import cv2
from PIL import Image
import io
import base64
import structlog
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model

from ..config import settings

logger = structlog.get_logger()


class FaceRecognitionService:
    """
    High-accuracy face recognition using ArcFace model.
    Features:
    - 512-dimensional embeddings (more accurate than MobileFaceNet's 128-dim)
    - RetinaFace detection for robust face finding
    - Face alignment for consistent embeddings
    """

    def __init__(self):
        self._app: Optional[FaceAnalysis] = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize InsightFace models"""
        try:
            logger.info("Initializing InsightFace models...")

            # Use buffalo_l for best accuracy, buffalo_s for speed
            # Models: detection (retinaface), recognition (arcface), age/gender
            self._app = FaceAnalysis(
                name="buffalo_l",  # Large model for production
                root=settings.MODEL_CACHE_DIR,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
                if settings.USE_GPU
                else ["CPUExecutionProvider"],
            )
            self._app.prepare(ctx_id=0 if settings.USE_GPU else -1, det_size=(640, 640))

            self._initialized = True
            logger.info("InsightFace models initialized successfully")
            return True
        except Exception as e:
            logger.error("Failed to initialize InsightFace", error=str(e))
            return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _decode_image(self, image_data: str) -> Optional[np.ndarray]:
        """Decode base64 image to numpy array (BGR format for OpenCV)"""
        try:
            # Remove data URL prefix if present
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)
            pil_image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB then BGR for OpenCV
            rgb_array = np.array(pil_image.convert("RGB"))
            bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

            return bgr_array
        except Exception as e:
            logger.error("Failed to decode image", error=str(e))
            return None

    def detect_faces(self, image_data: str) -> List[Dict[str, Any]]:
        """
        Detect all faces in an image.
        Returns list of detected faces with bounding boxes and landmarks.
        """
        if not self._initialized:
            logger.warning("Service not initialized")
            return []

        image = self._decode_image(image_data)
        if image is None:
            return []

        try:
            faces = self._app.get(image)
            results = []

            for face in faces:
                results.append(
                    {
                        "bbox": face.bbox.tolist(),
                        "det_score": float(face.det_score),
                        "landmarks": face.kps.tolist() if face.kps is not None else None,
                        "age": int(face.age) if hasattr(face, "age") else None,
                        "gender": "M" if face.gender == 1 else "F" if hasattr(face, "gender") else None,
                    }
                )

            return results
        except Exception as e:
            logger.error("Face detection failed", error=str(e))
            return []

    def get_embedding(self, image_data: str) -> Optional[np.ndarray]:
        """
        Extract face embedding from image.
        Returns 512-dimensional normalized embedding vector.
        """
        if not self._initialized:
            logger.warning("Service not initialized")
            return None

        image = self._decode_image(image_data)
        if image is None:
            return None

        try:
            faces = self._app.get(image)
            if not faces:
                logger.warning("No face detected in image")
                return None

            # Use the largest/most prominent face
            if len(faces) > 1:
                faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)

            face = faces[0]
            embedding = face.normed_embedding  # Already L2 normalized

            return embedding
        except Exception as e:
            logger.error("Embedding extraction failed", error=str(e))
            return None

    def get_face_analysis(self, image_data: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive face analysis including embedding, age, gender.
        """
        if not self._initialized:
            return None

        image = self._decode_image(image_data)
        if image is None:
            return None

        try:
            faces = self._app.get(image)
            if not faces:
                return None

            # Use largest face
            if len(faces) > 1:
                faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)

            face = faces[0]

            return {
                "embedding": face.normed_embedding.tolist(),
                "bbox": face.bbox.tolist(),
                "det_score": float(face.det_score),
                "age": int(face.age) if hasattr(face, "age") and face.age is not None else None,
                "gender": "M" if hasattr(face, "gender") and face.gender == 1 else "F" if hasattr(face, "gender") else None,
                "landmarks": face.kps.tolist() if face.kps is not None else None,
            }
        except Exception as e:
            logger.error("Face analysis failed", error=str(e))
            return None

    def compare_faces(
        self,
        image1_data: str,
        image2_data: str,
    ) -> Dict[str, Any]:
        """
        Compare two face images and return similarity score.
        Uses cosine similarity on ArcFace embeddings.
        """
        result = {
            "similarity": 0.0,
            "is_match": False,
            "confidence": "low",
            "face1_detected": False,
            "face2_detected": False,
            "face1_age": None,
            "face2_age": None,
            "error": None,
        }

        if not self._initialized:
            result["error"] = "Service not initialized"
            return result

        # Get analysis for both images
        analysis1 = self.get_face_analysis(image1_data)
        analysis2 = self.get_face_analysis(image2_data)

        if analysis1:
            result["face1_detected"] = True
            result["face1_age"] = analysis1.get("age")
        else:
            result["error"] = "No face detected in first image"
            return result

        if analysis2:
            result["face2_detected"] = True
            result["face2_age"] = analysis2.get("age")
        else:
            result["error"] = "No face detected in second image"
            return result

        # Calculate cosine similarity
        emb1 = np.array(analysis1["embedding"])
        emb2 = np.array(analysis2["embedding"])

        similarity = float(np.dot(emb1, emb2))  # Already normalized, so dot = cosine

        result["similarity"] = similarity

        # Determine match based on thresholds
        if similarity >= settings.FACE_MATCH_HIGH_CONFIDENCE:
            result["is_match"] = True
            result["confidence"] = "high"
        elif similarity >= settings.FACE_MATCH_THRESHOLD:
            result["is_match"] = True
            result["confidence"] = "medium"
        else:
            result["is_match"] = False
            result["confidence"] = "low"

        return result

    def generate_embedding_hash(self, embedding: np.ndarray) -> str:
        """
        Generate privacy-preserving hash from embedding.
        Uses quantization + SHA256 for deduplication without storing biometrics.
        """
        import hashlib

        # Quantize to 8-bit for consistent hashing
        quantized = ((embedding + 1) * 127.5).astype(np.uint8)
        return hashlib.sha256(quantized.tobytes()).hexdigest()

    def generate_fuzzy_hashes(self, embedding: np.ndarray, num_levels: int = 4) -> List[str]:
        """
        Generate fuzzy hashes at different granularities for appearance-tolerant matching.
        L0 = fine-grained, L3 = coarse-grained (most tolerant to aging, beard, glasses)
        """
        import hashlib

        hashes = []
        for i in range(num_levels):
            # Reduce granularity at each level
            levels = 64 >> i  # 64, 32, 16, 8
            quantized = ((embedding + 1) * (levels / 2)).astype(np.uint8)
            hash_val = hashlib.sha256(quantized.tobytes()).hexdigest()[:16]
            hashes.append(f"L{i}_{hash_val}")

        return hashes


# Singleton instance
face_recognition_service = FaceRecognitionService()
