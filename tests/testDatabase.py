from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from helmet_workbench.db.database import Database
from helmet_workbench.db.models import (
    AttendanceRecord,
    Employee,
    FaceSample,
    ViolationRecord,
)


def testDatabaseEnablesSqliteWrites(tmp_path: Path) -> None:
    database = Database.fromPath(tmp_path / "workbench.sqlite3")
    database.createAll()

    with database.session() as session:
        employee = Employee(employee_no="A-1001", name="张三")
        session.add(employee)

    with database.session() as session:
        assert session.query(Employee).count() == 1


def testEmployeeNumberIsUnique(tmp_path: Path) -> None:
    database = Database.fromPath(tmp_path / "workbench.sqlite3")
    database.createAll()
    with database.session() as session:
        session.add(Employee(employee_no="A-1001", name="张三"))
    with pytest.raises(IntegrityError), database.session() as session:
        session.add(Employee(employee_no="A-1001", name="李四"))


def testAttendanceIsUniquePerEmployeeAndDate(tmp_path: Path) -> None:
    database = Database.fromPath(tmp_path / "workbench.sqlite3")
    database.createAll()
    with database.session() as session:
        employee = Employee(employee_no="A-1001", name="张三")
        session.add(employee)
        session.flush()
        session.add(
            AttendanceRecord(
                employee_id=employee.id,
                employee_no=employee.employee_no,
                employee_name=employee.name,
                business_date=date(2026, 11, 7),
                occurred_at=datetime(2026, 11, 7, 8, 1),
                late=False,
            )
        )
    with pytest.raises(IntegrityError), database.session() as session:
        session.add(
            AttendanceRecord(
                employee_id=1,
                employee_no="A-1001",
                employee_name="张三",
                business_date=date(2026, 11, 7),
                occurred_at=datetime(2026, 11, 7, 8, 5),
                late=False,
            )
        )


def testDeletingEmployeeClearsSamplesButKeepsAuditRows(tmp_path: Path) -> None:
    database = Database.fromPath(tmp_path / "workbench.sqlite3")
    database.createAll()
    with database.session() as session:
        employee = Employee(employee_no="A-1001", name="张三")
        session.add(employee)
        session.flush()
        session.add(
            FaceSample(
                employee_id=employee.id,
                relative_path="dataset/a.jpg",
                sha256="a" * 64,
            )
        )
        session.add(
            ViolationRecord(
                employee_id=employee.id,
                employee_no=employee.employee_no,
                employee_name=employee.name,
                business_date=date(2026, 11, 7),
                occurred_at=datetime(2026, 11, 7, 9, 0),
            )
        )
    with database.session() as session:
        employee = session.query(Employee).one()
        employee.active = False
        session.query(FaceSample).delete()
    with database.session() as session:
        assert session.query(FaceSample).count() == 0
        assert session.query(ViolationRecord).one().employee_name == "张三"
