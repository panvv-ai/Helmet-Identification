# Helmet Detector Model Card

## Model

- Name: `helmetDetectorV1`
- Architecture: YOLOv3-tiny, two prediction scales
- Runtime format: Keras 3 `.keras`
- Input: RGB, 416×416, normalized to `[0, 1]`
- Classes: `person` = no helmet; `hat` = helmet worn
- Anchors: the nine anchors shipped by the original repository
- Score threshold: `0.50`
- NMS IoU threshold: `0.45`

## Provenance

The model weights originate from the repository history file:

```text
DemoThree/logs/yolov3_tiny/ep050-loss21.904-val_loss21.313.h5
```

They were loaded into a TensorFlow 2.21 / Keras 3 reconstruction of the original Tiny YOLO network. The converted artifact is distributed in the GitHub Release `models-v1`.

Converted artifact:

```text
size:   34,870,792 bytes
sha256: 0c61f70f9298f4b01eb1b020dadc86a2356c272e594137c99c4649206fdfbdae
```

## Validation

- All convolutional and batch-normalization weights load without shape mismatch.
- Real frames from the legacy demonstration video produce expected `hat` and `person` detections.
- Unit tests verify output scale shape, confidence decoding and non-maximum suppression behavior.

## Intended Use

Local demonstration and operator assistance for detecting whether visible workers wear safety helmets. It does not make autonomous safety, employment or disciplinary decisions.

## Limitations

- The legacy model was trained outside this repository; no reproducible dataset, training split or original evaluation report is available.
- Performance on small, distant, occluded, low-light or unusual camera angles may be limited.
- The `person` class represents a worker without a helmet in the legacy data convention; production users should validate this interpretation against their own data.
- The model is not a liveness detector and does not verify identity documents.

## Identity Model

Employee identity models are trained locally from user-collected samples. They use a 128×128 grayscale CNN, fixed random seed, stratified validation, default threshold `0.70`, at most eight epochs and early stopping. Each model stores its label order, metrics and metadata.
