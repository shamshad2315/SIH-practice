# 🚗 AI Vision & Smart Parking Service

Production-ready AI/ML Microservice for **Vehicle Detection**, **Smart Parking Slot Occupancy Tracking**, and **Automatic Number Plate Recognition (ANPR)** built with **FastAPI**, **YOLO (Ultralytics)**, **EasyOCR**, and **OpenCV**.

---

## 📂 Project Architecture

```
ai-service/
│
├── detection/
│   ├── __init__.py
│   ├── vehicle_detector.py         # YOLO vehicle detection (Car, Bike, Bus, Truck)
│   └── slot_detector.py            # Parking slot occupancy (IoU & polygon overlap)
│
├── anpr/
│   ├── __init__.py
│   ├── plate_detector.py           # Number plate detection (YOLO & Contour fallback)
│   └── ocr.py                      # EasyOCR text extraction & regex standardization
│
├── preprocessing/
│   ├── __init__.py
│   └── image_processor.py          # CLAHE, thresholding, deskewing, overlays
│
├── services/
│   ├── __init__.py
│   └── inference_service.py        # End-to-end multi-stage inference pipeline
│
├── tests/
│   ├── __init__.py
│   ├── test_vehicle_detection.py   # Vehicle detection & image tests
│   ├── test_slot_detection.py      # Slot IoU & occupancy tests
│   └── test_anpr.py                # License plate & OCR regex tests
│
├── models/
│   └── .gitkeep                    # Custom YOLO weights (.pt)
│
├── main.py                         # FastAPI application & REST endpoints
├── requirements.txt                # Python libraries & dependencies
├── .env.example                    # Environment variable configuration
├── .gitignore                      # Git ignored files & models
├── Dockerfile                      # Containerized deployment
└── README.md                       # Documentation
```

---

## ⚡ Features

1. **Vehicle Detection (`detection/vehicle_detector.py`)**:
   - Detects multiple vehicle classes: `car`, `motorcycle`, `bus`, `truck`.
   - Uses pretrained Ultralytics YOLOv8 weights (auto-downloaded) or custom models.
   - Extracts bounding boxes `[x1, y1, x2, y2]`, confidence scores, and center coordinates.

2. **Smart Parking Slot Occupancy (`detection/slot_detector.py`)**:
   - Supports both rectangular bounding boxes and arbitrary polygon coordinates.
   - Calculates Intersection over Union (IoU) and Intersection over Slot Area (IoA).
   - Reports occupied/vacant status, occupancy ratio, and summary statistics (Total, Occupied, Vacant, Occupancy %).

3. **Automatic Number Plate Recognition (`anpr/`)**:
   - Number plate localization via YOLO or adaptive morphological contour fallback.
   - Character extraction using **EasyOCR** with image enhancement (CLAHE, bilateral filter, adaptive binarization).
   - Regex-based format correction and standardization (supporting Indian and international formats).

4. **Image Preprocessing & Visual Overlays (`preprocessing/image_processor.py`)**:
   - Byte decoding, Base64 conversion, safe ROI cropping.
   - High-contrast visual overlays (Green for vacant slots, Red for occupied, Cyan for vehicles, Yellow for plates).

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or 3.11
- (Optional) CUDA-enabled GPU for accelerated inference

### 2. Installation

Clone or open the repository, then create a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and adjust settings as needed:

```bash
cp .env.example .env
```

Key environment variables:
| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `DEVICE` | `cpu` | Inference device (`cpu` or `cuda`) |
| `VEHICLE_MODEL_PATH` | `yolov8n.pt` | Path to YOLO vehicle model |
| `PLATE_MODEL_PATH` | `models/plate_yolov8n.pt` | Path to YOLO license plate model |
| `VEHICLE_CONF_THRESHOLD` | `0.35` | Vehicle detection confidence threshold |
| `SLOT_OVERLAP_IOU_THRESHOLD` | `0.20` | Slot occupancy threshold |

### 4. Running the Service

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Once started, open your browser and navigate to:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📡 REST API Endpoints

### 1. `POST /api/v1/detect/vehicles`
Detects vehicles in an uploaded image.
- **Form Data**: `file` (Image)
- **Query Param**: `conf_threshold` (Optional float)

### 2. `POST /api/v1/detect/slots`
Evaluates parking slot occupancy for predefined slots.
- **Form Data**:
  - `file`: Image file
  - `slots_json`: JSON string of slot definitions:
    ```json
    [
      {"slot_id": "A1", "bbox": [100, 150, 250, 350]},
      {"slot_id": "A2", "polygon": [[260, 150], [400, 150], [400, 350], [260, 350]]}
    ]
    ```

### 3. `POST /api/v1/anpr`
Detects license plates and extracts text using EasyOCR.
- **Form Data**: `file` (Image)

### 4. `POST /api/v1/pipeline/analyze`
Executes complete pipeline: Vehicle Detection + Slot Occupancy + ANPR + Annotated Image.
- **Form Data**:
  - `file`: Image file
  - `slots_json`: (Optional) Slot definitions JSON
  - `return_annotated_image`: `true` / `false`

### 5. `POST /api/v1/pipeline/analyze-json`
Executes complete pipeline via Base64 JSON payload.
```json
{
  "image_base64": "/9j/4AAQSkZJRgABA...",
  "slots": [
    { "slot_id": "A1", "bbox": [100, 150, 250, 350] }
  ],
  "return_annotated_image": true
}
```

---

## 🧪 Running Tests

Run the test suite using `pytest`:

```bash
pytest tests/ -v
```

---

## 🐳 Docker Deployment

Build and run using Docker:

```bash
# Build the Docker image
docker build -t ai-service:latest .

# Run the container
docker run -d -p 8000:8000 --name ai-vision-service ai-service:latest
```

---

## 📌 Custom Weights
To use fine-tuned YOLO weights:
1. Place your `.pt` file inside the `models/` directory (e.g. `models/plate_yolov8n.pt` or `models/vehicle_yolov8x.pt`).
2. Update `.env` or set `VEHICLE_MODEL_PATH` / `PLATE_MODEL_PATH`.
