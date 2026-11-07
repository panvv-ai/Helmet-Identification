from __future__ import annotations

import numpy as np
import pytest

from helmet_workbench.domain.models import DetectionBox, InvalidImage
from helmet_workbench.vision.imaging import (
    cropImage,
    decodeImageBytes,
    encodeJpeg,
    faceInput,
    resizeLongEdge,
)


def testDecodeImageBytesReturnsBgrImage(sample_image_bytes: bytes) -> None:
    image = decodeImageBytes(sample_image_bytes)

    assert image.shape == (240, 320, 3)
    assert image.dtype == np.uint8


def testDecodeImageBytesRejectsCorruptContent() -> None:
    with pytest.raises(InvalidImage):
        decodeImageBytes(b"not an image")


def testFaceInputIsGrayAndNormalized(sample_image: np.ndarray) -> None:
    result = faceInput(sample_image, 128)

    assert result.shape == (1, 128, 128, 1)
    assert result.dtype == np.float32
    assert 0.0 <= float(result.min()) <= float(result.max()) <= 1.0


def testCropImageClipsBoxesAtImageEdges(sample_image: np.ndarray) -> None:
    crop = cropImage(sample_image, DetectionBox(-20, -10, 100, 100))

    assert crop.shape[0] > 0
    assert crop.shape[1] > 0


def testResizeLongEdgePreservesAspectRatio(sample_image: np.ndarray) -> None:
    result = resizeLongEdge(sample_image, 160)

    assert max(result.shape[:2]) == 160
    assert result.shape[0] == 120


def testJpegEncodingRoundTrips(sample_image: np.ndarray) -> None:
    result = decodeImageBytes(encodeJpeg(sample_image))

    assert result.shape == sample_image.shape
