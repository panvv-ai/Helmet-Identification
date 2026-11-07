from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_file_encoding="utf-8",
        env_prefix="HELMET_WORKBENCH_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    storage_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "storage")
    database_url: str | None = None
    threshold: float = 0.7
    image_size: int = 128
    camera_frame_edge: int = 960
    camera_max_fps: int = 6
    analysis_max_fps: float = 5.0
    max_image_bytes: int = 20 * 1024 * 1024
    max_video_bytes: int = 500 * 1024 * 1024
    timezone: str = "Asia/Shanghai"
    shift_start: str = "08:00"
    evidence_enabled: bool = True
    testing: bool = False

    @property
    def resolved_database_url(self) -> str:
        default_database = self.storage_dir / "helmet_workbench.sqlite3"
        return self.database_url or f"sqlite+pysqlite:///{default_database}"

    @property
    def helmet_model_path(self) -> Path:
        return self.storage_dir / "models" / "helmetDetectorV1.keras"

    def ensure_directories(self) -> None:
        for name in ("samples", "models", "uploads", "outputs", "evidence", "temp"):
            (self.storage_dir / name).mkdir(parents=True, exist_ok=True)
