from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import numpy as np
from sqlalchemy import update

from helmet_workbench.db.models import CameraSession, Employee
from helmet_workbench.domain.models import (
    DetectionBox,
    DetectorObject,
    FacePrediction,
    HelmetState,
    ModelUnavailable,
    NoFaceDetected,
    PersonObservation,
)
from helmet_workbench.ml.faceCnn import FaceModelBundle
from helmet_workbench.services.detection import (
    buildObservations,
    recordBusinessObservations,
)
from helmet_workbench.services.employees import CollectResult
from helmet_workbench.vision.annotate import annotateObservations
from helmet_workbench.vision.imaging import encodeJpeg

if TYPE_CHECKING:
    from helmet_workbench.services.container import AppServices


class CameraService:
    def __init__(self, services: AppServices) -> None:
        self.services = services

    def start(
        self,
        *,
        mode: str,
        employee_id: str | None = None,
        model_id: str | None = None,
    ) -> CameraSession:
        if mode not in {"collect", "analysis", "business"}:
            raise ValueError("未知摄像头模式")
        if mode == "collect" and not employee_id:
            raise ValueError("采集模式必须指定员工")
        with self.services.database.session() as session:
            camera_session = CameraSession(
                mode=mode,
                employee_id=employee_id,
                model_id=model_id,
            )
            session.add(camera_session)
            session.flush()
            session.expunge(camera_session)
            return camera_session

    def process(
        self,
        session_id: str,
        image: np.ndarray,
        *,
        mode: str,
        now: datetime | None = None,
    ) -> dict[str, object]:
        current = now or datetime.now(ZoneInfo(self.services.settings.timezone))
        if mode == "collect":
            result = self._collect(session_id, image)
            return {
                "type": "collection",
                "detected": result.detected,
                "saved": result.saved,
                "duplicates": result.duplicates,
                "detections": [],
            }
        if mode not in {"analysis", "business"}:
            raise ValueError("未知摄像头模式")
        if self.services.helmet_detector is None:
            raise ModelUnavailable("安全帽模型尚未安装")
        detections = self.services.helmet_detector.detect(image)
        faces = self.services.face_detector.detect(image)
        bundle = self._activeBundle()
        observations: list[PersonObservation] = []

        def predict(face: DetectionBox) -> FacePrediction:
            if bundle is None:
                return FacePrediction(box=face, label="Unknown", confidence=0.0)
            from helmet_workbench.vision.imaging import cropImage

            return bundle.predict(cropImage(image, face, padding=4), face)

        observations = buildObservations(
            faces=faces,
            detections=detections,
            predictFace=predict,
        )
        observations = self._hydrateEmployees(observations)
        actions: list[str] = []
        evidence_path: str | None = None
        if mode == "business":
            evidence_path = self._writeEvidence(
                session_id,
                image,
                observations,
                detections,
            )
            with self.services.database.session() as session:
                actions = recordBusinessObservations(
                    session,
                    observations,
                    now=current,
                    session_id=session_id,
                    evidence_path=evidence_path,
                    shift_start=self._shiftStart(),
                )
        alerts = sum(
            1
            for observation in observations
            if observation.helmet_state is HelmetState.WITHOUT_HELMET
        )
        with self.services.database.session() as session:
            session.execute(
                update(CameraSession)
                .where(CameraSession.id == session_id)
                .values(
                    frames_processed=CameraSession.frames_processed + 1,
                    alerts=CameraSession.alerts + alerts,
                )
            )
        return {
            "type": "detection",
            "mode": mode,
            "actions": actions,
            "detections": [
                {
                    "box": {
                        "x": observation.face_box.x,
                        "y": observation.face_box.y,
                        "width": observation.face_box.width,
                        "height": observation.face_box.height,
                    },
                    "helmetState": observation.helmet_state.value,
                    "helmetConfidence": round(observation.helmet_confidence, 4),
                    "identity": observation.employee_name or "Unknown",
                    "employeeNo": observation.employee_no,
                    "identityConfidence": round(observation.identity_confidence, 4),
                }
                for observation in observations
            ],
            "alertCount": alerts,
        }

    def finish(self, session_id: str) -> dict[str, object]:
        with self.services.database.session() as session:
            camera_session = session.get(CameraSession, session_id)
            if camera_session is None:
                raise LookupError("摄像头会话不存在")
            camera_session.ended_at = datetime.now(UTC)
            camera_session.summary = {
                "framesProcessed": camera_session.frames_processed,
                "alerts": camera_session.alerts,
                "savedSamples": camera_session.saved_samples,
            }
            summary = dict(camera_session.summary)
        return summary

    def _collect(self, session_id: str, image: np.ndarray) -> CollectResult:
        with self.services.database.session() as session:
            camera_session = session.get(CameraSession, session_id)
            if camera_session is None or camera_session.employee_id is None:
                raise LookupError("采集会话不存在")
            employee_id = camera_session.employee_id
        try:
            result = self.services.employees.collect(employee_id, image)
        except NoFaceDetected:
            with self.services.database.session() as session:
                session.execute(
                    update(CameraSession)
                    .where(CameraSession.id == session_id)
                    .values(frames_processed=CameraSession.frames_processed + 1)
                )
            raise
        with self.services.database.session() as session:
            session.execute(
                update(CameraSession)
                .where(CameraSession.id == session_id)
                .values(
                    frames_processed=CameraSession.frames_processed + 1,
                    saved_samples=CameraSession.saved_samples + result.saved,
                )
            )
        return result

    def _activeBundle(self) -> FaceModelBundle | None:
        with self.services.database.session() as session:
            model = self.services.repository.activeModel(session)
            if model is None:
                return None
        return self.services.recognition.load(model)

    def _hydrateEmployees(
        self,
        observations: list[PersonObservation],
    ) -> list[PersonObservation]:
        with self.services.database.session() as session:
            result: list[PersonObservation] = []
            for observation in observations:
                if observation.employee_id is None:
                    result.append(observation)
                    continue
                employee = session.get(Employee, observation.employee_id)
                if employee is None:
                    result.append(observation)
                    continue
                result.append(
                    PersonObservation(
                        face_box=observation.face_box,
                        person_box=observation.person_box,
                        helmet_state=observation.helmet_state,
                        helmet_confidence=observation.helmet_confidence,
                        identity_label=observation.identity_label,
                        identity_confidence=observation.identity_confidence,
                        employee_id=employee.id,
                        employee_no=employee.employee_no,
                        employee_name=employee.name,
                    )
                )
            return result

    def _writeEvidence(
        self,
        session_id: str,
        image: np.ndarray,
        observations: list[PersonObservation],
        detections: list[DetectorObject],
    ) -> str | None:
        if not self._evidenceEnabled():
            return None
        annotated = annotateObservations(image, observations, detections)
        filename = f"{session_id}-{int(time.time() * 1000)}.jpg"
        path = self.services.layout.root / "evidence" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encodeJpeg(annotated))
        return self.services.layout.relative(path)

    def _shiftStart(self) -> str:
        from helmet_workbench.db.models import AppSetting

        with self.services.database.session() as session:
            setting = session.get(AppSetting, "shiftStart")
            return setting.value if setting is not None else self.services.settings.shift_start

    def _evidenceEnabled(self) -> bool:
        from helmet_workbench.db.models import AppSetting

        with self.services.database.session() as session:
            setting = session.get(AppSetting, "evidenceEnabled")
            if setting is None:
                return self.services.settings.evidence_enabled
            return setting.value == "1"
