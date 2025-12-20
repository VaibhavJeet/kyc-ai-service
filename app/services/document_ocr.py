"""
Document OCR Service using PaddleOCR
Provides high-accuracy text extraction from identity documents
"""

import numpy as np
from typing import Optional, Dict, Any, List
import cv2
from PIL import Image
import io
import base64
import re
import structlog

from ..config import settings

logger = structlog.get_logger()


class DocumentOCRService:
    """
    Document text extraction using PaddleOCR.
    Features:
    - Multi-language support (English, Hindi for Indian docs)
    - Document type detection
    - Field extraction (name, DOB, document number)
    - MRZ parsing for passports
    """

    def __init__(self):
        self._ocr = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize PaddleOCR"""
        try:
            from paddleocr import PaddleOCR

            logger.info("Initializing PaddleOCR...")

            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",  # English + supports Hindi
                use_gpu=settings.USE_GPU,
                show_log=False,
                det_model_dir=None,  # Use default models
                rec_model_dir=None,
                cls_model_dir=None,
            )

            self._initialized = True
            logger.info("PaddleOCR initialized successfully")
            return True
        except Exception as e:
            logger.error("Failed to initialize PaddleOCR", error=str(e))
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
            return np.array(pil_image.convert("RGB"))
        except Exception as e:
            logger.error("Failed to decode image", error=str(e))
            return None

    def extract_text(self, image_data: str) -> Dict[str, Any]:
        """
        Extract all text from document image.
        Returns list of detected text with bounding boxes and confidence.
        """
        result = {
            "texts": [],
            "full_text": "",
            "confidence": 0.0,
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
            ocr_result = self._ocr.ocr(image, cls=True)

            if not ocr_result or not ocr_result[0]:
                result["error"] = "No text detected"
                return result

            texts = []
            full_text_parts = []
            total_confidence = 0.0

            for line in ocr_result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]

                texts.append(
                    {
                        "text": text,
                        "bbox": bbox,
                        "confidence": float(confidence),
                    }
                )
                full_text_parts.append(text)
                total_confidence += confidence

            result["texts"] = texts
            result["full_text"] = " ".join(full_text_parts)
            result["confidence"] = total_confidence / len(texts) if texts else 0.0

            return result
        except Exception as e:
            logger.error("OCR extraction failed", error=str(e))
            result["error"] = str(e)
            return result

    def detect_document_type(self, image_data: str) -> Dict[str, Any]:
        """
        Detect the type of identity document.
        Supports: Aadhaar, PAN, Passport, Driving License, Voter ID
        """
        result = {
            "document_type": None,
            "confidence": 0.0,
            "detected_keywords": [],
            "error": None,
        }

        ocr_result = self.extract_text(image_data)
        if ocr_result.get("error"):
            result["error"] = ocr_result["error"]
            return result

        full_text = ocr_result["full_text"].upper()

        # Document type indicators
        indicators = {
            "aadhaar": ["AADHAAR", "UNIQUE IDENTIFICATION", "UIDAI", "आधार", "VID"],
            "pan": ["INCOME TAX", "PERMANENT ACCOUNT", "PAN", "GOVT OF INDIA"],
            "passport": ["PASSPORT", "REPUBLIC OF INDIA", "P<IND", "TRAVEL DOCUMENT"],
            "driving_license": ["DRIVING", "LICENCE", "LICENSE", "TRANSPORT", "RTO", "MOTOR"],
            "voter_id": ["ELECTION", "VOTER", "ELECTOR", "EPIC", "ELECTORS PHOTO"],
        }

        matches = {}
        detected_keywords = []

        for doc_type, keywords in indicators.items():
            match_count = 0
            for keyword in keywords:
                if keyword in full_text:
                    match_count += 1
                    detected_keywords.append(keyword)

            if match_count > 0:
                matches[doc_type] = match_count

        if matches:
            # Get the document type with most matches
            best_match = max(matches, key=matches.get)
            result["document_type"] = best_match
            result["confidence"] = min(1.0, matches[best_match] / 3)  # Normalize
            result["detected_keywords"] = detected_keywords
        else:
            result["document_type"] = "unknown"
            result["confidence"] = 0.0

        return result

    def extract_fields(self, image_data: str, document_type: str) -> Dict[str, Any]:
        """
        Extract specific fields based on document type.
        Returns structured data: name, DOB, document number, etc.
        """
        result = {
            "fields": {},
            "raw_text": "",
            "error": None,
        }

        ocr_result = self.extract_text(image_data)
        if ocr_result.get("error"):
            result["error"] = ocr_result["error"]
            return result

        full_text = ocr_result["full_text"]
        result["raw_text"] = full_text

        # Extract fields based on document type
        if document_type == "aadhaar":
            result["fields"] = self._extract_aadhaar_fields(full_text)
        elif document_type == "pan":
            result["fields"] = self._extract_pan_fields(full_text)
        elif document_type == "passport":
            result["fields"] = self._extract_passport_fields(full_text)
        elif document_type == "driving_license":
            result["fields"] = self._extract_dl_fields(full_text)
        elif document_type == "voter_id":
            result["fields"] = self._extract_voter_fields(full_text)
        else:
            result["fields"] = self._extract_generic_fields(full_text)

        return result

    def _extract_aadhaar_fields(self, text: str) -> Dict[str, Any]:
        """Extract fields from Aadhaar card"""
        fields = {}

        # Aadhaar number: 12 digits, often with spaces (XXXX XXXX XXXX)
        aadhaar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"
        aadhaar_match = re.search(aadhaar_pattern, text)
        if aadhaar_match:
            fields["document_number"] = aadhaar_match.group().replace(" ", "")
            # Mask for privacy
            fields["masked_number"] = f"XXXX-XXXX-{fields['document_number'][-4:]}"

        # DOB: DD/MM/YYYY or DD-MM-YYYY
        dob_pattern = r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b"
        dob_match = re.search(dob_pattern, text)
        if dob_match:
            fields["dob"] = dob_match.group()

        # Name: Usually after "Name:" or is capitalized line
        name_patterns = [
            r"(?:Name|नाम)\s*[:\s]+([A-Z][A-Za-z\s]+)",
            r"\b([A-Z]{2,}(?:\s+[A-Z]{2,})+)\b",
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                fields["name"] = name_match.group(1).strip()
                break

        # Gender
        if "MALE" in text.upper() or "पुरुष" in text:
            fields["gender"] = "M"
        elif "FEMALE" in text.upper() or "महिला" in text:
            fields["gender"] = "F"

        return fields

    def _extract_pan_fields(self, text: str) -> Dict[str, Any]:
        """Extract fields from PAN card"""
        fields = {}

        # PAN number: AAAAA0000A format
        pan_pattern = r"\b[A-Z]{5}\d{4}[A-Z]\b"
        pan_match = re.search(pan_pattern, text.upper())
        if pan_match:
            fields["document_number"] = pan_match.group()

        # Name
        name_pattern = r"(?:Name|नाम)\s*[:\s]+([A-Z][A-Za-z\s]+)"
        name_match = re.search(name_pattern, text, re.IGNORECASE)
        if name_match:
            fields["name"] = name_match.group(1).strip()

        # Father's name
        father_pattern = r"(?:Father|पिता)\s*[:\s]+([A-Z][A-Za-z\s]+)"
        father_match = re.search(father_pattern, text, re.IGNORECASE)
        if father_match:
            fields["father_name"] = father_match.group(1).strip()

        # DOB
        dob_pattern = r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b"
        dob_match = re.search(dob_pattern, text)
        if dob_match:
            fields["dob"] = dob_match.group()

        return fields

    def _extract_passport_fields(self, text: str) -> Dict[str, Any]:
        """Extract fields from Passport including MRZ"""
        fields = {}

        # Passport number
        passport_pattern = r"\b[A-Z]\d{7}\b"
        passport_match = re.search(passport_pattern, text.upper())
        if passport_match:
            fields["document_number"] = passport_match.group()

        # MRZ parsing (Machine Readable Zone)
        mrz_pattern = r"P<IND([A-Z<]+)<<([A-Z<]+)"
        mrz_match = re.search(mrz_pattern, text.upper())
        if mrz_match:
            surname = mrz_match.group(1).replace("<", " ").strip()
            given_names = mrz_match.group(2).replace("<", " ").strip()
            fields["surname"] = surname
            fields["given_names"] = given_names
            fields["name"] = f"{given_names} {surname}".strip()

        # DOB from MRZ (YYMMDD format)
        mrz_dob_pattern = r"\d{7}[MF<]\d{7}"
        mrz_dob_match = re.search(mrz_dob_pattern, text)
        if mrz_dob_match:
            mrz_line = mrz_dob_match.group()
            dob_raw = mrz_line[:6]
            # Convert YYMMDD to DD/MM/YYYY
            year = int(dob_raw[:2])
            year = 2000 + year if year < 50 else 1900 + year
            fields["dob"] = f"{dob_raw[4:6]}/{dob_raw[2:4]}/{year}"

        return fields

    def _extract_dl_fields(self, text: str) -> Dict[str, Any]:
        """Extract fields from Driving License"""
        fields = {}

        # DL number varies by state, generally alphanumeric
        dl_patterns = [
            r"\b[A-Z]{2}\d{2}\s?\d{11}\b",  # Standard format
            r"\b[A-Z]{2}-\d{2}-\d{4}-\d{7}\b",  # Alternative format
        ]
        for pattern in dl_patterns:
            dl_match = re.search(pattern, text.upper())
            if dl_match:
                fields["document_number"] = dl_match.group().replace(" ", "")
                break

        # Name
        name_pattern = r"(?:Name|नाम)\s*[:\s]+([A-Z][A-Za-z\s]+)"
        name_match = re.search(name_pattern, text, re.IGNORECASE)
        if name_match:
            fields["name"] = name_match.group(1).strip()

        # DOB
        dob_pattern = r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b"
        dob_match = re.search(dob_pattern, text)
        if dob_match:
            fields["dob"] = dob_match.group()

        return fields

    def _extract_voter_fields(self, text: str) -> Dict[str, Any]:
        """Extract fields from Voter ID (EPIC)"""
        fields = {}

        # EPIC number: 3 letters + 7 digits
        epic_pattern = r"\b[A-Z]{3}\d{7}\b"
        epic_match = re.search(epic_pattern, text.upper())
        if epic_match:
            fields["document_number"] = epic_match.group()

        # Name
        name_pattern = r"(?:Name|Elector)\s*[:\s]+([A-Z][A-Za-z\s]+)"
        name_match = re.search(name_pattern, text, re.IGNORECASE)
        if name_match:
            fields["name"] = name_match.group(1).strip()

        return fields

    def _extract_generic_fields(self, text: str) -> Dict[str, Any]:
        """Extract common fields from unknown document type"""
        fields = {}

        # Try to find any date
        date_pattern = r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b"
        date_match = re.search(date_pattern, text)
        if date_match:
            fields["date_found"] = date_match.group()

        # Try to find any alphanumeric ID
        id_pattern = r"\b[A-Z]{2,5}\d{6,12}\b"
        id_match = re.search(id_pattern, text.upper())
        if id_match:
            fields["possible_id"] = id_match.group()

        return fields


# Singleton instance
document_ocr_service = DocumentOCRService()
