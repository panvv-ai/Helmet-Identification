from __future__ import annotations

import numpy as np

from helmet_workbench.ml.helmetDetector import (
    ANCHORS,
    CLASS_NAMES,
    buildTinyYoloModel,
    decodeTinyYoloOutputs,
)


def testTinyYoloModelHasTwoOutputScales() -> None:
    model = buildTinyYoloModel()

    assert len(model.outputs) == 2
    assert tuple(model.output_shape[0][1:3]) == (13, 13)
    assert tuple(model.output_shape[1][1:3]) == (26, 26)


def testDecodeDetectionReturnsKnownHelmetClass() -> None:
    high = np.zeros((1, 13, 13, 3, 7), dtype=np.float32)
    low = np.zeros((1, 26, 26, 3, 7), dtype=np.float32)
    high[0, 6, 6, 0, 2:4] = 0.0
    high[0, 6, 6, 0, 4] = 3.0
    high[0, 6, 6, 0, 6] = 4.0

    detections = decodeTinyYoloOutputs(
        [high, low],
        anchors=ANCHORS,
        class_names=CLASS_NAMES,
        image_shape=(416, 416),
        score_threshold=0.5,
        iou_threshold=0.45,
    )

    assert len(detections) == 1
    assert detections[0].label == "hat"
    assert detections[0].confidence > 0.9
