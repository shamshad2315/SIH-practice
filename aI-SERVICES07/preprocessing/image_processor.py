"""
Image preprocessing and enhancement module for vehicle detection,
slot occupancy analysis, and ANPR/OCR optimization.
"""

import base64
from typing import List, Tuple, Optional, Union, Dict, Any
import cv2
import numpy as np


class ImageProcessor:
    """
    Comprehensive image processing utilities for CV pipelines.
    """

    @staticmethod
    def decode_image(image_bytes: bytes) -> np.ndarray:
        """
        Convert raw bytes (from HTTP upload) to an OpenCV BGR numpy array.
        """
        if not image_bytes:
            raise ValueError("Empty image bytes received.")
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode image from provided bytes. Invalid format.")
        return image

    @staticmethod
    def encode_image(image: np.ndarray, ext: str = ".jpg", quality: int = 90) -> bytes:
        """
        Encode an OpenCV image to JPEG/PNG bytes.
        """
        if image is None or image.size == 0:
            raise ValueError("Cannot encode empty image.")
        
        params = []
        if ext.lower() in [".jpg", ".jpeg"]:
            params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        elif ext.lower() == ".png":
            params = [int(cv2.IMWRITE_PNG_COMPRESSION), 4]
            
        success, encoded = cv2.imencode(ext, image, params)
        if not success:
            raise RuntimeError("Failed to encode image.")
        return encoded.tobytes()

    @staticmethod
    def to_base64(image: np.ndarray, ext: str = ".jpg") -> str:
        """
        Encode OpenCV image to base64 string.
        """
        img_bytes = ImageProcessor.encode_image(image, ext=ext)
        return base64.b64encode(img_bytes).decode("utf-8")

    @staticmethod
    def from_base64(b64_string: str) -> np.ndarray:
        """
        Decode base64 string to OpenCV BGR image.
        """
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_string)
        return ImageProcessor.decode_image(img_bytes)

    @staticmethod
    def crop_roi(image: np.ndarray, bbox: Union[List[int], Tuple[int, int, int, int]]) -> np.ndarray:
        """
        Safely crop a bounding box [x1, y1, x2, y2] from an image with boundary clipping.
        """
        h, w = image.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in bbox]
        
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))
        
        cropped = image[y1:y2, x1:x2]
        return cropped

    @staticmethod
    def resize_keep_aspect(image: np.ndarray, max_dim: int = 1280) -> np.ndarray:
        """
        Resize image while maintaining aspect ratio so that the longest edge is <= max_dim.
        """
        h, w = image.shape[:2]
        if max(h, w) <= max_dim:
            return image.copy()
        
        if h > w:
            new_h = max_dim
            new_w = int(w * (max_dim / h))
        else:
            new_w = max_dim
            new_h = int(h * (max_dim / w))
            
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """
        Apply contrast enhancement, noise reduction, and binarization
        to optimize license plate characters for OCR engines.
        """
        if image is None or image.size == 0:
            return image

        # 1. Convert to Grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 2. Resize to a minimum height for OCR clarity
        min_height = 80
        h, w = gray.shape
        if h < min_height:
            scale = min_height / float(h)
            gray = cv2.resize(gray, (int(w * scale), min_height), interpolation=cv2.INTER_CUBIC)

        # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 4. Bilateral Filter to smooth noise while keeping edges sharp
        filtered = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)

        # 5. Adaptive Threshold / Otsu Thresholding
        _, binarized = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return binarized

    @staticmethod
    def draw_overlays(
        image: np.ndarray,
        vehicles: Optional[List[Dict[str, Any]]] = None,
        slots: Optional[List[Dict[str, Any]]] = None,
        plates: Optional[List[Dict[str, Any]]] = None
    ) -> np.ndarray:
        """
        Draw visual overlays for vehicles, parking slots, and recognized license plates.
        """
        output = image.copy()

        # 1. Draw Parking Slots
        if slots:
            for slot in slots:
                is_occupied = slot.get("occupied", False)
                color = (0, 0, 230) if is_occupied else (0, 200, 0) # Red if occupied, Green if vacant
                slot_id = str(slot.get("slot_id", "Slot"))
                
                # Check if polygon or bbox
                if "polygon" in slot and slot["polygon"]:
                    pts = np.array(slot["polygon"], np.int32).reshape((-1, 1, 2))
                    cv2.polylines(output, [pts], isClosed=True, color=color, thickness=2)
                    overlay = output.copy()
                    cv2.fillPoly(overlay, [pts], color)
                    cv2.addWeighted(overlay, 0.2, output, 0.8, 0, output)
                    
                    # Label text at centroid
                    cx = int(np.mean([p[0] for p in slot["polygon"]]))
                    cy = int(np.mean([p[1] for p in slot["polygon"]]))
                    text = f"{slot_id} ({'OCCUPIED' if is_occupied else 'VACANT'})"
                    cv2.putText(output, text, (cx - 40, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                elif "bbox" in slot and slot["bbox"]:
                    x1, y1, x2, y2 = [int(v) for v in slot["bbox"]]
                    cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
                    overlay = output.copy()
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                    cv2.addWeighted(overlay, 0.15, output, 0.85, 0, output)
                    text = f"{slot_id}: {'OCCUPIED' if is_occupied else 'VACANT'}"
                    cv2.putText(output, text, (x1 + 5, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # 2. Draw Vehicles
        if vehicles:
            for v in vehicles:
                bbox = v.get("bbox", [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = [int(val) for val in bbox]
                    v_class = v.get("class_name", "vehicle")
                    conf = v.get("confidence", 0.0)
                    color = (255, 128, 0) # Cyan/Blue for vehicle bbox
                    
                    cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
                    label = f"{v_class} {conf:.2f}"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(output, (x1, y1 - 20), (x1 + tw + 6, y1), color, -1)
                    cv2.putText(output, label, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # 3. Draw Plates / ANPR
        if plates:
            for p in plates:
                bbox = p.get("bbox", [])
                text = p.get("plate_number", p.get("text", ""))
                conf = p.get("confidence", 0.0)
                if len(bbox) == 4:
                    x1, y1, x2, y2 = [int(val) for val in bbox]
                    cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    if text:
                        anpr_label = f"[{text}] ({conf:.2f})"
                        cv2.putText(output, anpr_label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        return output
