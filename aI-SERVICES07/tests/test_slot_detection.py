"""
Unit tests for Parking Slot Occupancy and IoU calculations.
"""

import pytest
from detection.slot_detector import SlotDetector


def test_calculate_bbox_iou():
    """
    Test standard Intersection over Union (IoU) calculation.
    """
    boxA = [0, 0, 100, 100]
    boxB = [0, 0, 100, 100]
    # Exact match should have IoU = 1.0
    assert pytest.approx(SlotDetector.calculate_bbox_iou(boxA, boxB), 0.01) == 1.0

    # No overlap should have IoU = 0.0
    boxC = [200, 200, 300, 300]
    assert SlotDetector.calculate_bbox_iou(boxA, boxC) == 0.0

    # Partial overlap (50x100 overlap)
    boxD = [50, 0, 150, 100]
    # Inter area = 50 * 100 = 5000, Union area = 10000 + 10000 - 5000 = 15000 -> IoU = 1/3 = 0.333
    assert pytest.approx(SlotDetector.calculate_bbox_iou(boxA, boxD), 0.02) == 0.333


def test_slot_evaluation_bbox():
    """
    Test slot occupancy evaluation with bounding boxes.
    """
    detector = SlotDetector(default_iou_threshold=0.25)

    slots = [
        {"slot_id": "A1", "bbox": [100, 100, 200, 200]}, # Occupied
        {"slot_id": "A2", "bbox": [300, 100, 400, 200]}  # Vacant
    ]

    vehicles = [
        {
            "id": 1,
            "class_name": "car",
            "confidence": 0.92,
            "bbox": [110, 105, 195, 195] # Overlaps slot A1 heavily
        }
    ]

    evaluated = detector.evaluate_slots(slots, vehicles)
    assert len(evaluated) == 2

    # A1 should be occupied
    slot_a1 = next(s for s in evaluated if s["slot_id"] == "A1")
    assert slot_a1["occupied"] is True
    assert slot_a1["vehicle"] is not None
    assert slot_a1["occupancy_ratio"] > 0.5

    # A2 should be vacant
    slot_a2 = next(s for s in evaluated if s["slot_id"] == "A2")
    assert slot_a2["occupied"] is False
    assert slot_a2["vehicle"] is None

    # Summary check
    summary = detector.summarize_occupancy(evaluated)
    assert summary["total_slots"] == 2
    assert summary["occupied_slots"] == 1
    assert summary["vacant_slots"] == 1
    assert summary["occupancy_percentage"] == 50.0


def test_slot_evaluation_polygon():
    """
    Test slot occupancy evaluation with polygon coordinates.
    """
    detector = SlotDetector(default_iou_threshold=0.20)

    polygon_slot = [
        {"slot_id": "P1", "polygon": [[50, 50], [150, 50], [150, 150], [50, 150]]}
    ]

    vehicles = [
        {"id": 1, "class_name": "car", "confidence": 0.88, "bbox": [60, 60, 140, 140]}
    ]

    evaluated = detector.evaluate_slots(polygon_slot, vehicles, image_shape=(500, 500))
    assert evaluated[0]["occupied"] is True
    assert evaluated[0]["occupancy_ratio"] > 0.5
