"""
Face Service - Production-Grade Face Detection & Recognition
Uses InsightFace with ArcFace ResNet100:
- buffalo_l model pack (~300MB)
- 512-dimensional embeddings
- 85% similarity threshold for production KYC
- State-of-the-art accuracy for sibling/twin detection
"""

import asyncio
import cv2
import numpy as np
import structlog
import traceback
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import insightface
from insightface.app import FaceAnalysis
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class FaceService:
    """Production-grade face detection and recognition using InsightFace"""

    def __init__(self):
        self.settings = get_settings()
        self.face_app: Optional[FaceAnalysis] = None
        self._initialized = False
        # Thread pool for CPU-bound operations (Issue #8)
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="face_worker")

    async def initialize(self, max_retries: int = 3) -> bool:
        """
        Initialize InsightFace models with retry logic
        Fixes Issue #2: Better error handling and retry logic
        """
        if self._initialized:
            return True

        for attempt in range(max_retries):
            try:
                logger.info(
                    "insightface.initializing",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    model="buffalo_l"
                )

                self.face_app = FaceAnalysis(
                    name='buffalo_l',
                    providers=['CPUExecutionProvider']
                )

                # Prepare models with 640x640 detection size for better accuracy
                self.face_app.prepare(ctx_id=0, det_size=(640, 640))

                self._initialized = True
                logger.info(
                    "insightface.initialized",
                    model="buffalo_l",
                    embedding_dim=512,
                    detection_size="640x640",
                    attempt=attempt + 1
                )
                return True

            except FileNotFoundError as e:
                logger.error(
                    "insightface.model_not_found",
                    error_type="FileNotFoundError",
                    error_message=str(e),
                    advice="Model files missing - cannot recover"
                )
                return False  # Fatal - don't retry

            except (ConnectionError, TimeoutError) as e:
                logger.warning(
                    "insightface.network_error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                if attempt < max_retries - 1:
                    backoff_seconds = 2 ** attempt
                    logger.info("insightface.retry_backoff", seconds=backoff_seconds)
                    await asyncio.sleep(backoff_seconds)
                continue

            except Exception as e:
                logger.error(
                    "insightface.init_failed",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    traceback=traceback.format_exc()
                )
                return False

        logger.error(
            "insightface.init_exhausted",
            max_retries=max_retries,
            status="Failed to initialize after all retries"
        )
        self._initialized = False
        return False

    def is_available(self) -> bool:
        """Check if face service is available"""
        return self._initialized

    async def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces in image using InsightFace
        Fixes Issue #8: Runs in thread pool to avoid blocking event loop
        Fixes Issue #3: Stores face objects for reuse
        """
        if not self.face_app:
            return []

        try:
            # Run CPU-intensive face detection in thread pool (Issue #8)
            loop = asyncio.get_event_loop()
            faces = await loop.run_in_executor(
                self.executor,
                self.face_app.get,
                image
            )

            results = []
            for face in faces:
                # Extract bounding box
                bbox = face.bbox.astype(int).tolist()
                x1, y1, x2, y2 = bbox

                # Extract detection confidence
                det_score = float(face.det_score)

                # Only include faces above threshold
                if det_score >= self.settings.face_detection_threshold:
                    results.append({
                        "box": [x1, y1, x2, y2],
                        "confidence": det_score,
                        "width": x2 - x1,
                        "height": y2 - y1,
                        "landmarks": face.kps.tolist() if hasattr(face, 'kps') else None,
                        "_face_obj": face  # Store for reuse (Issue #3)
                    })

            return results

        except Exception as e:
            logger.error(
                "face.detection_failed",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return []

    async def get_embedding(self, face_obj) -> Optional[np.ndarray]:
        """
        Get 512-dimensional face embedding from face object
        Fixes Issue #3: Reuses detected face instead of re-detecting

        Args:
            face_obj: InsightFace face object from detect_faces

        Returns:
            512-dimensional normalized embedding or None
        """
        if not self.face_app or face_obj is None:
            return None

        try:
            # InsightFace face objects already contain normalized embeddings
            embedding = face_obj.normed_embedding
            return embedding.astype(np.float32)

        except Exception as e:
            logger.error(
                "face.embedding_failed",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return None

    async def compare_faces(
        self,
        image1: np.ndarray,
        image2: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compare two face images using InsightFace 512-dim embeddings
        Fixes Issue #3: Single detection pass, no double detection

        Production threshold: 85% similarity for same person
        """
        # Detect faces in both images (single pass each)
        faces1 = await self.detect_faces(image1)
        faces2 = await self.detect_faces(image2)

        if not faces1:
            return {
                "match": False,
                "error": "No face detected in first image",
                "similarity": 0.0,
                "success": False
            }
        if not faces2:
            return {
                "match": False,
                "error": "No face detected in second image",
                "similarity": 0.0,
                "success": False
            }

        # Get embeddings from detected faces (reuse face objects)
        face1_obj = faces1[0]["_face_obj"]
        face2_obj = faces2[0]["_face_obj"]

        emb1 = await self.get_embedding(face1_obj)
        emb2 = await self.get_embedding(face2_obj)

        if emb1 is None or emb2 is None:
            return {
                "match": False,
                "error": "Failed to generate embeddings",
                "similarity": 0.0,
                "success": False
            }

        # Compute cosine similarity (embeddings are already normalized)
        similarity = float(np.dot(emb1, emb2))

        # Extract age/gender for recommendation logic
        age1 = int(face1_obj.age) if hasattr(face1_obj, 'age') else None
        age2 = int(face2_obj.age) if hasattr(face2_obj, 'age') else None
        gender1 = "male" if (hasattr(face1_obj, 'gender') and face1_obj.gender == 1) else "female" if hasattr(face1_obj, 'gender') else None
        gender2 = "male" if (hasattr(face2_obj, 'gender') and face2_obj.gender == 1) else "female" if hasattr(face2_obj, 'gender') else None

        age_difference = abs(age1 - age2) if (age1 and age2) else None
        gender_match = (gender1 == gender2) if (gender1 and gender2) else None

        # Determine recommendation (no age adjustment - Issue #4 removed)
        threshold = self.settings.face_match_threshold
        is_match = similarity >= threshold

        if similarity >= 0.90:
            recommendation = "AUTO_VERIFY"
            confidence = "high"
        elif similarity >= threshold:
            recommendation = "AUTO_VERIFY"
            confidence = "medium"
        elif similarity >= (threshold - 0.05):
            recommendation = "MANUAL_REVIEW"
            confidence = "medium"
        else:
            recommendation = "REJECT"
            confidence = "low"

        # Clean up internal face objects before returning
        for face in faces1 + faces2:
            if "_face_obj" in face:
                del face["_face_obj"]

        return {
            "match": is_match,
            "similarity": similarity,
            "threshold": threshold,
            "embedding_dim": 512,
            "model": "InsightFace ArcFace ResNet100",
            "success": True,
            # Additional fields for KYC decision making
            "recommendation": recommendation,
            "confidence": confidence,
            "gender_match": gender_match,
            "age_difference": age_difference,
            "age1": age1,
            "age2": age2,
            "gender1": gender1,
            "gender2": gender2,
            "face1": {
                "box": faces1[0]["box"],
                "confidence": faces1[0]["confidence"]
            },
            "face2": {
                "box": faces2[0]["box"],
                "confidence": faces2[0]["confidence"]
            }
        }

    async def estimate_age_gender(self, face_img: np.ndarray) -> Dict[str, Any]:
        """Estimate age and gender using InsightFace"""
        if not self.face_app:
            return {"age": None, "gender": None, "error": "InsightFace not initialized"}

        try:
            # Run in thread pool (Issue #8)
            loop = asyncio.get_event_loop()
            faces = await loop.run_in_executor(
                self.executor,
                self.face_app.get,
                face_img
            )

            if not faces:
                return {"age": None, "gender": None, "error": "No face detected"}

            face = faces[0]

            # Extract age and gender from InsightFace
            age = int(face.age) if hasattr(face, 'age') else None

            if hasattr(face, 'gender'):
                gender = "male" if face.gender == 1 else "female"
                gender_confidence = 0.9
            else:
                gender = None
                gender_confidence = 0.0

            return {
                "age": age,
                "gender": gender,
                "gender_confidence": gender_confidence
            }

        except Exception as e:
            logger.error(
                "face.age_gender_failed",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return {"age": None, "gender": None, "error": str(e)}

    async def check_liveness(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Basic liveness check using image analysis
        Fixes Issue #7: Uses config values instead of magic numbers
        """
        faces = await self.detect_faces(image)

        if not faces:
            return {"is_live": False, "score": 0.0, "reason": "No face detected"}

        face = faces[0]
        box = face["box"]
        face_img = image[box[1]:box[3], box[0]:box[2]]

        # Basic quality checks using config thresholds
        scores = []

        # 1. Blur detection (live faces are sharper)
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(laplacian_var / (self.settings.liveness_min_blur_variance * 10), 1.0)
        scores.append(blur_score)

        # 2. Color saturation (real faces have natural color)
        hsv = cv2.cvtColor(face_img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1].mean() / 255.0
        color_score = min(saturation / self.settings.liveness_min_saturation, 1.0) if self.settings.liveness_min_saturation > 0 else 1.0
        scores.append(color_score)

        # 3. Face size relative to image
        img_h, img_w = image.shape[:2]
        face_area = (box[2] - box[0]) * (box[3] - box[1])
        img_area = img_h * img_w
        size_ratio = face_area / img_area

        # Use config thresholds (Issue #7)
        if self.settings.liveness_min_face_ratio < size_ratio < self.settings.liveness_max_face_ratio:
            size_score = 1.0
        else:
            size_score = 0.5
        scores.append(size_score)

        # 4. Detection confidence from InsightFace
        det_confidence = face["confidence"]
        scores.append(det_confidence)

        # Combined score
        final_score = sum(scores) / len(scores)
        is_live = final_score >= self.settings.liveness_threshold

        # Clean up internal face object
        if "_face_obj" in face:
            del face["_face_obj"]

        return {
            "is_live": is_live,
            "score": float(final_score),
            "details": {
                "blur_score": float(blur_score),
                "color_score": float(color_score),
                "size_score": float(size_score),
                "detection_confidence": float(det_confidence)
            },
            "face_detected": True,
            "face_confidence": face["confidence"]
        }

    def unload(self):
        """Unload models to free memory"""
        self.face_app = None
        self._initialized = False
        self.executor.shutdown(wait=False)
        logger.info("insightface.unloaded", status="Models and thread pool cleaned up")


# Singleton instance
_face_service: Optional[FaceService] = None


def get_face_service() -> FaceService:
    """Get or create face service instance"""
    global _face_service
    if _face_service is None:
        _face_service = FaceService()
    return _face_service
