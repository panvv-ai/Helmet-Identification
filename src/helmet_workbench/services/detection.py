from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from helmet_workbench.db.models import AttendanceRecord, ViolationRecord
from helmet_workbench.domain.models import (
    DetectionBox,
    DetectorObject,
    FacePrediction,
    HelmetState,
    PersonObservation,
    associateFaceHelmet,
)


def _parseShift(value: str) -> tuple[int, int]:
    hour, minute = value.split(":", maxsplit=1)
    return int(hour), int(minute)


def recordBusinessObservations(
    session: Session,
    observations: list[PersonObservation],
    *,
    now: datetime,
    session_id: str | None,
    evidence_path: str | None,
    shift_start: str = "08:00",
) -> list[str]:
    actions: list[str] = []
    seen: set[tuple[str, str]] = set()
    hour, minute = _parseShift(shift_start)
    for observation in observations:
        if observation.employee_id is None or observation.employee_no is None:
            continue
        if observation.helmet_state is HelmetState.WITH_HELMET:
            action = "attendance"
            key = (action, observation.employee_id)
            if key in seen:
                continue
            exists = session.scalar(
                select(AttendanceRecord.id).where(
                    AttendanceRecord.employee_id == observation.employee_id,
                    AttendanceRecord.business_date == now.date(),
                )
            )
            if exists is None:
                session.add(
                    AttendanceRecord(
                        employee_id=observation.employee_id,
                        employee_no=observation.employee_no,
                        employee_name=observation.employee_name or observation.identity_label,
                        business_date=now.date(),
                        occurred_at=now,
                        late=(now.hour, now.minute) > (hour, minute),
                        session_id=session_id,
                        evidence_path=evidence_path,
                    )
                )
                actions.append(action)
            seen.add(key)
        elif observation.helmet_state is HelmetState.WITHOUT_HELMET:
            action = "violation"
            key = (action, observation.employee_id)
            if key in seen:
                continue
            exists = session.scalar(
                select(ViolationRecord.id).where(
                    ViolationRecord.employee_id == observation.employee_id,
                    ViolationRecord.business_date == now.date(),
                )
            )
            if exists is None:
                session.add(
                    ViolationRecord(
                        employee_id=observation.employee_id,
                        employee_no=observation.employee_no,
                        employee_name=observation.employee_name or observation.identity_label,
                        business_date=now.date(),
                        occurred_at=now,
                        session_id=session_id,
                        evidence_path=evidence_path,
                    )
                )
                actions.append(action)
            seen.add(key)
    session.flush()
    return actions


def buildObservations(
    *,
    faces: list[DetectionBox],
    detections: list[DetectorObject],
    predictFace: Callable[[DetectionBox], FacePrediction] | None,
) -> list[PersonObservation]:
    helmets = [item.box for item in detections if item.label == "hat"]
    no_helmet_people = [item.box for item in detections if item.label == "person"]
    observations: list[PersonObservation] = []
    for face in faces:
        state, confidence = associateFaceHelmet(face, helmets, no_helmet_people)
        person_box = face
        if state is HelmetState.WITHOUT_HELMET and no_helmet_people:
            person_box = max(
                no_helmet_people,
                key=lambda box: _overlap(face, box),
            )
        elif state is HelmetState.WITH_HELMET and helmets:
            person_box = max(helmets, key=lambda box: _overlap(face, box))
        prediction = predictFace(face) if predictFace is not None else None
        observations.append(
            PersonObservation(
                face_box=face,
                person_box=person_box,
                helmet_state=state,
                helmet_confidence=confidence,
                identity_label=prediction.label if prediction is not None else "Unknown",
                identity_confidence=prediction.confidence if prediction is not None else 0.0,
                employee_id=prediction.employee_id if prediction is not None else None,
                employee_name=(
                    prediction.label
                    if prediction is not None and prediction.known
                    else None
                ),
            )
        )
    return observations


def _overlap(left: DetectionBox, right: DetectionBox) -> float:
    left_edge = max(left.left, right.left)
    top_edge = max(left.top, right.top)
    right_edge = min(left.right, right.right)
    bottom_edge = min(left.bottom, right.bottom)
    intersection = max(0, right_edge - left_edge) * max(0, bottom_edge - top_edge)
    union = left.area + right.area - intersection
    return intersection / union if union else 0.0
