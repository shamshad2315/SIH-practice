"""
Unit tests for License Plate Detection and OCR formatting.
"""

import numpy as np
import pytest
from anpr.ocr import PlateOCR, INDIAN_PLATE_REGEX, GENERIC_PLATE_REGEX
from anpr.plate_detector import PlateDetector


def test_plate_ocr_text_cleaner():
    """
    Test plate text cleaning and standardization heuristics.
    """
    ocr = PlateOCR()

    # Test stripping noise and spacing
    assert ocr.clean_plate_text("MH-12-AB-1234") == "MH12AB1234"
    assert ocr.clean_plate_text(" dl 01 c 9999 ") == "DL01C9999"
    assert ocr.clean_plate_text("KA.05#MB@1234") == "KA05MB1234"

    # Test OCR misclassification corrections for Indian plates
    # 'O' in number spot should become '0', '0' in state spot should become 'O'
    raw_misclassified = "MH12AB123O" # Last char is letter 'O' instead of digit '0'
    corrected = ocr.standardize_plate_number(raw_misclassified)
    assert corrected == "MH12AB1230"


def test_plate_regex_patterns():
    """
    Test Indian and generic license plate regular expression validation.
    """
    # Valid Indian plates
    assert INDIAN_PLATE_REGEX.match("MH12AB1234") is not None
    assert INDIAN_PLATE_REGEX.match("DL01C1234") is not None
    assert INDIAN_PLATE_REGEX.match("KA05MB9999") is not None
    assert INDIAN_PLATE_REGEX.match("HR26DK8337") is not None

    # Invalid Indian plates
    assert INDIAN_PLATE_REGEX.match("1234MH") is None
    assert INDIAN_PLATE_REGEX.match("ABC") is None

    # Generic plates
    assert GENERIC_PLATE_REGEX.match("CALIFORNIA1") is not None
    assert GENERIC_PLATE_REGEX.match("7ABC123") is not None


def test_plate_detector_contours_fallback():
    """
    Test contour-based plate detection on synthetic image.
    """
    detector = PlateDetector(model_path="non_existent.pt")
    
    # Create synthetic image with a rectangular white plate on dark background
    image = np.zeros((400, 600, 3), dtype=np.uint8)
    # Draw white rectangle with aspect ratio ~ 3.5
    image[180:230, 200:375] = 255 # height=50, width=175 -> aspect ratio = 3.5

    plates = detector.detect_plates(image)
    assert isinstance(plates, list)
