from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from helmet_workbench.domain.models import DetectionBox, DetectorObject
from helmet_workbench.services.camera import CameraService
from helmet_workbench.services.container import AppServices


@dataclass
class FaceDetectorStub:
    def detect(self, _: np.ndarray) -> list[DetectionBox]:
        return [DetectionBox(30, 20, 64, 64)]


@dataclass
class HelmetDetectorStub:
    def detect(self, _: np.ndarray) -> list[DetectorObject]:
        return [
            DetectorObject(
                label="hat",
                confidence=0.9,
                box=DetectionBox(30, 5, 70, 70),
            )
        ]


def image() -> np.ndarray:
    result = np.zeros((160, 220, 3), dtype=np.uint8)
    result[20:84, 30:94] = 180
    return result


def testCollectSessionPersistsSamplesAndFinishes(tmp_path: Path) -> None:
    services = AppServices.forTesting(
        tmp_path,
        face_detector=FaceDetectorStub(),
        helmet_detector=HelmetDetectorStub(),
    )
    employee = services.employees.create("A-1001", "张三")
    camera = CameraService(services)

    session = camera.start(mode="collect", employee_id=employee.id)
    response = camera.process(session.id, image(), mode="collect")
    summary = camera.finish(session.id)

    assert response["type"] == "collection"
    assert response["saved"] == 1
    assert summary["savedSamples"] == 1
    assert len(services.employees.listSamples(employee.id)) == 1
