from __future__ import annotations

import io

import cv2
import numpy as np
import pytest


def encoded_image(
    width: int = 320,
    height: int = 240,
    color: tuple[int, int, int] = (40, 90, 180),
) -> bytes:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = color
    success, payload = cv2.imencode(".jpg", image)
    assert success
    return payload.tobytes()


@pytest.fixture
def sample_image_bytes() -> bytes:
    return encoded_image()


@pytest.fixture
def sample_image() -> np.ndarray:
    return cv2.imdecode(np.frombuffer(encoded_image(), dtype=np.uint8), cv2.IMREAD_COLOR)


@pytest.fixture
def empty_upload() -> io.BytesIO:
    return io.BytesIO()
