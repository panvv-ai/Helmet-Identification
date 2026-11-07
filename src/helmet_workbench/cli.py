from __future__ import annotations

from pathlib import Path

import cv2
import typer
import uvicorn

from helmet_workbench.api.app import createApp
from helmet_workbench.config import Settings
from helmet_workbench.ml.faceCnn import TrainingOptions
from helmet_workbench.ml.modelInstaller import ensureHelmetModel
from helmet_workbench.services.container import AppServices
from helmet_workbench.vision.imaging import decodeImageBytes

app = typer.Typer(
    name="helmet-workbench",
    help="安全帽识别、员工人脸训练与本地监控工作台。",
    invoke_without_command=True,
)


def _services() -> AppServices:
    settings = Settings()
    settings.ensure_directories()
    return AppServices(settings)


def prepareRuntime(settings: Settings) -> Path | None:
    """Prepare local directories and fetch the detector when available."""
    settings.ensure_directories()
    try:
        model_path: Path | None = ensureHelmetModel(settings.helmet_model_path)
    except Exception as exc:
        model_path = None
        typer.echo(f"模型自动准备失败，工作台仍将启动：{exc}", err=True)
    return model_path


@app.callback()
def default(
    context: typer.Context,
    host: str = typer.Option("127.0.0.1", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
) -> None:
    if context.invoked_subcommand is None:
        serve(host=host, port=port)


@app.command()
def init() -> None:
    """创建运行目录、数据库并下载默认安全帽模型。"""
    settings = Settings()
    path = prepareRuntime(settings)
    services = AppServices(settings)
    services.close()
    typer.echo(f"初始化完成：{path or '模型未就绪'}")


@app.command()
def download_models() -> None:
    """下载或校验安全帽运行时模型。"""
    settings = Settings()
    settings.ensure_directories()
    path = ensureHelmetModel(settings.helmet_model_path)
    typer.echo(f"模型已就绪：{path}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
) -> None:
    """自动初始化本地运行环境并启动 Web 工作台。"""
    settings = Settings(host=host, port=port)
    prepareRuntime(settings)
    uvicorn.run(createApp(settings), host=host, port=port)


@app.command()
def train(
    epochs: int = typer.Option(8, min=1, max=50),
    threshold: float = typer.Option(0.7, min=0.1, max=1.0),
) -> None:
    """从当前员工人脸样本训练身份模型。"""
    services = _services()
    try:
        model = services.training.train(
            threshold=threshold,
            options=TrainingOptions(epochs=epochs),
        )
        typer.echo(f"模型已创建：{model.id} {model.metrics}")
    finally:
        services.close()


@app.command()
def detect(image: Path) -> None:
    """分析一张照片并输出检测摘要。"""
    services = _services()
    try:
        annotated, detections = services.analysis.analyzeImage(
            decodeImageBytes(image.read_bytes())
        )
        output = services.layout.root / "outputs" / f"{image.stem}-annotated.jpg"
        output.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output), annotated)
        typer.echo(f"输出：{output}")
        typer.echo(detections)
    finally:
        services.close()


@app.command("upgrade-db")
def upgrade_db() -> None:
    """将数据库升级到最新 Alembic 版本。"""
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    configuration = Config(str(root / "migrations" / "alembic.ini"))
    configuration.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(configuration, "head")


if __name__ == "__main__":
    app()
