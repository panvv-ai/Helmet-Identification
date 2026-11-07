from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from helmet_workbench.ml.helmetDetector import convertLegacyHelmetModel


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the legacy YOLO weights to Keras.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("DemoThree/logs/yolov3_tiny/ep050-loss21.904-val_loss21.313.h5"),
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("storage/models/helmetDetectorV1.keras"),
    )
    arguments = parser.parse_args()
    output = convertLegacyHelmetModel(arguments.source, arguments.destination)
    print(f"model={output}")
    print(f"bytes={output.stat().st_size}")
    print(f"sha256={sha256(output)}")


if __name__ == "__main__":
    main()
