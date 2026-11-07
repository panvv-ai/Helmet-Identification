from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    id: str
    filename: str
    url: str
    sha256: str
    bytes: int
    classes: tuple[str, ...]
    input_size: int


def loadManifest() -> tuple[ModelArtifact, ...]:
    path = Path(__file__).resolve().parents[1] / "resources" / "modelManifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        ModelArtifact(
            id=item["id"],
            filename=item["filename"],
            url=item["url"],
            sha256=item["sha256"],
            bytes=int(item["bytes"]),
            classes=tuple(item["classes"]),
            input_size=int(item["inputSize"]),
        )
        for item in payload["models"]
    )


def sha256File(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def installModel(
    artifact: ModelArtifact,
    destination: Path,
    *,
    opener: object = urllib.request.urlopen,
) -> Path:
    if destination.is_file() and sha256File(destination) == artifact.sha256:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        delete=False,
        suffix=".download",
    ) as target:
        temporary = Path(target.name)
        try:
            with opener(artifact.url, timeout=120) as response:  # type: ignore[operator]
                shutil.copyfileobj(response, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    if sha256File(temporary) != artifact.sha256:
        temporary.unlink(missing_ok=True)
        raise ValueError("模型校验失败，下载文件可能不完整")
    if temporary.stat().st_size != artifact.bytes:
        temporary.unlink(missing_ok=True)
        raise ValueError("模型大小校验失败")
    os.replace(temporary, destination)
    return destination


def ensureHelmetModel(destination: Path) -> Path:
    artifact = next(item for item in loadManifest() if item.id == "helmetDetectorV1")
    return installModel(artifact, destination)
