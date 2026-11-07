from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from helmet_workbench.domain.models import (
    DetectionBox,
    DetectorObject,
    HelmetState,
    PersonObservation,
)
from helmet_workbench.services.container import AppServices
from helmet_workbench.services.detection import recordBusinessObservations


@dataclass
class FaceDetectorStub:
    boxes: list[DetectionBox]

    def detect(self, _: np.ndarray) -> list[DetectionBox]:
        return self.boxes


@dataclass
class HelmetDetectorStub:
    objects: list[DetectorObject]

    def detect(self, _: np.ndarray) -> list[DetectorObject]:
        return self.objects


def servicesFor(tmp_path: Path) -> AppServices:
    return AppServices.forTesting(
        tmp_path,
        face_detector=FaceDetectorStub([DetectionBox(40, 30, 64, 64)]),
        helmet_detector=HelmetDetectorStub([]),
    )


def image() -> np.ndarray:
    result = np.zeros((180, 220, 3), dtype=np.uint8)
    result[30:94, 40:104] = 180
    return result


def testEmployeeSampleDeduplicatesIdenticalFace(tmp_path: Path) -> None:
    services = servicesFor(tmp_path)
    employee = services.employees.create("A-1001", "张三")

    first = services.employees.collect(employee.id, image())
    second = services.employees.collect(employee.id, image())

    assert first.saved == 1
    assert second.saved == 0
    assert second.duplicates == 1
    assert len(services.employees.listSamples(employee.id)) == 1


def testDeactivatedEmployeeDisappearsFromActiveList(tmp_path: Path) -> None:
    services = servicesFor(tmp_path)
    employee = services.employees.create("A-1001", "张三")

    services.employees.deactivate(employee.id)

    assert services.employees.listActive() == []


def testBusinessRecordsAreDeduplicatedPerEmployeeAndDay(tmp_path: Path) -> None:
    services = servicesFor(tmp_path)
    employee = services.employees.create("A-1001", "张三")
    attendance = PersonObservation(
        face_box=DetectionBox(10, 10, 40, 40),
        person_box=DetectionBox(5, 5, 80, 100),
        helmet_state=HelmetState.WITH_HELMET,
        helmet_confidence=0.92,
        identity_label="张三",
        identity_confidence=0.95,
        employee_id=employee.id,
        employee_no=employee.employee_no,
        employee_name=employee.name,
    )
    violation = PersonObservation(
        face_box=DetectionBox(10, 10, 40, 40),
        person_box=DetectionBox(5, 5, 80, 100),
        helmet_state=HelmetState.WITHOUT_HELMET,
        helmet_confidence=0.93,
        identity_label="张三",
        identity_confidence=0.95,
        employee_id=employee.id,
        employee_no=employee.employee_no,
        employee_name=employee.name,
    )
    now = datetime(2026, 11, 7, 8, 20)

    with services.database.session() as session:
        actions = recordBusinessObservations(
            session,
            [attendance, violation, attendance, violation],
            now=now,
            session_id=None,
            evidence_path=None,
        )
        assert actions == ["attendance", "violation"]
        assert services.repository.countAttendance(session) == 1
        assert services.repository.countViolations(session) == 1


def testLateFlagUsesConfiguredShiftStart(tmp_path: Path) -> None:
    services = servicesFor(tmp_path)
    employee = services.employees.create("A-1001", "张三")
    observation = PersonObservation(
        face_box=DetectionBox(10, 10, 40, 40),
        person_box=DetectionBox(5, 5, 80, 100),
        helmet_state=HelmetState.WITH_HELMET,
        helmet_confidence=0.92,
        identity_label="张三",
        identity_confidence=0.95,
        employee_id=employee.id,
        employee_no=employee.employee_no,
        employee_name=employee.name,
    )

    with services.database.session() as session:
        recordBusinessObservations(
            session,
            [observation],
            now=datetime(2026, 11, 7, 9, 0),
            session_id=None,
            evidence_path=None,
            shift_start="08:30",
        )
        assert services.repository.listAttendance(session)[0].late is True
