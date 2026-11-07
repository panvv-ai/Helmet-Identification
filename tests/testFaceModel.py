from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from helmet_workbench.ml.faceCnn import (
    FaceCnnTrainer,
    InsufficientTrainingData,
    TrainingOptions,
    loadFaceModel,
)


def trainingImages() -> tuple[np.ndarray, list[int], list[str]]:
    rng = np.random.default_rng(7)
    images = rng.integers(0, 255, size=(8, 128, 128), dtype=np.uint8)
    images[4:] = 255 - images[4:]
    return images, [0, 0, 0, 0, 1, 1, 1, 1], ["A-1001|张三", "A-1002|李四"]


def testTrainingRequiresAtLeastTwoClasses(tmp_path: Path) -> None:
    trainer = FaceCnnTrainer()
    with pytest.raises(InsufficientTrainingData):
        trainer.train(
            images=np.zeros((4, 128, 128), dtype=np.uint8),
            class_indices=[0, 0, 0, 0],
            labels=["A-1001|张三"],
            artifact_dir=tmp_path,
        )


def testTrainingSavesReloadableModel(tmp_path: Path) -> None:
    images, class_indices, labels = trainingImages()
    trainer = FaceCnnTrainer()

    result = trainer.train(
        images=images,
        class_indices=class_indices,
        labels=labels,
        artifact_dir=tmp_path,
        options=TrainingOptions(epochs=1, batch_size=4, seed=9),
        threshold=0.7,
    )
    bundle = loadFaceModel(tmp_path)

    assert result.labels == tuple(labels)
    assert bundle.threshold == 0.7
    assert (tmp_path / "model.keras").is_file()
    prediction = bundle.predict(images[0], box=__import__(
        "helmet_workbench.domain.models", fromlist=["DetectionBox"]
    ).DetectionBox(0, 0, 32, 32))
    assert prediction.label in {"张三", "李四", "Unknown"}
    if prediction.known:
        assert prediction.employee_id in {"A-1001", "A-1002"}


def testThreeClassesStillReserveStratifiedValidationSamples(tmp_path: Path) -> None:
    rng = np.random.default_rng(11)
    images = rng.integers(0, 255, size=(12, 128, 128), dtype=np.uint8)
    images[4:8] = 255 - images[4:8]
    images[8:] = 96
    trainer = FaceCnnTrainer()

    result = trainer.train(
        images=images,
        class_indices=[0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
        labels=["A-1|甲", "A-2|乙", "A-3|丙"],
        artifact_dir=tmp_path,
        options=TrainingOptions(epochs=1, batch_size=3, seed=5),
    )

    assert len(result.labels) == 3
    assert (tmp_path / "model.keras").is_file()
