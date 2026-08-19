"""
Parking slot detection and occupancy calculation module.
Computes IoU/overlap between defined parking slot regions and detected vehicles.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class SlotDetector:
    """
    Evaluates parking slot status (Occupied vs. Vacant) based on geometric overlap
    between predefined/detected parking regions and detected vehicle bounding boxes.
    """

    def __init__(self, default_iou_threshold: float = 0.20):
        """
        Initialize SlotDetector with overlap threshold.
        """
        self.default_iou_threshold = default_iou_threshold

    @staticmethod
    def calculate_bbox_iou(boxA: List[int], boxB: List[int]) -> float:
        """
        Compute Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2].
        """
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        inter_width = max(0, xB - xA)
        inter_height = max(0, yB - yA)
        inter_area = inter_width * inter_height

        if inter_area == 0:
            return 0.0

        boxA_area = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
        boxB_area = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

        iou = inter_area / float(boxA_area + boxB_area - inter_area)
        return float(iou)

    @staticmethod
    def calculate_intersection_over_slot_area(slot_bbox: List[int], vehicle_bbox: List[int]) -> float:
        """
        Calculate the ratio of the slot area that is covered by the vehicle bbox.
        (Intersection Area / Slot Area)
        """
        xA = max(slot_bbox[0], vehicle_bbox[0])
        yA = max(slot_bbox[1], vehicle_bbox[1])
        xB = min(slot_bbox[2], vehicle_bbox[2])
        yB = min(slot_bbox[3], vehicle_bbox[3])

        inter_width = max(0, xB - xA)
        inter_height = max(0, yB - yA)
        inter_area = inter_width * inter_height

        slot_area = max(1, (slot_bbox[2] - slot_bbox[0]) * (slot_bbox[3] - slot_bbox[1]))
        return float(inter_area / slot_area)

    @staticmethod
    def calculate_polygon_overlap(
        polygon: List[List[int]],
        vehicle_bbox: List[int],
        canvas_size: Tuple[int, int] = (1080, 1920)
    ) -> float:
        """
        Compute polygon slot occupancy ratio with a vehicle bounding box using binary masks.
        """
        try:
            # Create binary mask for slot polygon
            slot_mask = np.zeros(canvas_size, dtype=np.uint8)
            poly_pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(slot_mask, [poly_pts], 255)
            slot_area = cv2.countNonZero(slot_mask)
            if slot_area == 0:
                return 0.0

            # Create binary mask for vehicle bbox
            veh_mask = np.zeros(canvas_size, dtype=np.uint8)
            x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
            cv2.rectangle(veh_mask, (x1, y1), (x2, y2), 255, -1)

            # Intersection mask
            inter_mask = cv2.bitwise_and(slot_mask, veh_mask)
            inter_area = cv2.countNonZero(inter_mask)

            return float(inter_area / slot_area)
        except Exception as e:
            logger.warning(f"Failed to calculate polygon overlap: {e}")
            return 0.0

    def evaluate_slots(
        self,
        slots: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        iou_threshold: Optional[float] = None,
        image_shape: Optional[Tuple[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate a list of parking slots against detected vehicles.

        Args:
            slots: List of slot configs, e.g. [{"slot_id": "A1", "bbox": [x1,y1,x2,y2]}] or with "polygon"
            vehicles: List of detected vehicles from VehicleDetector
            iou_threshold: Minimum overlap ratio to consider occupied (defaults to self.default_iou_threshold)
            image_shape: (height, width) for polygon mask calculation

        Returns:
            List of evaluated slots with occupancy status, vehicle info, and confidence ratio.
        """
        threshold = iou_threshold if iou_threshold is not None else self.default_iou_threshold
        canvas_size = image_shape if image_shape else (1080, 1920)
        evaluated_slots = []

        for slot in slots:
            slot_id = slot.get("slot_id", f"slot_{len(evaluated_slots) + 1}")
            slot_type = slot.get("slot_type", "standard")
            is_occupied = False
            best_overlap = 0.0
            matched_vehicle = None

            # 1. Evaluate Polygon Slots
            if "polygon" in slot and slot["polygon"]:
                poly = slot["polygon"]
                for veh in vehicles:
                    v_bbox = veh.get("bbox", [])
                    if len(v_bbox) == 4:
                        overlap = self.calculate_polygon_overlap(poly, v_bbox, canvas_size)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            matched_vehicle = veh

                is_occupied = best_overlap >= threshold

                evaluated_slots.append({
                    "slot_id": slot_id,
                    "slot_type": slot_type,
                    "polygon": poly,
                    "occupied": bool(is_occupied),
                    "occupancy_ratio": round(best_overlap, 4),
                    "vehicle": matched_vehicle if is_occupied else None
                })

            # 2. Evaluate Rectangular BBox Slots
            elif "bbox" in slot and slot["bbox"]:
                s_bbox = slot["bbox"]
                for veh in vehicles:
                    v_bbox = veh.get("bbox", [])
                    if len(v_bbox) == 4:
                        overlap = self.calculate_intersection_over_slot_area(s_bbox, v_bbox)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            matched_vehicle = veh

                is_occupied = best_overlap >= threshold

                evaluated_slots.append({
                    "slot_id": slot_id,
                    "slot_type": slot_type,
                    "bbox": s_bbox,
                    "occupied": bool(is_occupied),
                    "occupancy_ratio": round(best_overlap, 4),
                    "vehicle": matched_vehicle if is_occupied else None
                })
            else:
                evaluated_slots.append({
                    "slot_id": slot_id,
                    "slot_type": slot_type,
                    "occupied": False,
                    "occupancy_ratio": 0.0,
                    "vehicle": None,
                    "error": "Missing valid 'bbox' or 'polygon' configuration"
                })

        return evaluated_slots

    @staticmethod
    def summarize_occupancy(evaluated_slots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary metrics from evaluated parking slots.
        """
        total = len(evaluated_slots)
        occupied = sum(1 for s in evaluated_slots if s.get("occupied", False))
        vacant = total - occupied
        occupancy_rate = round((occupied / total * 100), 2) if total > 0 else 0.0

        return {
            "total_slots": total,
            "occupied_slots": occupied,
            "vacant_slots": vacant,
            "occupancy_percentage": occupancy_rate
        }
