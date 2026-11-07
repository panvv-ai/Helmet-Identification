from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from helmet_workbench.db.models import Base


class Database:
    def __init__(self, url: str, *, engine: Engine | None = None) -> None:
        self.url = url
        self.engine = engine or create_engine(
            url,
            connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        )
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._configureSqlite)
        self._sessionFactory = sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def fromPath(cls, path: Path) -> Database:
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(f"sqlite+pysqlite:///{path}")

    @staticmethod
    def _configureSqlite(connection: object, _: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    def createAll(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._sessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        self.engine.dispose()
