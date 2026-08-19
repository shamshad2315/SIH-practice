"""
FastAPI AI Service Entry Point.
Provides RESTful APIs for YOLO Vehicle Detection, Parking Slot Occupancy,
and Automatic Number Plate Recognition (ANPR).
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from preprocessing.image_processor import ImageProcessor
from services.inference_service import InferenceService

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_service")

# Global Inference Service instance
inference_service: Optional[InferenceService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown event handler.
    """
    global inference_service
    logger.info("Starting AI Service...")
    
    vehicle_model = os.getenv("VEHICLE_MODEL_PATH", "yolov8n.pt")
    plate_model = os.getenv("PLATE_MODEL_PATH", "models/plate_yolov8n.pt")
    device = os.getenv("DEVICE", "cpu")
    vehicle_conf = float(os.getenv("VEHICLE_CONF_THRESHOLD", "0.35"))
    plate_conf = float(os.getenv("PLATE_CONF_THRESHOLD", "0.30"))
    ocr_conf = float(os.getenv("OCR_CONF_THRESHOLD", "0.35"))
    slot_iou = float(os.getenv("SLOT_OVERLAP_IOU_THRESHOLD", "0.20"))

    inference_service = InferenceService(
        vehicle_model_path=vehicle_model,
        plate_model_path=plate_model,
        device=device,
        vehicle_conf=vehicle_conf,
        plate_conf=plate_conf,
        ocr_conf=ocr_conf,
        slot_iou_thresh=slot_iou
    )
    yield
    logger.info("Shutting down AI Service...")


app = FastAPI(
    title="AI Vision & ANPR Service",
    description="Microservice for YOLO-based Vehicle Detection, Smart Parking Slot Occupancy, and License Plate Recognition (ANPR).",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Request/Response Models ---

class SlotDefinition(BaseModel):
    slot_id: str = Field(..., description="Unique identifier for the parking slot, e.g. 'A-101'")
    slot_type: Optional[str] = Field("standard", description="Slot type: standard, handicapped, ev, etc.")
    bbox: Optional[List[int]] = Field(None, description="Bounding box [x1, y1, x2, y2]")
    polygon: Optional[List[List[int]]] = Field(None, description="Polygon points [[x1, y1], [x2, y2], ...]")


class Base64InferenceRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded JPEG/PNG image")
    slots: Optional[List[SlotDefinition]] = Field(None, description="Optional parking slot coordinates")
    return_annotated_image: Optional[bool] = Field(True, description="Whether to return base64 annotated image")
    conf_threshold: Optional[float] = Field(None, description="Custom vehicle confidence threshold")


# --- API Endpoints ---

@app.get("/", tags=["System"])
async def root():
    """
    Service root endpoint.
    """
    return {
        "service": "AI Vision & ANPR Microservice",
        "status": "online",
        "docs_url": "/docs",
        "health_check": "/health"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for container orchestrators.
    """
    return {
        "status": "healthy",
        "service_ready": inference_service is not None
    }


@app.get("/info", tags=["System"])
async def service_info():
    """
    Returns environment and model information.
    """
    return {
        "device": os.getenv("DEVICE", "cpu"),
        "vehicle_model": os.getenv("VEHICLE_MODEL_PATH", "yolov8n.pt"),
        "plate_model": os.getenv("PLATE_MODEL_PATH", "models/plate_yolov8n.pt"),
        "default_vehicle_conf": float(os.getenv("VEHICLE_CONF_THRESHOLD", "0.35")),
        "default_slot_iou": float(os.getenv("SLOT_OVERLAP_IOU_THRESHOLD", "0.20"))
    }


@app.post("/api/v1/detect/vehicles", tags=["Detection"])
async def detect_vehicles(
    file: UploadFile = File(..., description="Image file (JPG/PNG)"),
    conf_threshold: Optional[float] = Query(None, description="Confidence threshold (0.0 - 1.0)")
):
    """
    Detect vehicles (cars, motorcycles, buses, trucks) in the uploaded image.
    """
    if inference_service is None:
        raise HTTPException(status_code=503, detail="Inference service not initialized.")

    try:
        contents = await file.read()
        image = ImageProcessor.decode_image(contents)
        result = inference_service.run_vehicle_detection(image, conf_threshold=conf_threshold)
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        logger.error(f"Vehicle detection error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/detect/slots", tags=["Detection"])
async def detect_slot_occupancy(
    file: UploadFile = File(..., description="Image file (JPG/PNG)"),
    slots_json: str = Form(..., description="JSON string array of slot definitions, e.g. [{'slot_id':'A1','bbox':[100,100,300,400]}]"),
    iou_threshold: Optional[float] = Form(None, description="Overlap IoU threshold for occupancy")
):
    """
    Detect parking slot occupancy for predefined slots in the uploaded image.
    """
    if inference_service is None:
        raise HTTPException(status_code=503, detail="Inference service not initialized.")

    try:
        slots_data = json.loads(slots_json)
        contents = await file.read()
        image = ImageProcessor.decode_image(contents)

        result = inference_service.run_slot_analysis(
            image=image,
            slots=slots_data,
            iou_threshold=iou_threshold
        )
        return JSONResponse(content={"status": "success", **result})
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for 'slots_json'.")
    except Exception as e:
        logger.error(f"Slot occupancy error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/anpr", tags=["ANPR"])
async def recognize_license_plate(
    file: UploadFile = File(..., description="Image file containing vehicle/license plate"),
    conf_threshold: Optional[float] = Query(None, description="Detection confidence threshold")
):
    """
    Detect license plates and perform OCR text extraction.
    """
    if inference_service is None:
        raise HTTPException(status_code=503, detail="Inference service not initialized.")

    try:
        contents = await file.read()
        image = ImageProcessor.decode_image(contents)
        result = inference_service.run_anpr(image, conf_threshold=conf_threshold)
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        logger.error(f"ANPR error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/pipeline/analyze", tags=["Pipeline"])
async def run_full_pipeline_upload(
    file: UploadFile = File(..., description="Image file (JPG/PNG)"),
    slots_json: Optional[str] = Form(None, description="Optional JSON string array of slot definitions"),
    return_annotated_image: bool = Form(True, description="Return base64 annotated image overlay")
):
    """
    Execute complete AI pipeline via Multipart File Upload:
    Vehicle Detection + Parking Slot Occupancy + ANPR + Annotated Image.
    """
    if inference_service is None:
        raise HTTPException(status_code=503, detail="Inference service not initialized.")

    try:
        slots_data = json.loads(slots_json) if slots_json else None
        contents = await file.read()
        image = ImageProcessor.decode_image(contents)

        result = inference_service.run_full_pipeline(
            image=image,
            slots=slots_data,
            return_annotated_image=return_annotated_image
        )
        return JSONResponse(content=result)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for 'slots_json'.")
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/pipeline/analyze-json", tags=["Pipeline"])
async def run_full_pipeline_json(request: Base64InferenceRequest):
    """
    Execute complete AI pipeline via Base64 JSON Payload.
    """
    if inference_service is None:
        raise HTTPException(status_code=503, detail="Inference service not initialized.")

    try:
        image = ImageProcessor.from_base64(request.image_base64)
        slots_data = [s.model_dump() for s in request.slots] if request.slots else None

        result = inference_service.run_full_pipeline(
            image=image,
            slots=slots_data,
            return_annotated_image=request.return_annotated_image or False
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Base64 pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting Uvicorn server on http://{host}:{port}...")
    uvicorn.run("main:app", host=host, port=port, reload=debug)
