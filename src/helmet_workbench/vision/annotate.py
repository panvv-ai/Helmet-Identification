from __future__ import annotations

import cv2
import numpy as np

from helmet_workbench.domain.models import DetectorObject, HelmetState, PersonObservation


def annotateObservations(
    image: np.ndarray,
    observations: list[PersonObservation],
    detections: list[DetectorObject] | None = None,
) -> np.ndarray:
    result = image.copy()
    for detection in detections or []:
        compliant = detection.label == "hat"
        color = (95, 220, 145) if compliant else (58, 174, 255)
        box = detection.box
        cv2.rectangle(
            result,
            (box.x, box.y),
            (box.right, box.bottom),
            color,
            2,
        )
        label = f"{'已戴帽' if compliant else '未戴帽'} {detection.confidence:.2f}"
        cv2.putText(
            result,
            label,
            (box.x, max(16, box.y - 7)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            color,
            2,
            cv2.LINE_AA,
        )
    for observation in observations:
        color = (
            (80, 220, 120)
            if observation.helmet_state is HelmetState.WITH_HELMET
            else (40, 170, 255)
            if observation.helmet_state is HelmetState.WITHOUT_HELMET
            else (190, 190, 190)
        )
        x, y = observation.face_box.x, observation.face_box.y
        width, height = observation.face_box.width, observation.face_box.height
        cv2.rectangle(result, (x, y), (x + width, y + height), color, 3)
        label = (
            observation.employee_name
            if observation.employee_name
            else "身份未识别"
        )
        status = "已戴帽" if observation.helmet_state is HelmetState.WITH_HELMET else "未戴帽"
        text = f"{label} | {status}"
        cv2.rectangle(result, (x, max(0, y - 30)), (x + max(180, len(text) * 16), y), color, -1)
        cv2.putText(
            result,
            text,
            (x + 6, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (10, 18, 28),
            2,
            cv2.LINE_AA,
        )
    return result
