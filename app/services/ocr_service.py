"""
OCR Service - Ultra-Lightweight Document OCR
Uses Tesseract OCR with OpenCV preprocessing
~30MB disk, ~80MB RAM, no ML inference spikes
"""

import cv2
import numpy as np
import structlog
import pytesseract
import re
from typing import Optional, Dict, Any, List
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class OCRService:
    """Ultra-lightweight OCR using Tesseract with preprocessing"""

    def __init__(self):
        self.settings = get_settings()
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize OCR service"""
        if self._initialized:
            return True

        try:
            # Test Tesseract availability
            pytesseract.get_tesseract_version()
            self._initialized = True
            logger.info("Tesseract OCR initialized")
            return True
        except Exception as e:
            logger.error(
                "Tesseract not available",
                error=str(e),
                hint="Install Tesseract: apt-get install tesseract-ocr (Linux) or download from GitHub (Windows)"
            )
            return False

    def is_available(self) -> bool:
        """Check if OCR is available"""
        return self._initialized

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy:
        - Grayscale conversion
        - Adaptive thresholding
        - Noise removal
        - Deskew
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Resize if too small
        h, w = gray.shape
        if h < 300 or w < 300:
            scale = max(300 / h, 300 / w)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )

        # Morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        return thresh

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Deskew image using Hough transform"""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) < 10:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90

        if abs(angle) > 0.5:
            h, w = image.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            image = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )

        return image

    async def extract_text(
        self,
        image: np.ndarray,
        lang: Optional[str] = None,
        preprocess: bool = True
    ) -> Dict[str, Any]:
        """Extract text from image"""
        if not self._initialized:
            return {"text": "", "error": "OCR not initialized"}

        try:
            if preprocess:
                processed = self._preprocess_image(image)
                processed = self._deskew(processed)
            else:
                processed = image

            # Run Tesseract
            config = self.settings.tesseract_config
            text = pytesseract.image_to_string(
                processed,
                lang=lang or self.settings.tesseract_lang,
                config=config
            )

            # Get detailed data
            data = pytesseract.image_to_data(
                processed,
                lang=lang or self.settings.tesseract_lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )

            # Calculate average confidence
            confidences = [int(c) for c in data["conf"] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "text": text.strip(),
                "confidence": avg_confidence,
                "words": len([w for w in data["text"] if w.strip()]),
                "lines": text.count("\n") + 1
            }

        except Exception as e:
            logger.error("OCR extraction failed", error=str(e))
            return {"text": "", "error": str(e), "confidence": 0}

    async def extract_document_info(
        self,
        image: np.ndarray,
        document_type: str = "id_card"
    ) -> Dict[str, Any]:
        """
        Extract structured information from ID documents
        Supports: Aadhaar, PAN, Passport, Driving License
        """
        result = await self.extract_text(image)

        if result.get("error"):
            return result

        text = result["text"].upper()
        info = {"raw_text": result["text"], "confidence": result["confidence"]}

        # Pattern matching for Indian documents
        patterns = {
            # Aadhaar (12 digits, groups of 4)
            "aadhaar": r"\b\d{4}\s*\d{4}\s*\d{4}\b",
            # PAN (5 letters, 4 digits, 1 letter)
            "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
            # Passport (1 letter, 7 digits)
            "passport": r"\b[A-Z]\d{7}\b",
            # Driving License (state code + digits)
            "dl": r"\b[A-Z]{2}\d{2}\s*\d{4}\s*\d{7}\b",
            # Date patterns
            "dob": r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b",
            # Name pattern (after common prefixes)
            "name": r"(?:NAME|नाम)\s*[:\-]?\s*([A-Z\s]+)",
        }

        # Extract matches
        for key, pattern in patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                if key == "name":
                    info["name"] = matches[0].strip()
                elif key == "dob":
                    info["dob"] = matches[0]
                else:
                    info["document_number"] = matches[0].replace(" ", "")
                    info["document_type"] = key

        # Detect document type if not specified
        if "document_type" not in info:
            if "AADHAAR" in text or "आधार" in text:
                info["document_type"] = "aadhaar"
            elif "INCOME TAX" in text or "PAN" in text:
                info["document_type"] = "pan"
            elif "PASSPORT" in text or "REPUBLIC OF INDIA" in text:
                info["document_type"] = "passport"
            elif "DRIVING" in text or "LICENCE" in text:
                info["document_type"] = "driving_license"

        return info

    async def verify_document(
        self,
        image: np.ndarray,
        expected_name: Optional[str] = None,
        expected_dob: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify document and check against expected values"""
        doc_info = await self.extract_document_info(image)

        verification = {
            "document_detected": "document_type" in doc_info,
            "document_type": doc_info.get("document_type"),
            "document_number": doc_info.get("document_number"),
            "confidence": doc_info.get("confidence", 0),
            "name_match": None,
            "dob_match": None
        }

        # Verify name if provided
        if expected_name and doc_info.get("name"):
            extracted_name = doc_info["name"].upper().strip()
            expected = expected_name.upper().strip()
            # Simple matching - could use fuzzy matching
            verification["name_match"] = (
                expected in extracted_name or
                extracted_name in expected or
                self._name_similarity(extracted_name, expected) > 0.8
            )
            verification["extracted_name"] = doc_info["name"]

        # Verify DOB if provided
        if expected_dob and doc_info.get("dob"):
            verification["dob_match"] = self._normalize_date(doc_info["dob"]) == self._normalize_date(expected_dob)
            verification["extracted_dob"] = doc_info["dob"]

        return verification

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        words1 = set(name1.split())
        words2 = set(name2.split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string for comparison"""
        # Remove separators and normalize
        date_str = re.sub(r"[/\-\.]", "", date_str)
        return date_str


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get or create OCR service instance"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
