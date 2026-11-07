from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def testVisibleRootContainsOnlyStandardProjectFiles() -> None:
    visible = {
        path.name
        for path in ROOT.iterdir()
        if not path.name.startswith(".") and path.name not in {"storage", ".venv"}
    }

    assert visible == {
        "README.md",
        "LICENSE",
        "main.py",
        "pyproject.toml",
        "uv.lock",
        "config",
        "docs",
        "frontend",
        "migrations",
        "scripts",
        "src",
        "tests",
    }


def testNoLegacyDemoDirectoryRemains() -> None:
    assert not (ROOT / "DemoThree").exists()


def testPythonSourceFilenamesUseLowerCamelCase() -> None:
    python_files = [
        *ROOT.glob("src/**/*.py"),
        *ROOT.glob("tests/*.py"),
        *ROOT.glob("scripts/*.py"),
        ROOT / "main.py",
    ]
    for path in python_files:
        stem = path.stem
        if stem.startswith("__"):
            continue
        assert stem[0].islower(), path
        assert "_" not in stem, path


def testProductScreenshotIsReferencedByBothReadmes() -> None:
    image = ROOT / "docs" / "images" / "helmet-workbench.png"
    assert image.is_file()
    assert "docs/images/helmet-workbench.png" in (ROOT / "README.md").read_text(
        encoding="utf-8"
    )
    assert "images/helmet-workbench.png" in (ROOT / "docs" / "README.en.md").read_text(
        encoding="utf-8"
    )
