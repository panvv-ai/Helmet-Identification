from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from helmet_workbench.db.database import Database
from helmet_workbench.db.models import Employee, FaceSample
from helmet_workbench.domain.models import (
    FaceDetectorLike,
    NoFaceDetected,
    normalizeEmployeeName,
    normalizeEmployeeNumber,
)
from helmet_workbench.services.storage import StorageLayout
from helmet_workbench.vision.imaging import cropImage


class EmployeeConflict(ValueError):
    """Raised when an employee number already exists."""


class EmployeeNotFound(LookupError):
    """Raised when an employee cannot be found."""


@dataclass(frozen=True, slots=True)
class CollectResult:
    detected: int
    saved: int
    duplicates: int


@dataclass(frozen=True, slots=True)
class TrainingDataset:
    images: np.ndarray
    class_indices: list[int]
    labels: list[str]
    employee_ids: list[str]
    employee_numbers: list[str]
    employee_names: list[str]


class EmployeeService:
    def __init__(
        self,
        database: Database,
        layout: StorageLayout,
        face_detector: FaceDetectorLike,
    ) -> None:
        self.database = database
        self.layout = layout
        self.face_detector = face_detector

    def create(self, employee_no: str, name: str) -> Employee:
        normalized_no = normalizeEmployeeNumber(employee_no)
        normalized_name = normalizeEmployeeName(name)
        try:
            with self.database.session() as session:
                employee = Employee(employee_no=normalized_no, name=normalized_name)
                session.add(employee)
                session.flush()
                session.expunge(employee)
                return employee
        except IntegrityError as exc:
            raise EmployeeConflict("员工编号已存在") from exc

    def get(self, employee_id: str) -> Employee:
        with self.database.session() as session:
            employee = session.get(Employee, employee_id)
            if employee is None:
                raise EmployeeNotFound("员工不存在")
            session.expunge(employee)
            return employee

    def listActive(self) -> list[Employee]:
        with self.database.session() as session:
            employees = list(
                session.scalars(
                    select(Employee)
                    .where(Employee.active.is_(True))
                    .order_by(Employee.employee_no)
                )
            )
            for employee in employees:
                session.expunge(employee)
            return employees

    def listSamples(self, employee_id: str) -> list[FaceSample]:
        with self.database.session() as session:
            samples = list(
                session.scalars(
                    select(FaceSample)
                    .where(FaceSample.employee_id == employee_id)
                    .order_by(FaceSample.created_at.desc())
                )
            )
            for sample in samples:
                session.expunge(sample)
            return samples

    def update(self, employee_id: str, employee_no: str, name: str) -> Employee:
        normalized_no = normalizeEmployeeNumber(employee_no)
        normalized_name = normalizeEmployeeName(name)
        try:
            with self.database.session() as session:
                employee = session.get(Employee, employee_id)
                if employee is None:
                    raise EmployeeNotFound("员工不存在")
                if not employee.active:
                    raise EmployeeNotFound("员工已停用")
                employee.employee_no = normalized_no
                employee.name = normalized_name
                session.flush()
                session.expunge(employee)
                return employee
        except IntegrityError as exc:
            raise EmployeeConflict("员工编号已存在") from exc

    def collect(self, employee_id: str, image: np.ndarray) -> CollectResult:
        self.get(employee_id)
        faces = self.face_detector.detect(image)
        if not faces:
            raise NoFaceDetected("未检测到人脸")
        largest = max(faces, key=lambda box: box.area)
        crop = cropImage(image, largest, padding=8)
        success, payload = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 94])
        if not success:
            raise ValueError("无法编码人脸样本")
        digest = hashlib.sha256(payload.tobytes()).hexdigest()
        path = self.layout.samplePath(employee_id, digest)
        try:
            with self.database.session() as session:
                sample = FaceSample(
                    employee_id=employee_id,
                    relative_path=self.layout.relative(path),
                    sha256=digest,
                )
                session.add(sample)
                session.flush()
        except IntegrityError:
            return CollectResult(detected=len(faces), saved=0, duplicates=1)
        path.write_bytes(payload.tobytes())
        return CollectResult(detected=len(faces), saved=1, duplicates=0)

    def deleteSample(self, sample_id: str) -> bool:
        with self.database.session() as session:
            sample = session.get(FaceSample, sample_id)
            if sample is None:
                return False
            path = self.layout.resolve(sample.relative_path)
            session.delete(sample)
            session.flush()
        path.unlink(missing_ok=True)
        return True

    def samplePath(self, sample_id: str) -> Path:
        with self.database.session() as session:
            sample = session.get(FaceSample, sample_id)
            if sample is None:
                raise EmployeeNotFound("样本人脸不存在")
            return self.layout.resolve(sample.relative_path)

    def deactivate(self, employee_id: str) -> None:
        with self.database.session() as session:
            employee = session.get(Employee, employee_id)
            if employee is None:
                raise EmployeeNotFound("员工不存在")
            employee.active = False
            for sample in list(employee.samples):
                path = self.layout.resolve(sample.relative_path)
                path.unlink(missing_ok=True)
                session.delete(sample)

    def trainingDataset(self) -> TrainingDataset:
        employees = self.listActive()
        images: list[np.ndarray] = []
        class_indices: list[int] = []
        labels: list[str] = []
        employee_ids: list[str] = []
        employee_numbers: list[str] = []
        employee_names: list[str] = []
        for employee in employees:
            samples = self.listSamples(employee.id)
            if not samples:
                continue
            labels.append(f"{employee.id}|{employee.name}")
            employee_ids.append(employee.id)
            employee_numbers.append(employee.employee_no)
            employee_names.append(employee.name)
            class_index = len(labels) - 1
            for sample in samples:
                path = self.layout.resolve(sample.relative_path)
                image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                if image is None:
                    continue
                images.append(cv2.resize(image, (128, 128)))
                class_indices.append(class_index)
        return TrainingDataset(
            images=np.asarray(images, dtype=np.uint8),
            class_indices=class_indices,
            labels=labels,
            employee_ids=employee_ids,
            employee_numbers=employee_numbers,
            employee_names=employee_names,
        )
