from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class InvalidImage(ValueError):
    """Raised when an uploaded image cannot be decoded."""


class InvalidEmployeeNumber(ValueError):
    """Raised when an employee number contains unsafe characters."""


class InvalidEmployeeName(ValueError):
    """Raised when an employee name is empty or too long."""


class NoFaceDetected(ValueError):
    """Raised when an image does not contain a detectable face."""


class ModelUnavailable(RuntimeError):
    """Raised when a required model artifact is not installed."""


class SourceKind(StrEnum):
    PHOTO = "photo"
    VIDEO = "video"
    CAMERA = "camera"


class RunMode(StrEnum):
    COLLECT = "collect"
    ANALYSIS = "analysis"
    BUSINESS = "business"


class HelmetState(StrEnum):
    WITH_HELMET = "with_helmet"
    WITHOUT_HELMET = "without_helmet"
    UNKNOWN = "unknown"


class JobKind(StrEnum):
    COLLECT = "collect"
    TRAIN = "train"
    ANALYZE = "analyze"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class DetectionBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)


@dataclass(frozen=True, slots=True)
class DetectorObject:
    label: str
    confidence: float
    box: DetectionBox


@dataclass(frozen=True, slots=True)
class FacePrediction:
    box: DetectionBox
    label: str
    confidence: float
    employee_id: str | None = None
    known: bool = False


class FaceDetectorLike(Protocol):
    def detect(self, image: Any) -> list[DetectionBox]: ...


class HelmetDetectorLike(Protocol):
    def detect(self, image: Any) -> list[DetectorObject]: ...


class FacePredictorLike(Protocol):
    def predict(self, crop: Any, box: DetectionBox) -> FacePrediction: ...


@dataclass(frozen=True, slots=True)
class PersonObservation:
    face_box: DetectionBox
    person_box: DetectionBox
    helmet_state: HelmetState
    helmet_confidence: float
    identity_label: str
    identity_confidence: float
    employee_id: str | None = None
    employee_no: str | None = None
    employee_name: str | None = None


def normalizeEmployeeNumber(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    if not normalized or not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,39}", normalized):
        raise InvalidEmployeeNumber("员工编号只能包含字母、数字、点、下划线和连字符")
    return normalized


def normalizeEmployeeName(value: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).strip().split())
    if not normalized or "/" in normalized or "\\" in normalized or "\x00" in normalized:
        raise InvalidEmployeeName("员工姓名不能为空，也不能包含路径分隔符")
    if len(normalized) > 80:
        raise InvalidEmployeeName("员工姓名不能超过 80 个字符")
    return normalized


def _intersectionOverFace(face: DetectionBox, target: DetectionBox) -> float:
    left = max(face.left, target.left)
    top = max(face.top, target.top)
    right = min(face.right, target.right)
    bottom = min(face.bottom, target.bottom)
    area = max(0, right - left) * max(0, bottom - top)
    return area / max(1, face.area)


def _expanded(box: DetectionBox, scale_x: float, scale_y: float, down: float = 0.0) -> DetectionBox:
    extra_width = int(box.width * scale_x)
    extra_height = int(box.height * scale_y)
    return DetectionBox(
        x=box.x - extra_width,
        y=box.y - extra_height,
        width=box.width + extra_width * 2,
        height=box.height + extra_height + int(box.height * down),
    )


def _associationScore(face: DetectionBox, target: DetectionBox) -> float:
    containment = _intersectionOverFace(face, target)
    fx, fy = face.center
    tx, ty = target.center
    scale = max(target.width, target.height, face.width, face.height, 1)
    distance = math.hypot(fx - tx, fy - ty) / scale
    proximity = max(0.0, 1.0 - min(distance, 1.0))
    return containment * 0.75 + proximity * 0.25


def associateFaceHelmet(
    face: DetectionBox,
    helmet_boxes: list[DetectionBox],
    no_helmet_person_boxes: list[DetectionBox],
) -> tuple[HelmetState, float]:
    candidates: list[tuple[float, HelmetState]] = []
    for box in helmet_boxes:
        candidates.append(
            (
                _associationScore(face, _expanded(box, 0.35, 0.65, down=0.55)),
                HelmetState.WITH_HELMET,
            )
        )
    for box in no_helmet_person_boxes:
        candidates.append(
            (
                _associationScore(face, _expanded(box, 0.05, 0.05)) + 0.05,
                HelmetState.WITHOUT_HELMET,
            )
        )
    if not candidates:
        return HelmetState.UNKNOWN, 0.0
    score, state = max(candidates, key=lambda item: item[0])
    if score < 0.35:
        return HelmetState.UNKNOWN, max(0.0, min(1.0, score))
    return state, max(0.0, min(1.0, score))
