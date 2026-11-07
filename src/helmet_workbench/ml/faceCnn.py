from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from tensorflow import keras

from helmet_workbench.domain.models import DetectionBox, FacePrediction
from helmet_workbench.vision.imaging import faceInput


class InsufficientTrainingData(ValueError):
    """Raised when employee face samples cannot train a classifier."""


class PredictModel(Protocol):
    def predict(self, data: np.ndarray, verbose: int = 0) -> np.ndarray: ...


@dataclass(frozen=True, slots=True)
class TrainingOptions:
    epochs: int = 8
    batch_size: int = 16
    input_size: int = 128
    validationFraction: float = 0.2
    seed: int = 42


@dataclass(frozen=True, slots=True)
class TrainingResult:
    artifact_dir: Path
    metrics: dict[str, float]
    labels: tuple[str, ...]
    threshold: float
    input_size: int


def buildFaceCnn(num_classes: int, input_size: int) -> keras.Model:
    return keras.Sequential(
        [
            keras.layers.Input(shape=(input_size, input_size, 1)),
            keras.layers.Conv2D(32, (5, 5), padding="same", activation="relu"),
            keras.layers.MaxPooling2D(pool_size=(2, 2)),
            keras.layers.Conv2D(64, (5, 5), padding="same", activation="relu"),
            keras.layers.MaxPooling2D(pool_size=(2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(512, activation="relu"),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(num_classes, activation="softmax"),
        ],
        name="helmet_workbench_face_cnn",
    )


class FaceCnnTrainer:
    def train(
        self,
        *,
        images: np.ndarray,
        class_indices: list[int],
        labels: list[str],
        artifact_dir: Path,
        options: TrainingOptions | None = None,
        threshold: float = 0.7,
    ) -> TrainingResult:
        settings = options or TrainingOptions()
        if len(labels) < 2:
            raise InsufficientTrainingData("训练至少需要 2 名员工")
        counts = np.bincount(np.asarray(class_indices, dtype=np.int32), minlength=len(labels))
        if np.any(counts < 2):
            raise InsufficientTrainingData("每名员工至少需要 2 张可读人脸")
        if images.shape[0] != len(class_indices):
            raise ValueError("图片数量与标签数量不一致")

        keras.utils.set_random_seed(settings.seed)
        data = images.astype(np.float32) / 255.0
        if data.ndim == 3:
            data = data[:, :, :, np.newaxis]
        target = np.asarray(class_indices, dtype=np.int32)
        minimum_test_size = len(labels) / len(target)
        test_size = max(
            settings.validationFraction,
            minimum_test_size,
            math.ceil(len(labels) / len(target)),
        )
        x_train, x_test, y_train, y_test = train_test_split(
            data,
            target,
            test_size=min(test_size, 0.5),
            random_state=settings.seed,
            stratify=target,
        )
        model = buildFaceCnn(len(labels), settings.input_size)
        model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        model.fit(
            x_train,
            y_train,
            validation_data=(x_test, y_test),
            epochs=settings.epochs,
            batch_size=settings.batch_size,
            callbacks=[
                keras.callbacks.EarlyStopping(
                    monitor="val_loss",
                    patience=3,
                    restore_best_weights=True,
                )
            ],
            verbose=0,
        )
        loss, accuracy = model.evaluate(x_test, y_test, verbose=0)
        probabilities = model.predict(x_test, verbose=0)
        predicted = np.argmax(probabilities, axis=1)
        metrics = {
            "loss": float(loss),
            "accuracy": float(accuracy_score(y_test, predicted)),
            "macroF1": float(f1_score(y_test, predicted, average="macro", zero_division=0)),
        }
        artifact_dir.mkdir(parents=True, exist_ok=True)
        model.save(artifact_dir / "model.keras")
        metadata = {
            "schemaVersion": 1,
            "labels": labels,
            "threshold": threshold,
            "inputSize": settings.input_size,
            "metrics": metrics,
            "seed": settings.seed,
            "createdAt": datetime.now(UTC).isoformat(),
        }
        (artifact_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return TrainingResult(
            artifact_dir=artifact_dir,
            metrics=metrics,
            labels=tuple(labels),
            threshold=threshold,
            input_size=settings.input_size,
        )


class FaceModelBundle:
    def __init__(
        self,
        *,
        model: PredictModel,
        labels: tuple[str, ...],
        threshold: float,
        input_size: int,
    ) -> None:
        self.model = model
        self.labels = labels
        self.threshold = threshold
        self.input_size = input_size

    def predict(self, crop: np.ndarray, box: DetectionBox) -> FacePrediction:
        probabilities = np.asarray(self.model.predict(faceInput(crop, self.input_size), verbose=0))
        if probabilities.size != len(self.labels):
            return FacePrediction(box=box, label="Unknown", confidence=0.0)
        index = int(np.argmax(probabilities[0]))
        confidence = float(probabilities[0, index])
        raw_label = self.labels[index]
        employee_id, _, label = raw_label.partition("|")
        if confidence < self.threshold:
            return FacePrediction(box=box, label="Unknown", confidence=confidence)
        return FacePrediction(
            box=box,
            label=label or employee_id,
            confidence=confidence,
            employee_id=employee_id,
            known=True,
        )


def loadFaceModel(artifact_dir: Path) -> FaceModelBundle:
    metadata = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
    model = keras.models.load_model(artifact_dir / "model.keras")
    return FaceModelBundle(
        model=model,
        labels=tuple(metadata["labels"]),
        threshold=float(metadata["threshold"]),
        input_size=int(metadata["inputSize"]),
    )
