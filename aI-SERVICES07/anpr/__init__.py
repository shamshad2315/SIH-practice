"""
Automatic Number Plate Recognition (ANPR) Module.
"""
from .plate_detector import PlateDetector
from .ocr import PlateOCR

__all__ = ["PlateDetector", "PlateOCR"]
