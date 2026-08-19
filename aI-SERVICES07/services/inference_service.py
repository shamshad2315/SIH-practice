"""
Complete AI inference pipeline integrating Vehicle Detection, Parking Slot Analysis,
and Automatic Number Plate Recognition (ANPR).
"""

import time
import logging
from typing import Dict, Any, List, Optional
import numpy as np

from preprocessing.image_processor import ImageProcessor
from detection.vehicle_detector import VehicleDetector
from detection.slot_detector import SlotDetector
from anpr.plate_detector import PlateDetector
from anpr.ocr import PlateOCR

logger = logging.getLogger(__name__)


class InferenceService:
    """
    Orchestrates the complete computer vision pipeline.
    """

    def __init__(
        self,
        vehicle_model_path: str = "yolov8n.pt",
        plate_model_path: str = "models/plate_yolov8n.pt",
        device: str = "cpu",
        vehicle_conf: float = 0.35,
        plate_conf: float = 0.30,
        ocr_conf: float = 0.35,
        slot_iou_thresh: float = 0.20
    ):
        """
        Initialize all detection, OCR, and analysis sub-modules.
        """
        logger.info("Initializing AI Inference Pipeline...")
        self.device = device
        self.vehicle_detector = VehicleDetector(
            model_path=vehicle_model_path,
            device=device,
            conf_threshold=vehicle_conf
        )
        self.plate_detector = PlateDetector(
            model_path=plate_model_path,
            device=device,
            conf_threshold=plate_conf
        )
        self.plate_ocr = PlateOCR(
            languages=["en"],
            use_gpu=(device != "cpu"),
            min_conf=ocr_conf
        )
        self.slot_detector = SlotDetector(default_iou_threshold=slot_iou_thresh)
        logger.info("AI Inference Pipeline initialized successfully.")

    def run_vehicle_detection(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Run vehicle detection only.
        """
        start_time = time.perf_counter()
        vehicles = self.vehicle_detector.detect(image, conf_threshold=conf_threshold)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "vehicle_count": len(vehicles),
            "vehicles": vehicles,
            "latency_ms": elapsed_ms
        }

    def run_slot_analysis(
        self,
        image: np.ndarray,
        slots: List[Dict[str, Any]],
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect vehicles and calculate parking slot occupancy.
        """
        start_time = time.perf_counter()
        
        # 1. Detect vehicles
        vehicles = self.vehicle_detector.detect(image, conf_threshold=conf_threshold)

        # 2. Evaluate slot occupancy
        h, w = image.shape[:2]
        evaluated_slots = self.slot_detector.evaluate_slots(
            slots=slots,
            vehicles=vehicles,
            iou_threshold=iou_threshold,
            image_shape=(h, w)
        )

        summary = self.slot_detector.summarize_occupancy(evaluated_slots)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "summary": summary,
            "slots": evaluated_slots,
            "vehicles": vehicles,
            "latency_ms": elapsed_ms
        }

    def run_anpr(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Run license plate detection and OCR on the image.
        """
        start_time = time.perf_counter()

        # 1. Detect license plate candidates
        plate_candidates = self.plate_detector.detect_plates(image, conf_threshold=conf_threshold)

        # 2. Run OCR on each plate candidate
        recognized_plates = []
        for candidate in plate_candidates:
            cropped = candidate.get("cropped_plate")
            if cropped is not None and cropped.size > 0:
                ocr_res = self.plate_ocr.read_plate(cropped, enhance=True)
                
                # Only include if text was extracted
                if ocr_res.get("plate_number"):
                    recognized_plates.append({
                        "id": candidate.get("id"),
                        "bbox": candidate.get("bbox"),
                        "detection_confidence": candidate.get("confidence"),
                        "plate_number": ocr_res.get("plate_number"),
                        "raw_text": ocr_res.get("raw_text"),
                        "ocr_confidence": ocr_res.get("confidence"),
                        "is_valid_format": ocr_res.get("is_valid")
                    })

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "plate_count": len(recognized_plates),
            "plates": recognized_plates,
            "latency_ms": elapsed_ms
        }

    def run_full_pipeline(
        self,
        image: np.ndarray,
        slots: Optional[List[Dict[str, Any]]] = None,
        return_annotated_image: bool = True
    ) -> Dict[str, Any]:
        """
        Execute full pipeline:
        1. Vehicle Detection
        2. Parking Slot Occupancy (if slots provided)
        3. ANPR (Plate Localization & EasyOCR) for each detected vehicle / full image
        4. Optional Annotated Overlay Image (Base64)
        """
        start_time = time.perf_counter()
        h, w = image.shape[:2]

        # 1. Detect Vehicles
        vehicles = self.vehicle_detector.detect(image)

        # 2. Evaluate Slots (if provided)
        evaluated_slots = []
        slot_summary = None
        if slots:
            evaluated_slots = self.slot_detector.evaluate_slots(
                slots=slots,
                vehicles=vehicles,
                image_shape=(h, w)
            )
            slot_summary = self.slot_detector.summarize_occupancy(evaluated_slots)

        # 3. Detect & Read License Plates
        # First check plates on full image
        plates_res = self.run_anpr(image)
        recognized_plates = plates_res.get("plates", [])

        # If no plates found on full image, attempt plate detection on cropped vehicle ROIs
        if not recognized_plates and vehicles:
            for veh in vehicles:
                v_bbox = veh.get("bbox")
                if v_bbox:
                    v_crop = ImageProcessor.crop_roi(image, v_bbox)
                    sub_plates = self.plate_detector.detect_plates(v_crop)
                    for sp in sub_plates:
                        sp_crop = sp.get("cropped_plate")
                        if sp_crop is not None and sp_crop.size > 0:
                            ocr_res = self.plate_ocr.read_plate(sp_crop)
                            if ocr_res.get("plate_number"):
                                # Map back bounding box to original image coordinates
                                vx1, vy1 = v_bbox[0], v_bbox[1]
                                px1, py1, px2, py2 = sp.get("bbox", [0, 0, 0, 0])
                                global_bbox = [vx1 + px1, vy1 + py1, vx1 + px2, vy1 + py2]
                                
                                recognized_plates.append({
                                    "id": len(recognized_plates) + 1,
                                    "vehicle_id": veh.get("id"),
                                    "bbox": global_bbox,
                                    "detection_confidence": sp.get("confidence"),
                                    "plate_number": ocr_res.get("plate_number"),
                                    "raw_text": ocr_res.get("raw_text"),
                                    "ocr_confidence": ocr_res.get("confidence"),
                                    "is_valid_format": ocr_res.get("is_valid")
                                })

        # 4. Generate Annotated Image Overlay (Optional)
        annotated_b64 = None
        if return_annotated_image:
            overlay_img = ImageProcessor.draw_overlays(
                image=image,
                vehicles=vehicles,
                slots=evaluated_slots,
                plates=recognized_plates
            )
            annotated_b64 = ImageProcessor.to_base64(overlay_img)

        total_latency = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "status": "success",
            "metadata": {
                "image_width": w,
                "image_height": h,
                "latency_ms": total_latency,
                "device": self.device
            },
            "vehicles": {
                "count": len(vehicles),
                "items": vehicles
            },
            "parking_slots": {
                "summary": slot_summary,
                "items": evaluated_slots
            } if slots else None,
            "anpr": {
                "count": len(recognized_plates),
                "items": recognized_plates
            },
            "annotated_image": annotated_b64
        }
