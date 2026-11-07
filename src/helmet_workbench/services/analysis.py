from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np

from helmet_workbench.domain.models import DetectionBox, FacePrediction, ModelUnavailable
from helmet_workbench.ml.faceCnn import FaceModelBundle
from helmet_workbench.services.detection import buildObservations
from helmet_workbench.services.jobs import JobContext
from helmet_workbench.vision.annotate import annotateObservations
from helmet_workbench.vision.imaging import cropImage

if TYPE_CHECKING:
    from helmet_workbench.services.container import AppServices


class AnalysisService:
    def __init__(self, services: AppServices) -> None:
        self.services = services

    def analyzeImage(self, image: np.ndarray) -> tuple[np.ndarray, list[dict[str, Any]]]:
        if self.services.helmet_detector is None:
            raise ModelUnavailable("安全帽模型尚未安装")
        detections = self.services.helmet_detector.detect(image)
        faces = self.services.face_detector.detect(image)
        bundle = self._bundle()

        def predict(face: DetectionBox) -> FacePrediction:
            if bundle is None:
                return FacePrediction(box=face, label="Unknown", confidence=0.0)
            return bundle.predict(cropImage(image, face, padding=4), face)

        observations = buildObservations(
            faces=faces,
            detections=detections,
            predictFace=predict,
        )
        payload = [
            {
                "box": {
                    "x": observation.face_box.x,
                    "y": observation.face_box.y,
                    "width": observation.face_box.width,
                    "height": observation.face_box.height,
                },
                "helmetState": observation.helmet_state.value,
                "helmetConfidence": round(observation.helmet_confidence, 4),
                "identity": observation.identity_label,
                "employeeNo": observation.employee_no,
                "identityConfidence": round(observation.identity_confidence, 4),
            }
            for observation in observations
        ]
        if not payload:
            payload = [
                {
                    "box": {
                        "x": detection.box.x,
                        "y": detection.box.y,
                        "width": detection.box.width,
                        "height": detection.box.height,
                    },
                    "helmetState": (
                        "with_helmet"
                        if detection.label == "hat"
                        else "without_helmet"
                    ),
                    "helmetConfidence": round(detection.confidence, 4),
                    "identity": "Unknown",
                    "employeeNo": None,
                    "identityConfidence": 0.0,
                }
                for detection in detections
            ]
        return annotateObservations(image, observations, detections), payload

    def analyzePhoto(self, payload: bytes, *, output: Path) -> dict[str, Any]:
        from helmet_workbench.vision.imaging import decodeImageBytes, encodeJpeg

        annotated, detections = self.analyzeImage(decodeImageBytes(payload))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encodeJpeg(annotated))
        return {
            "outputPath": self.services.layout.relative(output),
            "detections": detections,
        }

    def analyzeVideo(
        self,
        source: Path,
        *,
        output: Path,
        progress: JobContext | None = None,
    ) -> dict[str, Any]:
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise ValueError("无法打开视频文件")
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 25.0)
        total = max(1, int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 1))
        stride = max(1, int(round(fps / max(0.5, self.services.settings.analysis_max_fps))))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        output.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(output),
            cv2.VideoWriter_fourcc(*"mp4v"),  # type: ignore[attr-defined]
            min(fps, self.services.settings.analysis_max_fps),
            (width, height),
        )
        if not writer.isOpened():
            capture.release()
            raise ValueError("无法创建输出视频")
        frame_index = 0
        processed = 0
        all_detections: list[dict[str, Any]] = []
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % stride == 0:
                    annotated, detections = self.analyzeImage(frame)
                    writer.write(annotated)
                    processed += 1
                    for detection in detections:
                        detection["frameIndex"] = frame_index
                        all_detections.append(detection)
                    if progress is not None and processed % 5 == 0:
                        percent = min(95, max(1, int(frame_index / total * 100)))
                        progress.update(percent, f"正在分析第 {frame_index} 帧")
                frame_index += 1
        finally:
            capture.release()
            writer.release()
        return {
            "outputPath": self.services.layout.relative(output),
            "framesProcessed": processed,
            "detectionCount": len(all_detections),
            "detections": all_detections[:500],
        }

    def _bundle(self) -> FaceModelBundle | None:
        with self.services.database.session() as session:
            model = self.services.repository.activeModel(session)
            if model is None:
                return None
        return self.services.recognition.load(model)


def uniqueOutputPath(root: Path, name: str = "output") -> Path:
    return root / f"{name}-{int(time.time() * 1000)}.mp4"
