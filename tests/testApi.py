from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from helmet_workbench.api.app import createApp
from helmet_workbench.config import Settings
from helmet_workbench.domain.models import DetectionBox, DetectorObject
from helmet_workbench.services.container import AppServices


@dataclass
class FaceDetectorStub:
    def detect(self, _: object) -> list[DetectionBox]:
        return [DetectionBox(30, 20, 64, 64)]


@dataclass
class HelmetDetectorStub:
    def detect(self, _: object) -> list[DetectorObject]:
        return [DetectorObject("hat", 0.92, DetectionBox(30, 5, 70, 70))]


def buildClient(tmp_path: Path) -> TestClient:
    settings = Settings(
        storage_dir=tmp_path / "storage",
        testing=True,
    )
    return TestClient(createApp(settings))


def buildInjectedClient(tmp_path: Path) -> TestClient:
    settings = Settings(storage_dir=tmp_path / "storage", testing=True)
    services = AppServices(
        settings,
        face_detector=FaceDetectorStub(),
        helmet_detector=HelmetDetectorStub(),
    )
    return TestClient(createApp(services=services))


def testBootstrapStartsWithNoEmployees(tmp_path: Path) -> None:
    with buildClient(tmp_path) as client:
        response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["employees"] == []
    assert payload["activeModel"] is None
    assert payload["helmetModelReady"] is False


def testEmployeeCrudAndDuplicateValidation(tmp_path: Path) -> None:
    with buildClient(tmp_path) as client:
        created = client.post(
            "/api/employees",
            json={"employeeNo": "a-1001", "name": " 张三 "},
        )
        duplicate = client.post(
            "/api/employees",
            json={"employeeNo": "A-1001", "name": "李四"},
        )

    assert created.status_code == 201
    assert created.json()["employeeNo"] == "A-1001"
    assert duplicate.status_code == 409


def testEmployeeCanBeUpdated(tmp_path: Path) -> None:
    with buildClient(tmp_path) as client:
        employee = client.post(
            "/api/employees",
            json={"employeeNo": "A-1001", "name": "张三"},
        ).json()
        updated = client.patch(
            f"/api/employees/{employee['id']}",
            json={"employeeNo": "A-2001", "name": "张三丰"},
        )

    assert updated.status_code == 200
    assert updated.json()["employeeNo"] == "A-2001"
    assert updated.json()["name"] == "张三丰"


def testBootstrapAndSettingsExposeBusinessRules(tmp_path: Path) -> None:
    with buildClient(tmp_path) as client:
        response = client.get("/api/bootstrap")
        current = client.get("/api/settings")
        updated = client.patch(
            "/api/settings",
            json={"shiftStart": "09:00", "evidenceEnabled": False},
        )

    assert response.json()["settings"]["shiftStart"] == "08:00"
    assert current.json()["shiftStart"] == "08:00"
    assert updated.status_code == 200
    assert updated.json()["shiftStart"] == "09:00"


def testSampleUploadAppearsInBootstrapAndCanBeDeleted(
    tmp_path: Path,
    sample_image_bytes: bytes,
) -> None:
    with buildInjectedClient(tmp_path) as client:
        employee = client.post(
            "/api/employees",
            json={"employeeNo": "A-1001", "name": "张三"},
        ).json()
        upload = client.post(
            f"/api/employees/{employee['id']}/samples",
            files={"file": ("face.jpg", sample_image_bytes, "image/jpeg")},
        )
        samples = client.get(f"/api/employees/{employee['id']}/samples").json()
        deleted = client.delete(f"/api/samples/{samples[0]['id']}")

    assert upload.status_code == 201
    assert upload.json()["saved"] == 1
    assert len(samples) == 1
    assert deleted.status_code == 200


def testCameraCollectWebSocketReturnsSavedSample(
    tmp_path: Path,
    sample_image_bytes: bytes,
) -> None:
    with buildInjectedClient(tmp_path) as client:
        employee = client.post(
            "/api/employees",
            json={"employeeNo": "A-1001", "name": "张三"},
        ).json()
        with client.websocket_connect(
            f"/api/ws/camera?mode=collect&employee_id={employee['id']}"
        ) as websocket:
            session = websocket.receive_json()
            websocket.send_bytes(sample_image_bytes)
            response = websocket.receive_json()

    assert session["type"] == "session"
    assert response["type"] == "collection"
    assert response["saved"] == 1


def testPhotoAnalysisJobProducesOutput(
    tmp_path: Path,
    sample_image_bytes: bytes,
) -> None:
    with buildInjectedClient(tmp_path) as client:
        response = client.post(
            "/api/jobs/analyze",
            data={"source": "photo"},
            files={"files": ("scene.jpg", sample_image_bytes, "image/jpeg")},
        )
        job_id = response.json()["id"]
        job = client.get(f"/api/jobs/{job_id}").json()
        for _ in range(100):
            if job["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.02)
            job = client.get(f"/api/jobs/{job_id}").json()

    assert response.status_code == 202
    assert job["status"] == "succeeded"
    assert job["result"]["outputs"][0]["detections"][0]["helmetState"] == "with_helmet"
