# Legacy Feature Mapping

| Legacy capability | Current implementation |
| --- | --- |
| PyQt camera attendance tab | React camera workspace + WebSocket business mode |
| PyQt live detection tab | Browser camera analysis/business modes |
| Local MP4 detection tab | Photo/video analysis jobs with annotated output |
| Attendance SQL inserts | SQLAlchemy `attendance_records` with per-day unique constraint |
| Violation SQL inserts | SQLAlchemy `violation_records` with per-day unique constraint |
| Date/employee statistical queries | REST records filters and CSV export |
| Manual model/database file replacement | Versioned identity models, activation controls and Alembic migrations |
| Haar + employee CNN recognition | Rebuilt 128×128 grayscale CNN service |
| YOLOv3-tiny helmet detection | Converted Keras 3 runtime artifact |

## Removed Legacy Assets

- PyQt generated UI code and `.ui` files.
- IDE metadata and Python bytecode caches.
- Duplicate full YOLO and Tiny YOLO implementations.
- Undocumented scratch scripts and demo dialogs.
- FaceNet and MTCNN code not used by the active recognition path.
- Old SQLite database, sample video, large local font and duplicate model files.
- Old face classifier with label output that did not match the employee database.

The original implementation remains available in Git history. Current business data starts empty; no legacy records are imported automatically.
