"""
Unit tests for Vehicle Detection and Image Preprocessing.
"""

import numpy as np
import cv2
import pytest

from preprocessing.image_processor import ImageProcessor
from detection.vehicle_detector import VehicleDetector


def test_image_processor_encoding_decoding():
    """
    Test image decoding from bytes, encoding, and base64 round-trip.
    """
    # Create a synthetic 100x100 RGB image
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    dummy_img[20:80, 20:80] = [0, 255, 0] # Green square

    # Encode to bytes
    encoded_bytes = ImageProcessor.encode_image(dummy_img, ext=".jpg")
    assert isinstance(encoded_bytes, bytes)
    assert len(encoded_bytes) > 0

    # Decode back
    decoded_img = ImageProcessor.decode_image(encoded_bytes)
    assert decoded_img.shape == (100, 100, 3)

    # Base64 test
    b64_str = ImageProcessor.to_base64(dummy_img)
    assert isinstance(b64_str, str)
    decoded_from_b64 = ImageProcessor.from_base64(b64_str)
    assert decoded_from_b64.shape == (100, 100, 3)


def test_image_processor_crop_roi():
    """
    Test safe ROI cropping with out-of-boundary values.
    """
    img = np.zeros((200, 300, 3), dtype=np.uint8)
    
    # Valid crop
    crop = ImageProcessor.crop_roi(img, [10, 10, 50, 60])
    assert crop.shape == (50, 40, 3)

    # Out of bounds crop should be clamped safely
    crop_oob = ImageProcessor.crop_roi(img, [-20, -10, 500, 400])
    assert crop_oob.shape == (200, 300, 3)


def test_vehicle_detector_initialization():
    """
    Test VehicleDetector class instantiation.
    """
    detector = VehicleDetector(model_path="non_existent_model.pt", device="cpu")
    # Empty image should return empty list gracefully
    empty_img = np.zeros((100, 100, 3), dtype=np.uint8)
    results = detector.detect(empty_img)
    assert isinstance(results, list)
