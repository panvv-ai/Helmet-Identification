from __future__ import annotations

import cv2
import numpy as np

from helmet_workbench.domain.models import DetectionBox


class HaarFaceDetector:
    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_alt.xml"  # type: ignore[attr-defined]
        self.cascade = cv2.CascadeClassifier(cascade_path)
        if self.cascade.empty():
            raise RuntimeError("无法加载 OpenCV 人脸检测模型")

    def detect(self, image: np.ndarray) -> list[DetectionBox]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        gray = cv2.equalizeHist(gray)
        faces = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(30, 30),
        )
        return [
            DetectionBox(int(x), int(y), int(width), int(height))
            for x, y, width, height in sorted(
                faces,
                key=lambda item: int(item[2]) * int(item[3]),
                reverse=True,
            )
        ]
