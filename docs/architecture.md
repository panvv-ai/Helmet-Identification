# Architecture

## Runtime Shape

Helmet Workbench is a local single-user application. FastAPI serves the API and built React assets from one process, while SQLite stores metadata and `storage/` contains media and model artifacts.

```text
Browser
  ├── REST /api/* ─────── FastAPI
  └── WebSocket ───────── FastAPI
                              │
                              ├── service layer
                              │   ├── employees / samples
                              │   ├── training / model registry
                              │   ├── camera / analysis
                              │   └── jobs / records
                              │
                              ├── SQLAlchemy + SQLite
                              └── storage/ (samples, models, evidence, outputs)
```

## Detection Pipeline

1. Resize and letterbox the image for the YOLOv3-tiny detector.
2. Detect fixed classes: `person` (no helmet) and `hat` (helmet worn).
3. Detect all visible faces with OpenCV Haar.
4. Associate each face with the nearest helmet or no-helmet person box.
5. Crop the face, convert to 128×128 grayscale, and classify identity with the active CNN.
6. Apply the identity threshold and return boxes, status, confidence and employee metadata.

## Persistence

- `employees`: active and deactivated employee profiles.
- `face_samples`: deduplicated face crops and relative file paths.
- `recognition_models` and `model_labels`: model versions, metrics and stable class order.
- `jobs`: persistent batch and training state.
- `camera_sessions` and `detection_events`: camera session metrics and detection events.
- `attendance_records` and `violation_records`: unique per employee and business date.
- `app_settings`: shift time, threshold and evidence retention.

SQLite enables WAL, foreign keys and a busy timeout. Relative paths keep runtime data portable when `storage/` is moved as a whole.

## Boundaries

- Core detection, training and persistence are injectable services and do not depend on the browser UI.
- REST and WebSocket contracts are defined by FastAPI/Pydantic models.
- Model and media files are not stored as database BLOBs.
- Long-running training and file analysis are serialized to avoid competing TensorFlow sessions.
