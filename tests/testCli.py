from __future__ import annotations

from typer.testing import CliRunner

from helmet_workbench import cli


def testServePreparesRuntimeBeforeStarting(monkeypatch: object) -> None:
    calls: list[str] = []

    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli,
        "prepareRuntime",
        lambda settings: calls.append(f"prepare:{settings.port}"),
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli.uvicorn,
        "run",
        lambda app, host, port: calls.append(f"serve:{port}"),
    )

    result = CliRunner().invoke(cli.app, ["serve", "--port", "8123"])

    assert result.exit_code == 0
    assert calls == ["prepare:8123", "serve:8123"]


def testNoArgumentStartupUsesTheSamePreparationFlow(monkeypatch: object) -> None:
    calls: list[str] = []

    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli,
        "prepareRuntime",
        lambda settings: calls.append(f"prepare:{settings.port}"),
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli.uvicorn,
        "run",
        lambda app, host, port: calls.append(f"serve:{port}"),
    )

    result = CliRunner().invoke(cli.app, ["--port", "8124"])

    assert result.exit_code == 0
    assert calls == ["prepare:8124", "serve:8124"]
