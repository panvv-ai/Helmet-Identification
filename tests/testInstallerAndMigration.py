from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from helmet_workbench.ml.modelInstaller import loadManifest, sha256File


def testModelManifestReferencesVersionedRelease() -> None:
    artifacts = loadManifest()

    assert artifacts[0].id == "helmetDetectorV1"
    assert "/releases/download/models-v1/" in artifacts[0].url
    assert len(artifacts[0].sha256) == 64


def testSha256FileIsStable(tmp_path: Path) -> None:
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"helmet-workbench")

    assert sha256File(sample) == sha256File(sample)
    assert len(sha256File(sample)) == 64


def testAlembicUpgradesEmptyDatabase(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    database_path = tmp_path / "migrated.sqlite3"
    monkeypatch.setenv("HELMET_WORKBENCH_STORAGE_DIR", str(tmp_path))  # type: ignore[attr-defined]
    root = Path(__file__).resolve().parents[1]
    configuration = Config(str(root / "migrations" / "alembic.ini"))
    configuration.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(configuration, "head")

    # The environment may resolve an explicit URL from the host process.
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    tables = set(inspect(engine).get_table_names())
    if not tables:
        default_path = tmp_path / "helmet_workbench.sqlite3"
        engine = create_engine(f"sqlite+pysqlite:///{default_path}")
        tables = set(inspect(engine).get_table_names())
    assert {"employees", "face_samples", "jobs", "attendance_records"} <= tables
