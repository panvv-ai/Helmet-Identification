from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import select, update

from helmet_workbench.db.database import Database
from helmet_workbench.db.models import TaskJob
from helmet_workbench.domain.models import JobStatus


class JobConflict(RuntimeError):
    """Raised when another serial batch job is already running."""


class JobContext:
    def __init__(self, database: Database, job_id: str) -> None:
        self.database = database
        self.job_id = job_id

    def update(self, progress: int, message: str) -> None:
        with self.database.session() as session:
            session.execute(
                update(TaskJob)
                .where(TaskJob.id == self.job_id)
                .values(
                    status=JobStatus.RUNNING.value,
                    progress=max(0, min(99, progress)),
                    message=message,
                )
            )


Worker = Callable[[JobContext], dict[str, Any]]


class JobManager:
    def __init__(self, database: Database) -> None:
        self.database = database
        self._lock = threading.Lock()
        self._running = False
        with database.session() as session:
            session.execute(
                update(TaskJob)
                .where(TaskJob.status == JobStatus.RUNNING.value)
                .values(
                    status=JobStatus.INTERRUPTED.value,
                    message="服务重启，任务未完成",
                    error_code="interrupted",
                    error_message="服务重启导致任务中断",
                )
            )

    def submit(self, kind: str, payload: dict[str, Any], worker: Worker) -> TaskJob:
        job = self._createQueued(kind, payload)
        thread = threading.Thread(
            target=self._execute,
            args=(job.id, worker),
            name=f"helmet-workbench-{kind}-{job.id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def get(self, job_id: str) -> TaskJob:
        with self.database.session() as session:
            job = session.get(TaskJob, job_id)
            if job is None:
                raise LookupError("任务不存在")
            session.expunge(job)
            return job

    def listRecent(self, limit: int = 20) -> list[TaskJob]:
        with self.database.session() as session:
            jobs = list(
                session.scalars(
                    select(TaskJob).order_by(TaskJob.created_at.desc()).limit(limit)
                )
            )
            for job in jobs:
                session.expunge(job)
            return jobs

    def waitFor(self, job_id: str, timeout: float = 10.0) -> TaskJob:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.get(job_id)
            if job.status in {
                JobStatus.SUCCEEDED.value,
                JobStatus.FAILED.value,
                JobStatus.INTERRUPTED.value,
            }:
                return job
            time.sleep(0.05)
        raise TimeoutError(f"任务 {job_id} 未在 {timeout} 秒内完成")

    def _createQueued(self, kind: str, payload: dict[str, Any]) -> TaskJob:
        with self._lock:
            if self._running:
                raise JobConflict("已有训练或批量分析任务正在运行")
            self._running = True
        try:
            with self.database.session() as session:
                job = TaskJob(
                    kind=kind,
                    status=JobStatus.QUEUED.value,
                    progress=0,
                    message="任务已排队",
                    payload=payload,
                )
                session.add(job)
                session.flush()
                session.expunge(job)
                return job
        except Exception:
            with self._lock:
                self._running = False
            raise

    def _execute(self, job_id: str, worker: Worker) -> None:
        context = JobContext(self.database, job_id)
        try:
            context.update(1, "任务已启动")
            result = worker(context)
            with self.database.session() as session:
                job = session.get_one(TaskJob, job_id)
                job.status = JobStatus.SUCCEEDED.value
                job.progress = 100
                job.message = "任务完成"
                job.result = result
        except Exception as exc:
            with self.database.session() as session:
                job = session.get_one(TaskJob, job_id)
                job.status = JobStatus.FAILED.value
                job.message = "任务失败"
                job.error_code = "job_failed"
                job.error_message = str(exc)
        finally:
            with self._lock:
                self._running = False
