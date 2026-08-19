"""
License plate detection module using YOLO and morphological contour fallback.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class PlateDetector:
    """
    Detects vehicle license plates using dedicated YOLO weights or contour-based heuristics.
    """

    def __init__(
        self,
        model_path: str = "models/plate_yolov8n.pt",
        device: str = "cpu",
        conf_threshold: float = 0.30
    ):
        """
        Initialize the license plate detector.
        """
        self.model_path = model_path
        self.device = device
        self.conf_threshold = conf_threshold
        self.model = None
        self._load_model()

    def _load_model(self):
        """
        Attempt to load YOLO license plate weights if available.
        """
        if os.path.exists(self.model_path):
            try:
                from ultralytics import YOLO
                logger.info(f"Loading license plate YOLO model from: {self.model_path}")
                self.model = YOLO(self.model_path)
                if self.device != "cpu":
                    self.model.to(self.device)
                logger.info("License plate model loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load plate model '{self.model_path}': {e}. Using contour detector fallback.")
                self.model = None
        else:
            logger.info(
                f"Plate model '{self.model_path}' not found on disk. "
                "PlateDetector will use adaptive morphological contour detection fallback."
            )
            self.model = None

    def detect_plates(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect license plates in the input image.

        Args:
            image: BGR numpy image.
            conf_threshold: Optional confidence threshold override.

        Returns:
            List of detected plates with bboxes, confidence, and cropped plate arrays.
        """
        if image is None or image.size == 0:
            return []

        conf = conf_threshold if conf_threshold is not None else self.conf_threshold

        # 1. Use YOLO model if loaded
        if self.model is not None:
            return self._detect_with_yolo(image, conf)

        # 2. Use Morphological & Contour-based fallback
        return self._detect_with_contours(image)

    def _detect_with_yolo(self, image: np.ndarray, conf: float) -> List[Dict[str, Any]]:
        """
        Detect plates using YOLO model.
        """
        detections = []
        try:
            results = self.model.predict(
                source=image,
                conf=conf,
                device=self.device,
                verbose=False
            )

            h, w = image.shape[:2]
            for r in results:
                for i, box in enumerate(r.boxes):
                    score = float(box.conf[0].item())
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

                    # Clamp boundaries
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)

                    cropped = image[y1:y2, x1:x2]
                    detections.append({
                        "id": i + 1,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(score, 4),
                        "cropped_plate": cropped,
                        "method": "yolo"
                    })
        except Exception as e:
            logger.error(f"YOLO plate detection failed: {e}. Falling back to contours.")
            return self._detect_with_contours(image)

        return detections

    def _detect_with_contours(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Adaptive morphological contour detection fallback for rectangular license plates.
        """
        detections = []
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Noise filtering & Sobel gradient along X-axis
            blur = cv2.bilateralFilter(gray, 11, 17, 17)
            grad_x = cv2.Sobel(blur, cv2.CV_16S, 1, 0, ksize=3)
            abs_grad_x = cv2.convertScaleAbs(grad_x)

            # Morphological close to connect text regions
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
            morph = cv2.morphologyEx(abs_grad_x, cv2.MORPH_CLOSE, kernel)

            # Thresholding
            _, thresh = cv2.threshold(morph, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            candidate_idx = 1
            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = cw / float(max(1, ch))
                area = cw * ch

                # Standard license plate aspect ratio is between 2.0 and 6.0
                # Plate area should be at least 0.1% and at most 20% of image
                min_area = (h * w) * 0.001
                max_area = (h * w) * 0.25

                if 2.0 <= aspect_ratio <= 6.0 and min_area <= area <= max_area:
                    x1, y1 = max(0, x), max(0, y)
                    x2, y2 = min(w, x + cw), min(h, y + ch)
                    cropped = image[y1:y2, x1:x2]

                    detections.append({
                        "id": candidate_idx,
                        "bbox": [x1, y1, x2, y2],
                        "confidence": 0.70, # Baseline heuristic confidence
                        "cropped_plate": cropped,
                        "method": "contour_heuristic"
                    })
                    candidate_idx += 1

            # Limit candidates to top 5 largest by area
            detections.sort(key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]), reverse=True)
            return detections[:5]

        except Exception as e:
            logger.error(f"Contour plate detection error: {e}")
            return []
