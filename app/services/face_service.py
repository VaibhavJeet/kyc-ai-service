"""
Face Service - Ultra-Lightweight Face Detection & Recognition
Uses:
- Ultra-Light Face Detector (~1-2MB, ~30-50MB RAM)
- MobileFaceNet INT8 (~3-5MB, ~40-60MB RAM)
- MobileNetV2 Age/Gender INT8 (~1.5MB, ~20-30MB RAM)
Total: ~15MB models, ~120MB RAM peak
"""

import cv2
import numpy as np
import structlog
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import onnxruntime as ort
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class FaceService:
    """Ultra-lightweight face detection and recognition service"""

    def __init__(self):
        self.settings = get_settings()
        self.detector: Optional[ort.InferenceSession] = None
        self.recognizer: Optional[ort.InferenceSession] = None
        self.age_gender: Optional[ort.InferenceSession] = None
        self._initialized = False

        # ONNX Runtime session options for minimal memory
        self.session_options = ort.SessionOptions()
        self.session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session_options.intra_op_num_threads = 2
        self.session_options.inter_op_num_threads = 1

    async def initialize(self) -> bool:
        """Initialize face models"""
        if self._initialized:
            return True

        models_loaded = 0

        # Load Ultra-Light Face Detector
        try:
            detector_path = Path(self.settings.face_detector_model)
            if detector_path.exists():
                self.detector = ort.InferenceSession(
                    str(detector_path),
                    self.session_options,
                    providers=["CPUExecutionProvider"]
                )
                logger.info("Face detector loaded", model=str(detector_path))
                models_loaded += 1
            else:
                logger.warning("Face detector model not found", path=str(detector_path))
        except Exception as e:
            logger.error("Failed to load face detector", error=str(e))

        # Load MobileFaceNet for recognition
        try:
            recognizer_path = Path(self.settings.face_recognition_model)
            if recognizer_path.exists():
                self.recognizer = ort.InferenceSession(
                    str(recognizer_path),
                    self.session_options,
                    providers=["CPUExecutionProvider"]
                )
                logger.info("Face recognizer loaded", model=str(recognizer_path))
                models_loaded += 1
            else:
                logger.warning("Face recognizer model not found", path=str(recognizer_path))
        except Exception as e:
            logger.error("Failed to load face recognizer", error=str(e))

        # Load Age/Gender model
        try:
            age_gender_path = Path(self.settings.age_gender_model)
            if age_gender_path.exists():
                self.age_gender = ort.InferenceSession(
                    str(age_gender_path),
                    self.session_options,
                    providers=["CPUExecutionProvider"]
                )
                logger.info("Age/Gender model loaded", model=str(age_gender_path))
                models_loaded += 1
            else:
                logger.warning("Age/Gender model not found", path=str(age_gender_path))
        except Exception as e:
            logger.error("Failed to load age/gender model", error=str(e))

        self._initialized = models_loaded > 0
        return self._initialized

    def is_available(self) -> bool:
        """Check if face service is available"""
        return self._initialized

    def _preprocess_for_detection(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for Ultra-Light Face Detector (320x240 input)"""
        img = cv2.resize(image, (320, 240))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = (img - 127.0) / 128.0
        img = img.transpose(2, 0, 1)
        img = np.expand_dims(img, axis=0).astype(np.float32)
        return img

    def _preprocess_for_recognition(self, face_img: np.ndarray) -> np.ndarray:
        """Preprocess face for MobileFaceNet (112x112 input)"""
        face = cv2.resize(face_img, (112, 112))
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        face = (face - 127.5) / 127.5
        face = face.transpose(2, 0, 1)
        face = np.expand_dims(face, axis=0).astype(np.float32)
        return face

    def _preprocess_for_age_gender(self, face_img: np.ndarray) -> np.ndarray:
        """Preprocess face for age/gender model (96x96 or 224x224 input)"""
        face = cv2.resize(face_img, (96, 96))
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        face = face / 255.0
        face = face.transpose(2, 0, 1)
        face = np.expand_dims(face, axis=0).astype(np.float32)
        return face

    async def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces in image using Ultra-Light Face Detector"""
        if not self.detector:
            return []

        h, w = image.shape[:2]
        input_tensor = self._preprocess_for_detection(image)

        # Run inference
        input_name = self.detector.get_inputs()[0].name
        outputs = self.detector.run(None, {input_name: input_tensor})

        # Parse detections (format depends on specific model)
        # Ultra-Light outputs: [confidences, boxes]
        confidences = outputs[0]
        boxes = outputs[1]

        faces = []
        for i in range(confidences.shape[1]):
            conf = confidences[0, i, 1]  # Face confidence
            if conf > self.settings.face_detection_threshold:
                # Scale box to original image size
                x1 = int(boxes[0, i, 0] * w)
                y1 = int(boxes[0, i, 1] * h)
                x2 = int(boxes[0, i, 2] * w)
                y2 = int(boxes[0, i, 3] * h)

                # Ensure valid box
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                if x2 - x1 >= self.settings.min_face_size and y2 - y1 >= self.settings.min_face_size:
                    faces.append({
                        "box": [x1, y1, x2, y2],
                        "confidence": float(conf),
                        "width": x2 - x1,
                        "height": y2 - y1
                    })

        return faces

    async def get_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """Get face embedding using MobileFaceNet (128-dim)"""
        if not self.recognizer:
            return None

        input_tensor = self._preprocess_for_recognition(face_img)
        input_name = self.recognizer.get_inputs()[0].name
        outputs = self.recognizer.run(None, {input_name: input_tensor})

        embedding = outputs[0][0]
        # Normalize embedding
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    async def compare_faces(
        self,
        image1: np.ndarray,
        image2: np.ndarray
    ) -> Dict[str, Any]:
        """Compare two face images and return similarity"""
        # Detect faces in both images
        faces1 = await self.detect_faces(image1)
        faces2 = await self.detect_faces(image2)

        if not faces1:
            return {"match": False, "error": "No face detected in first image", "similarity": 0.0}
        if not faces2:
            return {"match": False, "error": "No face detected in second image", "similarity": 0.0}

        # Get face crops
        box1 = faces1[0]["box"]
        face1 = image1[box1[1]:box1[3], box1[0]:box1[2]]

        box2 = faces2[0]["box"]
        face2 = image2[box2[1]:box2[3], box2[0]:box2[2]]

        # Get embeddings
        emb1 = await self.get_embedding(face1)
        emb2 = await self.get_embedding(face2)

        if emb1 is None or emb2 is None:
            return {"match": False, "error": "Failed to generate embeddings", "similarity": 0.0}

        # Cosine similarity
        similarity = float(np.dot(emb1, emb2))
        
        return {
            "match": similarity >= self.settings.face_match_threshold,
            "similarity": similarity,
            "threshold": self.settings.face_match_threshold,
            "face1": {"box": box1, "confidence": faces1[0]["confidence"]},
            "face2": {"box": box2, "confidence": faces2[0]["confidence"]}
        }

    async def compare_faces_with_age(
        self,
        image1: np.ndarray,
        image2: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compare faces with age adjustment.
        If age gap > 10 years, applies a bonus to the similarity score.
        """
        # Base comparison to get faces and embeddings
        base_result = await self.compare_faces(image1, image2)
        
        if "error" in base_result:
            return base_result

        # Extract faces again (inefficient, but reuses existing flow safely)
        # In a real optimization, we'd refactor to return crops
        faces1 = await self.detect_faces(image1)
        faces2 = await self.detect_faces(image2)
        
        box1 = faces1[0]["box"]
        face1 = image1[box1[1]:box1[3], box1[0]:box1[2]]

        box2 = faces2[0]["box"]
        face2 = image2[box2[1]:box2[3], box2[0]:box2[2]]

        # Estimate ages
        age_gender1 = await self.estimate_age_gender(face1)
        age_gender2 = await self.estimate_age_gender(face2)
        
        age1 = age_gender1.get("age")
        age2 = age_gender2.get("age")
        
        adjusted_similarity = base_result["similarity"]
        age_gap = 0
        bonus = 0.0

        if age1 is not None and age2 is not None:
            age_gap = abs(age1 - age2)
            
            # Logic: If age gap > 10 years, apply relaxed threshold (bonus)
            if age_gap > 10:
                # 10-20 years: small bonus, 20+ years: larger bonus
                # Cap bonus to avoid false positives
                if age_gap <= 20:
                    bonus = 0.05
                else:
                    bonus = 0.10
                
                adjusted_similarity = min(1.0, adjusted_similarity + bonus)

        # Recalculate match with adjusted similarity
        is_match = adjusted_similarity >= self.settings.face_match_threshold

        return {
            "match": is_match,
            "similarity": adjusted_similarity,
            "original_similarity": base_result["similarity"],
            "age_gap": age_gap,
            "age1": age1,
            "age2": age2,
            "bonus_applied": bonus,
            "threshold": self.settings.face_match_threshold,
            "details": "Age-adjusted matching applied" if bonus > 0 else "Standard matching"
        }

    async def estimate_age_gender(self, face_img: np.ndarray) -> Dict[str, Any]:
        """Estimate age and gender from face image"""
        if not self.age_gender:
            return {"age": None, "gender": None, "error": "Age/gender model not loaded"}

        input_tensor = self._preprocess_for_age_gender(face_img)
        input_name = self.age_gender.get_inputs()[0].name
        outputs = self.age_gender.run(None, {input_name: input_tensor})

        # Output format depends on model
        # Typically: [age_output, gender_output] or combined
        if len(outputs) >= 2:
            age = float(outputs[0][0])
            gender_prob = outputs[1][0]
            gender = "male" if gender_prob[0] > gender_prob[1] else "female"
            gender_confidence = float(max(gender_prob))
        else:
            # Combined output
            output = outputs[0][0]
            age = float(output[0])
            gender = "male" if output[1] > 0.5 else "female"
            gender_confidence = float(abs(output[1] - 0.5) * 2)

        return {
            "age": int(age),
            "gender": gender,
            "gender_confidence": gender_confidence
        }

    async def check_liveness(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Basic liveness check using image analysis
        No ML model - uses texture and quality analysis
        """
        faces = await self.detect_faces(image)

        if not faces:
            return {"is_live": False, "score": 0.0, "reason": "No face detected"}

        face = faces[0]
        box = face["box"]
        face_img = image[box[1]:box[3], box[0]:box[2]]

        # Basic quality checks
        scores = []

        # 1. Blur detection (live faces are sharper)
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(laplacian_var / 500.0, 1.0)
        scores.append(blur_score)

        # 2. Color variance (real faces have natural color distribution)
        hsv = cv2.cvtColor(face_img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1].mean() / 255.0
        color_score = min(saturation * 2, 1.0)
        scores.append(color_score)

        # 3. Face size relative to image
        img_h, img_w = image.shape[:2]
        face_area = (box[2] - box[0]) * (box[3] - box[1])
        img_area = img_h * img_w
        size_ratio = face_area / img_area
        size_score = 1.0 if 0.1 < size_ratio < 0.8 else 0.5
        scores.append(size_score)

        # 4. Aspect ratio check
        aspect = (box[2] - box[0]) / max(box[3] - box[1], 1)
        aspect_score = 1.0 if 0.6 < aspect < 1.5 else 0.5
        scores.append(aspect_score)

        # Combined score
        final_score = sum(scores) / len(scores)
        is_live = final_score >= self.settings.liveness_threshold

        return {
            "is_live": is_live,
            "score": float(final_score),
            "details": {
                "blur_score": float(blur_score),
                "color_score": float(color_score),
                "size_score": float(size_score),
                "aspect_score": float(aspect_score)
            },
            "face_detected": True,
            "face_confidence": face["confidence"]
        }

    def unload(self):
        """Unload models to free memory"""
        self.detector = None
        self.recognizer = None
        self.age_gender = None
        self._initialized = False
        logger.info("Face models unloaded")


# Singleton instance
_face_service: Optional[FaceService] = None


def get_face_service() -> FaceService:
    """Get or create face service instance"""
    global _face_service
    if _face_service is None:
        _face_service = FaceService()
    return _face_service
