from __future__ import annotations

from pathlib import Path


class StorageLayout:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("非法资源路径")
        return candidate

    def samplePath(self, employee_id: str, sha256: str) -> Path:
        path = self.root / "samples" / employee_id / f"{sha256}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
