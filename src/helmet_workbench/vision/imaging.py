from __future__ import annotations

import cv2
import numpy as np

from helmet_workbench.domain.models import DetectionBox, InvalidImage


def decodeImageBytes(payload: bytes) -> np.ndarray:
    if not payload:
        raise InvalidImage("图片内容为空")
    data = np.frombuffer(payload, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise InvalidImage("无法解码图片文件")
    return image


def encodeJpeg(image: np.ndarray, quality: int = 90) -> bytes:
    success, payload = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        raise InvalidImage("无法编码 JPEG 图片")
    return payload.tobytes()


def cropImage(image: np.ndarray, box: DetectionBox, padding: int = 0) -> np.ndarray:
    height, width = image.shape[:2]
    left = max(0, box.left - padding)
    top = max(0, box.top - padding)
    right = min(width, box.right + padding)
    bottom = min(height, box.bottom + padding)
    if right <= left or bottom <= top:
        raise InvalidImage("裁剪区域超出图片")
    return image[top:bottom, left:right].copy()


def resizeLongEdge(image: np.ndarray, edge: int) -> np.ndarray:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= edge:
        return image.copy()
    scale = edge / longest
    return cv2.resize(
        image,
        (max(1, int(width * scale)), max(1, int(height * scale))),
        interpolation=cv2.INTER_AREA,
    )


def faceInput(image: np.ndarray, size: int) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    resized = cv2.resize(gray, (size, size), interpolation=cv2.INTER_LINEAR)
    normalized = resized.astype(np.float32) / 255.0
    return normalized.reshape(1, size, size, 1)
