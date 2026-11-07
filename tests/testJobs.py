from __future__ import annotations

import time
from pathlib import Path

from helmet_workbench.db.database import Database
from helmet_workbench.db.models import TaskJob
from helmet_workbench.domain.models import JobStatus
from helmet_workbench.services.jobs import JobManager


def testJobManagerPersistsSuccessfulResult(tmp_path: Path) -> None:
    database = Database.fromPath(tmp_path / "jobs.sqlite3")
    database.createAll()
    manager = JobManager(database)

    job = manager.submit("train", {"mode": "test"}, lambda context: {"saved": 2})
    finished = manager.waitFor(job.id, timeout=5)

    assert finished.status == JobStatus.SUCCEEDED.value
    assert finished.result == {"saved": 2}


def testInterruptedRunningJobsAreMarkedOnStartup(tmp_path: Path) -> None:
    database = Database.fromPath(tmp_path / "jobs.sqlite3")
    database.createAll()
    with database.session() as session:
        session.add(
            TaskJob(
                kind="train",
                status=JobStatus.RUNNING.value,
                progress=50,
                message="processing",
            )
        )

    manager = JobManager(database)
    jobs = manager.listRecent()

    assert jobs[0].status == JobStatus.INTERRUPTED.value


def testJobManagerRejectsConcurrentBatchJobs(tmp_path: Path) -> None:
    database = Database.fromPath(tmp_path / "jobs.sqlite3")
    database.createAll()
    manager = JobManager(database)

    first = manager.submit(
        "train",
        {},
        lambda context: (time.sleep(0.25), {"done": True})[1],
    )
    try:
        manager.submit("analyze", {}, lambda context: {"done": True})
    except Exception as exc:
        assert "已有" in str(exc)
    else:
        raise AssertionError("expected a conflict")
    manager.waitFor(first.id, timeout=5)
