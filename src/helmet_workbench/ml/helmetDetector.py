from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from tensorflow import keras

from helmet_workbench.domain.models import (
    DetectionBox,
    DetectorObject,
    InvalidImage,
    ModelUnavailable,
)

CLASS_NAMES = ("person", "hat")
ANCHORS = np.asarray(
    [
        [10, 13],
        [16, 30],
        [33, 23],
        [30, 61],
        [62, 45],
        [59, 119],
        [116, 90],
        [156, 198],
        [373, 326],
    ],
    dtype=np.float32,
)
INPUT_SIZE = 416


def _block(
    x: keras.KerasTensor,
    filters: int,
    kernel: int,
    *,
    strides: int = 1,
    conv_name: str,
    bn_name: str,
) -> keras.KerasTensor:
    x = keras.layers.Conv2D(
        filters,
        kernel,
        strides=strides,
        padding="valid" if strides == 2 else "same",
        use_bias=False,
        name=conv_name,
    )(x)
    x = keras.layers.BatchNormalization(name=bn_name)(x)
    return keras.layers.LeakyReLU(negative_slope=0.1)(x)


def buildTinyYoloModel() -> keras.Model:
    inputs = keras.Input((INPUT_SIZE, INPUT_SIZE, 3), name="input_1")
    x = _block(
        inputs,
        16,
        3,
        conv_name="conv2d_1",
        bn_name="batch_normalization_1",
    )
    x = keras.layers.MaxPooling2D(2, 2, name="max_pooling2d_1")(x)
    x = _block(x, 32, 3, conv_name="conv2d_2", bn_name="batch_normalization_2")
    x = keras.layers.MaxPooling2D(2, 2, name="max_pooling2d_2")(x)
    x = _block(x, 64, 3, conv_name="conv2d_3", bn_name="batch_normalization_3")
    x = keras.layers.MaxPooling2D(2, 2, name="max_pooling2d_3")(x)
    x = _block(x, 128, 3, conv_name="conv2d_4", bn_name="batch_normalization_4")
    x = keras.layers.MaxPooling2D(2, 2, name="max_pooling2d_4")(x)
    skip = _block(x, 256, 3, conv_name="conv2d_5", bn_name="batch_normalization_5")
    x = keras.layers.MaxPooling2D(2, 2, name="max_pooling2d_5")(skip)
    x = _block(x, 512, 3, conv_name="conv2d_6", bn_name="batch_normalization_6")
    x = keras.layers.MaxPooling2D(
        (2, 2),
        (1, 1),
        padding="same",
        name="max_pooling2d_6",
    )(x)
    x = _block(x, 1024, 3, conv_name="conv2d_7", bn_name="batch_normalization_7")
    x = _block(x, 256, 1, conv_name="conv2d_8", bn_name="batch_normalization_8")
    y1 = _block(x, 512, 3, conv_name="conv2d_9", bn_name="batch_normalization_9")
    y1 = keras.layers.Conv2D(21, 1, padding="same", name="conv2d_10")(y1)
    up = _block(x, 128, 1, conv_name="conv2d_11", bn_name="batch_normalization_10")
    up = keras.layers.UpSampling2D(2, name="up_sampling2d_1")(up)
    x = keras.layers.Concatenate(name="concatenate_1")([up, skip])
    x = _block(x, 256, 3, conv_name="conv2d_12", bn_name="batch_normalization_11")
    y2 = keras.layers.Conv2D(21, 1, padding="same", name="conv2d_13")(x)
    return keras.Model(inputs, [y1, y2], name="helmetDetectorV1")


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    if not len(boxes):
        return []
    x1, y1, x2, y2 = boxes.T
    areas = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        xx1 = np.maximum(x1[current], x1[order[1:]])
        yy1 = np.maximum(y1[current], y1[order[1:]])
        xx2 = np.minimum(x2[current], x2[order[1:]])
        yy2 = np.minimum(y2[current], y2[order[1:]])
        width = np.maximum(0.0, xx2 - xx1)
        height = np.maximum(0.0, yy2 - yy1)
        intersection = width * height
        union = areas[current] + areas[order[1:]] - intersection
        iou = np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)
        order = order[1:][iou <= iou_threshold]
    return keep


def decodeTinyYoloOutputs(
    outputs: list[np.ndarray],
    *,
    anchors: np.ndarray,
    class_names: tuple[str, ...],
    image_shape: tuple[int, int],
    score_threshold: float,
    iou_threshold: float,
) -> list[DetectorObject]:
    all_boxes: list[np.ndarray] = []
    all_scores: list[float] = []
    all_classes: list[int] = []
    anchor_masks = ((3, 4, 5), (1, 2, 3))
    input_shape = np.asarray(
        [outputs[0].shape[1] * 32, outputs[0].shape[2] * 32],
        dtype=np.float32,
    )
    image_h, image_w = image_shape
    for scale, raw in enumerate(outputs):
        grid_h, grid_w = raw.shape[1:3]
        reshaped = raw.reshape(1, grid_h, grid_w, len(anchor_masks[scale]), -1)
        grid_y, grid_x = np.indices((grid_h, grid_w), dtype=np.float32)
        grid = np.stack([grid_x, grid_y], axis=-1)[None, :, :, None, :]
        xy = np.asarray(
            _sigmoid(reshaped[..., :2]) + grid,
            dtype=np.float32,
        )
        xy = xy / np.asarray([grid_w, grid_h], dtype=np.float32)  # type: ignore[assignment]
        wh = (
            np.exp(np.clip(reshaped[..., 2:4], -8.0, 8.0))
            * anchors[list(anchor_masks[scale])]
            / input_shape[::-1]
        )
        confidence = _sigmoid(reshaped[..., 4:5])
        class_scores = _sigmoid(reshaped[..., 5:]) * confidence
        class_ids = np.argmax(class_scores, axis=-1)
        scores = np.max(class_scores, axis=-1)
        mask = scores >= score_threshold
        if not np.any(mask):
            continue
        xy = xy[mask]
        wh = wh[mask]
        mins = xy - wh / 2
        maxes = xy + wh / 2
        boxes = np.concatenate([mins, maxes], axis=-1)
        scale_x = np.min(input_shape / np.asarray([image_w, image_h]))
        new_shape = np.round(np.asarray([image_w, image_h], dtype=np.float32) * scale_x)
        offset = (input_shape - new_shape) / 2 / input_shape
        resize_scale = input_shape / new_shape
        mins = (boxes[..., :2] - offset) * resize_scale
        maxes = (boxes[..., 2:] - offset) * resize_scale
        resized = np.concatenate([mins, maxes], axis=-1) * np.asarray(
            [image_w, image_h, image_w, image_h],
            dtype=np.float32,
        )
        resized[:, [0, 2]] = np.clip(resized[:, [0, 2]], 0, image_w)
        resized[:, [1, 3]] = np.clip(resized[:, [1, 3]], 0, image_h)
        all_boxes.extend(resized)
        all_scores.extend(scores[mask].astype(float).tolist())
        all_classes.extend(class_ids[mask].astype(int).tolist())

    detections: list[DetectorObject] = []
    for class_id, class_name in enumerate(class_names):
        indices = [index for index, value in enumerate(all_classes) if value == class_id]
        if not indices:
            continue
        boxes = np.asarray([all_boxes[index] for index in indices], dtype=np.float32)
        scores = np.asarray([all_scores[index] for index in indices], dtype=np.float32)
        keep = _nms(boxes, scores, iou_threshold)
        for index in keep:
            x1, y1, x2, y2 = boxes[index]
            detections.append(
                DetectorObject(
                    label=class_name,
                    confidence=float(scores[index]),
                    box=DetectionBox(
                        int(x1),
                        int(y1),
                        max(1, int(x2 - x1)),
                        max(1, int(y2 - y1)),
                    ),
                )
            )
    return sorted(detections, key=lambda item: item.confidence, reverse=True)


class HelmetDetector:
    def __init__(
        self,
        model_path: Path,
        *,
        score_threshold: float = 0.5,
        iou_threshold: float = 0.45,
    ) -> None:
        if not model_path.is_file():
            raise ModelUnavailable("安全帽模型尚未安装")
        self.model_path = model_path
        self.score_threshold = score_threshold
        self.iou_threshold = iou_threshold
        try:
            self.model = keras.models.load_model(model_path, compile=False)
        except Exception as exc:
            raise ModelUnavailable(f"安全帽模型加载失败：{exc}") from exc

    def detect(self, image: np.ndarray) -> list[DetectorObject]:
        if image.ndim != 3 or image.shape[2] != 3:
            raise InvalidImage("安全帽检测要求三通道彩色图片")
        height, width = image.shape[:2]
        ratio = min(INPUT_SIZE / width, INPUT_SIZE / height)
        new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
        resized = cv2.resize(image, new_size, interpolation=cv2.INTER_LINEAR)
        canvas = np.full((INPUT_SIZE, INPUT_SIZE, 3), 128, dtype=np.uint8)
        offset_x = (INPUT_SIZE - new_size[0]) // 2
        offset_y = (INPUT_SIZE - new_size[1]) // 2
        canvas[offset_y : offset_y + new_size[1], offset_x : offset_x + new_size[0]] = resized
        batch = canvas[:, :, ::-1].astype(np.float32) / 255.0
        outputs = [np.asarray(item) for item in self.model.predict(batch[None], verbose=0)]
        return decodeTinyYoloOutputs(
            outputs,
            anchors=ANCHORS,
            class_names=CLASS_NAMES,
            image_shape=(height, width),
            score_threshold=self.score_threshold,
            iou_threshold=self.iou_threshold,
        )


def convertLegacyHelmetModel(source: Path, destination: Path) -> Path:
    model = buildTinyYoloModel()
    model.load_weights(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    model.save(destination)
    return destination
