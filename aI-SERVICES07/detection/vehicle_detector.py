"""
YOLO-based vehicle detector for cars, motorcycles, buses, trucks, and vans.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

# Standard COCO class mappings for vehicles
DEFAULT_VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


class VehicleDetector:
    """
    Vehicle detector using Ultralytics YOLO models.
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        device: str = "cpu",
        conf_threshold: float = 0.35,
        target_classes: Optional[Dict[int, str]] = None
    ):
        """
        Initialize YOLO model for vehicle detection.
        """
        self.model_path = model_path
        self.device = device
        self.conf_threshold = conf_threshold
        self.target_classes = target_classes or DEFAULT_VEHICLE_CLASSES
        self.model = None
        self._load_model()

    def _load_model(self):
        """
        Load YOLO weights safely.
        """
        try:
            from ultralytics import YOLO
            logger.info(f"Loading vehicle detection model from: {self.model_path}")
            self.model = YOLO(self.model_path)
            # Warm up or set device
            if self.device != "cpu":
                self.model.to(self.device)
            logger.info("Vehicle detection model loaded successfully.")
        except Exception as e:
            logger.warning(
                f"Failed to load YOLO model from '{self.model_path}': {e}. "
                "Detector will operate in mock/fallback mode until model is provided."
            )
            self.model = None

    def detect(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None,
        allowed_classes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run inference on the image and detect vehicles.

        Args:
            image: BGR numpy image.
            conf_threshold: Optional override for confidence threshold.
            allowed_classes: List of class names to filter (e.g. ['car', 'truck']).

        Returns:
            List of detected vehicle dictionaries containing bbox, confidence, class, center.
        """
        if image is None or image.size == 0:
            return []

        conf = conf_threshold if conf_threshold is not None else self.conf_threshold
        detections = []

        if self.model is None:
            logger.debug("Running in fallback/mock mode (model not initialized).")
            return detections

        try:
            # Run YOLO prediction
            # Filter by class IDs from target_classes
            class_ids = list(self.target_classes.keys())
            results = self.model.predict(
                source=image,
                conf=conf,
                classes=class_ids,
                device=self.device,
                verbose=False
            )

            for r in results:
                boxes = r.boxes
                for i, box in enumerate(boxes):
                    cls_id = int(box.cls[0].item())
                    score = float(box.conf[0].item())
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

                    cls_name = self.target_classes.get(cls_id, r.names.get(cls_id, f"class_{cls_id}"))

                    if allowed_classes and cls_name not in allowed_classes:
                        continue

                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    area = int((x2 - x1) * (y2 - y1))

                    detections.append({
                        "id": i + 1,
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "confidence": round(score, 4),
                        "bbox": [x1, y1, x2, y2],
                        "center": [cx, cy],
                        "area": area
                    })

        except Exception as e:
            logger.error(f"Error during vehicle detection: {e}", exc_info=True)

        return detections
