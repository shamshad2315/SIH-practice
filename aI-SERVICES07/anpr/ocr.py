"""
OCR module for License Plate character extraction using EasyOCR and regex post-processing.
"""

import re
import logging
from typing import Dict, Any, List, Optional
import numpy as np
from preprocessing.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

# Regular expressions for license plate formatting
# Standard Indian license plate pattern: MH12AB1234, DL01C1234, KA05MB9999, etc.
INDIAN_PLATE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$")
GENERIC_PLATE_REGEX = re.compile(r"^[A-Z0-9]{4,12}$")


class PlateOCR:
    """
    Extracts and standardizes license plate characters using EasyOCR.
    """

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
        min_conf: float = 0.35
    ):
        """
        Initialize PlateOCR.
        """
        self.languages = languages or ["en"]
        self.use_gpu = use_gpu
        self.min_conf = min_conf
        self._reader = None

    @property
    def reader(self):
        """
        Lazy loader for EasyOCR reader.
        """
        if self._reader is None:
            try:
                import easyocr
                logger.info(f"Initializing EasyOCR reader (Languages={self.languages}, GPU={self.use_gpu})...")
                self._reader = easyocr.Reader(self.languages, gpu=self.use_gpu, verbose=False)
                logger.info("EasyOCR reader initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
                self._reader = None
        return self._reader

    def clean_plate_text(self, raw_text: str) -> str:
        """
        Clean raw OCR text by removing noise, whitespace, and special characters.
        """
        # Upper case and remove all non-alphanumerics
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        return cleaned

    def standardize_plate_number(self, text: str) -> str:
        """
        Apply heuristic correction for common OCR character misclassifications:
        - Numbers in letter positions ('0' -> 'O', '8' -> 'B', '5' -> 'S', '1' -> 'I')
        - Letters in number positions ('O' -> '0', 'B' -> '8', 'S' -> '5', 'I' -> '1', 'Z' -> '2')
        """
        if not text:
            return ""

        cleaned = self.clean_plate_text(text)
        if len(cleaned) < 4:
            return cleaned

        chars = list(cleaned)

        # Indian plate format heuristic: 2 Letters + 1-2 Digits + 1-3 Letters + 4 Digits
        # E.g. [M, H] [1, 2] [A, B] [1, 2, 3, 4]
        if len(chars) >= 8 and len(chars) <= 11:
            # First 2 should be letters (State code)
            for i in range(min(2, len(chars))):
                if chars[i] == '0': chars[i] = 'O'
                elif chars[i] == '1': chars[i] = 'I'
                elif chars[i] == '8': chars[i] = 'B'
                elif chars[i] == '5': chars[i] = 'S'

            # Last 4 should be numbers
            for i in range(max(0, len(chars) - 4), len(chars)):
                if chars[i] == 'O' or chars[i] == 'Q' or chars[i] == 'D': chars[i] = '0'
                elif chars[i] == 'I' or chars[i] == 'L' or chars[i] == 'T': chars[i] = '1'
                elif chars[i] == 'Z': chars[i] = '2'
                elif chars[i] == 'S': chars[i] = '5'
                elif chars[i] == 'B': chars[i] = '8'

        return "".join(chars)

    def read_plate(
        self,
        plate_image: np.ndarray,
        enhance: bool = True
    ) -> Dict[str, Any]:
        """
        Read text from a cropped license plate image.

        Args:
            plate_image: Cropped plate BGR image array.
            enhance: Whether to apply CLAHE, filtering, and thresholding before OCR.

        Returns:
            Dictionary containing cleaned plate number, raw text, confidence score, and validation status.
        """
        if plate_image is None or plate_image.size == 0:
            return {
                "plate_number": "",
                "raw_text": "",
                "confidence": 0.0,
                "is_valid": False,
                "error": "Empty plate image provided"
            }

        if self.reader is None:
            return {
                "plate_number": "",
                "raw_text": "",
                "confidence": 0.0,
                "is_valid": False,
                "error": "EasyOCR engine not available"
            }

        try:
            # Try raw image first or enhanced image
            target_img = ImageProcessor.enhance_for_ocr(plate_image) if enhance else plate_image

            # Run EasyOCR
            results = self.reader.readtext(target_img, detail=1, paragraph=False)

            # If enhanced yielded no results, fallback to raw image
            if not results and enhance:
                results = self.reader.readtext(plate_image, detail=1, paragraph=False)

            if not results:
                return {
                    "plate_number": "",
                    "raw_text": "",
                    "confidence": 0.0,
                    "is_valid": False
                }

            # Aggregate text and calculate average confidence
            raw_text_parts = []
            confidences = []

            for bbox, text, conf in results:
                if conf >= self.min_conf:
                    raw_text_parts.append(text)
                    confidences.append(conf)

            if not raw_text_parts:
                # If all below min_conf, pick the highest one
                best = max(results, key=lambda x: x[2])
                raw_text_parts.append(best[1])
                confidences.append(best[2])

            raw_combined = " ".join(raw_text_parts)
            cleaned_text = self.standardize_plate_number(raw_combined)
            avg_conf = float(np.mean(confidences)) if confidences else 0.0

            is_valid = bool(
                INDIAN_PLATE_REGEX.match(cleaned_text) or
                GENERIC_PLATE_REGEX.match(cleaned_text)
            )

            return {
                "plate_number": cleaned_text,
                "raw_text": raw_combined,
                "confidence": round(avg_conf, 4),
                "is_valid": is_valid
            }

        except Exception as e:
            logger.error(f"OCR recognition failed: {e}", exc_info=True)
            return {
                "plate_number": "",
                "raw_text": "",
                "confidence": 0.0,
                "is_valid": False,
                "error": str(e)
            }
