from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from helmet_workbench.api.schemas import (
    AttendanceView,
    BootstrapView,
    CollectView,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeView,
    JobView,
    ModelView,
    SampleView,
    SettingsUpdate,
    SettingsView,
    ViolationView,
)
from helmet_workbench.config import PROJECT_ROOT, Settings
from helmet_workbench.db.models import AppSetting, FaceSample, TaskJob
from helmet_workbench.domain.models import InvalidImage, NoFaceDetected, SourceKind
from helmet_workbench.services.container import AppServices
from helmet_workbench.services.employees import EmployeeConflict, EmployeeNotFound
from helmet_workbench.services.jobs import JobConflict, JobContext
from helmet_workbench.vision.imaging import decodeImageBytes


def _employeeViews(services: AppServices) -> list[EmployeeView]:
    with services.database.session() as session:
        employees = services.repository.listEmployees(session, active_only=True)
        result: list[EmployeeView] = []
        for employee in employees:
            count = len(
                session.scalars(
                    select(FaceSample).where(FaceSample.employee_id == employee.id)
                ).all()
            )
            result.append(
                EmployeeView(
                    id=employee.id,
                    employee_no=employee.employee_no,
                    name=employee.name,
                    active=employee.active,
                    sample_count=count,
                    created_at=employee.created_at,
                )
            )
        return result


def _getSetting(services: AppServices, key: str, fallback: str) -> str:
    with services.database.session() as session:
        setting = session.get(AppSetting, key)
        return setting.value if setting is not None else fallback


def _settingsView(services: AppServices) -> SettingsView:
    return SettingsView(
        shift_start=_getSetting(services, "shiftStart", services.settings.shift_start),
        evidence_enabled=_getSetting(
            services,
            "evidenceEnabled",
            "1" if services.settings.evidence_enabled else "0",
        )
        == "1",
        threshold=float(_getSetting(services, "threshold", str(services.settings.threshold))),
        camera_max_fps=services.settings.camera_max_fps,
    )


def createApp(settings: Settings | None = None, services: AppServices | None = None) -> FastAPI:
    resolved = services or AppServices(settings or Settings())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        resolved.close()

    app = FastAPI(
        title="Helmet Workbench API",
        version="0.1.0",
        description="Local safety-helmet monitoring and employee recognition API.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.services = resolved

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/bootstrap", response_model=BootstrapView)
    def bootstrap() -> BootstrapView:
        model_views: list[ModelView] = []
        active_model: ModelView | None = None
        with resolved.database.session() as session:
            models = resolved.repository.listModels(session)
            active = resolved.repository.activeModel(session)
            for model in models:
                view = ModelView(
                    id=model.id,
                    name=model.name,
                    active=model.active,
                    threshold=model.threshold,
                    metrics=model.metrics,
                    created_at=model.created_at,
                )
                model_views.append(view)
                if active is not None and active.id == model.id:
                    active_model = view
            attendance = len(
                resolved.repository.listAttendance(session, business_date=date.today())
            )
            violations = len(
                resolved.repository.listViolations(session, business_date=date.today())
            )
        return BootstrapView(
            employees=_employeeViews(resolved),
            models=model_views,
            active_model=active_model,
            helmet_model_ready=resolved.settings.helmet_model_path.is_file(),
            settings=_settingsView(resolved),
            attendance_today=attendance,
            violations_today=violations,
        )

    @app.post("/api/employees", response_model=EmployeeView, status_code=201)
    def createEmployee(payload: EmployeeCreate) -> EmployeeView:
        try:
            employee = resolved.employees.create(payload.employee_no, payload.name)
        except (ValueError, EmployeeConflict) as exc:
            status = 409 if isinstance(exc, EmployeeConflict) else 422
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return EmployeeView(
            id=employee.id,
            employee_no=employee.employee_no,
            name=employee.name,
            active=employee.active,
            sample_count=0,
            created_at=employee.created_at,
        )

    @app.get("/api/employees", response_model=list[EmployeeView])
    def employees() -> list[EmployeeView]:
        return _employeeViews(resolved)

    @app.patch("/api/employees/{employee_id}", response_model=EmployeeView)
    def updateEmployee(employee_id: str, payload: EmployeeUpdate) -> EmployeeView:
        try:
            employee = resolved.employees.update(
                employee_id,
                payload.employee_no,
                payload.name,
            )
            samples = resolved.employees.listSamples(employee.id)
        except EmployeeNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except EmployeeConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return EmployeeView(
            id=employee.id,
            employee_no=employee.employee_no,
            name=employee.name,
            active=employee.active,
            sample_count=len(samples),
            created_at=employee.created_at,
        )

    @app.delete("/api/employees/{employee_id}")
    def deactivateEmployee(employee_id: str) -> dict[str, bool]:
        try:
            resolved.employees.deactivate(employee_id)
        except EmployeeNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"deleted": True}

    @app.post(
        "/api/employees/{employee_id}/samples",
        response_model=CollectView,
        status_code=201,
    )
    async def uploadSample(employee_id: str, file: UploadFile = File(...)) -> CollectView:
        payload = await file.read()
        if len(payload) > resolved.settings.max_image_bytes:
            raise HTTPException(status_code=413, detail="图片超过大小限制")
        try:
            image = decodeImageBytes(payload)
            result = resolved.employees.collect(employee_id, image)
        except InvalidImage as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NoFaceDetected as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except EmployeeNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return CollectView(
            detected=result.detected,
            saved=result.saved,
            duplicates=result.duplicates,
        )

    @app.get(
        "/api/employees/{employee_id}/samples",
        response_model=list[SampleView],
    )
    def listSamples(employee_id: str) -> list[SampleView]:
        try:
            samples = resolved.employees.listSamples(employee_id)
        except EmployeeNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return [
            SampleView(
                id=sample.id,
                image_url=f"/api/samples/{sample.id}/image",
                created_at=sample.created_at,
            )
            for sample in samples
        ]

    @app.get("/api/samples/{sample_id}/image")
    def sampleImage(sample_id: str) -> FileResponse:
        try:
            path = resolved.employees.samplePath(sample_id)
        except EmployeeNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(
            path,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.delete("/api/samples/{sample_id}")
    def deleteSample(sample_id: str) -> dict[str, bool]:
        if not resolved.employees.deleteSample(sample_id):
            raise HTTPException(status_code=404, detail="样本人脸不存在")
        return {"deleted": True}

    @app.get("/api/models", response_model=list[ModelView])
    def models() -> list[ModelView]:
        with resolved.database.session() as session:
            return [
                ModelView(
                    id=model.id,
                    name=model.name,
                    active=model.active,
                    threshold=model.threshold,
                    metrics=model.metrics,
                    created_at=model.created_at,
                )
                for model in resolved.repository.listModels(session)
            ]

    @app.post("/api/models/{model_id}/activate", response_model=ModelView)
    def activateModel(model_id: str) -> ModelView:
        try:
            model = resolved.training.activate(model_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return ModelView(
            id=model.id,
            name=model.name,
            active=True,
            threshold=model.threshold,
            metrics=model.metrics,
            created_at=model.created_at,
        )

    @app.post("/api/jobs/train", response_model=JobView, status_code=202)
    def trainJob() -> JobView:
        def worker(context: JobContext) -> dict[str, object]:
            model = resolved.training.train(progress=context)
            return {"modelId": model.id, "metrics": model.metrics}

        try:
            job = resolved.jobs.submit("train", {}, worker)
        except JobConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _jobView(job)

    @app.post("/api/jobs/analyze", response_model=JobView, status_code=202)
    async def analyzeJob(
        source: str = Form(...),
        files: list[UploadFile] = File(...),
    ) -> JobView:
        if source not in {SourceKind.PHOTO.value, SourceKind.VIDEO.value}:
            raise HTTPException(status_code=422, detail="照片或视频分析来源无效")
        if source == SourceKind.VIDEO.value and len(files) != 1:
            raise HTTPException(status_code=422, detail="视频一次只能上传一个文件")
        payloads: list[tuple[str, bytes]] = []
        for upload in files:
            data = await upload.read()
            payloads.append((upload.filename or "upload", data))

        def worker(context: JobContext) -> dict[str, object]:
            outputs: list[dict[str, object]] = []
            if source == SourceKind.PHOTO.value:
                for index, (_, payload) in enumerate(payloads):
                    output = (
                        resolved.layout.root
                        / "outputs"
                        / context.job_id
                        / f"photo-{index + 1}.jpg"
                    )
                    result = resolved.analysis.analyzePhoto(payload, output=output)
                    outputs.append(result)
                    context.update(
                        min(95, int((index + 1) / len(payloads) * 90) + 5),
                        "正在分析照片",
                    )
            else:
                filename, payload = payloads[0]
                suffix = "".join(Path(filename).suffixes)[-12:] or ".mp4"
                upload = resolved.layout.root / "uploads" / context.job_id / f"source{suffix}"
                upload.parent.mkdir(parents=True, exist_ok=True)
                upload.write_bytes(payload)
                output = resolved.layout.root / "outputs" / context.job_id / "annotated.mp4"
                outputs.append(
                    resolved.analysis.analyzeVideo(
                        upload,
                        output=output,
                        progress=context,
                    )
                )
            return {"outputs": outputs}

        try:
            job = resolved.jobs.submit(
                "analyze",
                {"source": source, "fileCount": len(files)},
                worker,
            )
        except JobConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _jobView(job)

    @app.get("/api/jobs", response_model=list[JobView])
    def jobs() -> list[JobView]:
        return [_jobView(job) for job in resolved.jobs.listRecent()]

    @app.get("/api/jobs/{job_id}", response_model=JobView)
    def job(job_id: str) -> JobView:
        try:
            return _jobView(resolved.jobs.get(job_id))
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/records/attendance", response_model=list[AttendanceView])
    def attendanceRecords(
        day: date | None = None,
        employeeNo: str | None = None,
    ) -> list[AttendanceView]:
        with resolved.database.session() as session:
            records = resolved.repository.listAttendance(
                session,
                business_date=day,
                employee_no=employeeNo,
            )
            return [
                AttendanceView(
                    id=record.id,
                    employee_no=record.employee_no,
                    employee_name=record.employee_name,
                    date=record.business_date.isoformat(),
                    occurred_at=record.occurred_at,
                    late=record.late,
                    evidence_url=(
                        f"/api/assets/{record.evidence_path}"
                        if record.evidence_path is not None
                        else None
                    ),
                )
                for record in records
            ]

    @app.get("/api/records/violations", response_model=list[ViolationView])
    def violationRecords(
        day: date | None = None,
        employeeNo: str | None = None,
    ) -> list[ViolationView]:
        with resolved.database.session() as session:
            records = resolved.repository.listViolations(
                session,
                business_date=day,
                employee_no=employeeNo,
            )
            return [
                ViolationView(
                    id=record.id,
                    employee_no=record.employee_no,
                    employee_name=record.employee_name,
                    date=record.business_date.isoformat(),
                    occurred_at=record.occurred_at,
                    evidence_url=(
                        f"/api/assets/{record.evidence_path}"
                        if record.evidence_path is not None
                        else None
                    ),
                )
                for record in records
            ]

    @app.get("/api/records/attendance.csv")
    def attendanceCsv() -> Response:
        with resolved.database.session() as session:
            records = resolved.repository.listAttendance(session)
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(["员工编号", "姓名", "日期", "签到时间", "迟到"])
        for record in records:
            writer.writerow(
                [
                    record.employee_no,
                    record.employee_name,
                    record.business_date.isoformat(),
                    record.occurred_at.isoformat(),
                    "是" if record.late else "否",
                ]
            )
        return Response(
            stream.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="attendance.csv"'},
        )

    @app.get("/api/assets/{relative_path:path}")
    def asset(relative_path: str) -> FileResponse:
        try:
            path = resolved.layout.resolve(relative_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        allowed_roots = (
            resolved.layout.root / "evidence",
            resolved.layout.root / "outputs",
            resolved.layout.root / "uploads",
        )
        if not any(path.is_relative_to(root) for root in allowed_roots):
            raise HTTPException(status_code=404, detail="资源不存在")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="资源不存在")
        return FileResponse(path)

    @app.websocket("/api/ws/camera")
    async def cameraSocket(websocket: WebSocket) -> None:
        mode = websocket.query_params.get("mode", "analysis")
        employee_id = websocket.query_params.get("employee_id")
        try:
            camera_session = resolved.camera.start(mode=mode, employee_id=employee_id)
        except ValueError as exc:
            await websocket.close(code=1008, reason=str(exc))
            return
        await websocket.accept()
        await websocket.send_json(
            {"type": "session", "sessionId": camera_session.id, "mode": mode}
        )
        try:
            while True:
                payload = await websocket.receive_bytes()
                if len(payload) > resolved.settings.max_image_bytes:
                    await websocket.send_json(
                        {"type": "error", "message": "摄像头帧超过大小限制"}
                    )
                    continue
                try:
                    image = decodeImageBytes(payload)
                    response = resolved.camera.process(
                        camera_session.id,
                        image,
                        mode=mode,
                    )
                except (InvalidImage, NoFaceDetected, ValueError) as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                await websocket.send_json(response)
        except WebSocketDisconnect:
            pass
        finally:
            resolved.camera.finish(camera_session.id)

    @app.patch("/api/settings", response_model=SettingsView)
    def updateSettings(payload: SettingsUpdate) -> SettingsView:
        values: dict[str, str] = {}
        if payload.shift_start is not None:
            values["shiftStart"] = payload.shift_start
        if payload.evidence_enabled is not None:
            values["evidenceEnabled"] = "1" if payload.evidence_enabled else "0"
        if payload.threshold is not None:
            values["threshold"] = str(payload.threshold)
        with resolved.database.session() as session:
            for key, value in values.items():
                setting = session.get(AppSetting, key)
                if setting is None:
                    session.add(AppSetting(key=key, value=value))
                else:
                    setting.value = value
        return _settingsView(resolved)

    @app.get("/api/settings", response_model=SettingsView)
    def getSettings() -> SettingsView:
        return _settingsView(resolved)

    dist = PROJECT_ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="frontend-assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(status_code=404, detail="接口不存在")
            return FileResponse(dist / "index.html")

    return app


def _jobView(job: TaskJob) -> JobView:
    return JobView(
        id=job.id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        message=job.message,
        result=job.result,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
    )
