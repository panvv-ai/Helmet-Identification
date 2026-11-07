from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from helmet_workbench.db.models import (
    AttendanceRecord,
    Employee,
    RecognitionModel,
    ViolationRecord,
)


class Repository:
    def countAttendance(self, session: Session) -> int:
        return int(session.scalar(select(func.count()).select_from(AttendanceRecord)) or 0)

    def countViolations(self, session: Session) -> int:
        return int(session.scalar(select(func.count()).select_from(ViolationRecord)) or 0)

    def listEmployees(self, session: Session, *, active_only: bool = False) -> list[Employee]:
        statement = select(Employee).order_by(Employee.employee_no)
        if active_only:
            statement = statement.where(Employee.active.is_(True))
        return list(session.scalars(statement))

    def activeModel(self, session: Session) -> RecognitionModel | None:
        return session.scalar(
            select(RecognitionModel)
            .where(RecognitionModel.active.is_(True))
            .order_by(RecognitionModel.created_at.desc())
        )

    def listModels(self, session: Session) -> list[RecognitionModel]:
        return list(
            session.scalars(
                select(RecognitionModel).order_by(RecognitionModel.created_at.desc())
            )
        )

    def listAttendance(
        self,
        session: Session,
        *,
        business_date: date | None = None,
        employee_no: str | None = None,
    ) -> list[AttendanceRecord]:
        statement = select(AttendanceRecord).order_by(AttendanceRecord.occurred_at.desc())
        if business_date is not None:
            statement = statement.where(AttendanceRecord.business_date == business_date)
        if employee_no:
            statement = statement.where(AttendanceRecord.employee_no == employee_no)
        return list(session.scalars(statement))

    def listViolations(
        self,
        session: Session,
        *,
        business_date: date | None = None,
        employee_no: str | None = None,
    ) -> list[ViolationRecord]:
        statement = select(ViolationRecord).order_by(ViolationRecord.occurred_at.desc())
        if business_date is not None:
            statement = statement.where(ViolationRecord.business_date == business_date)
        if employee_no:
            statement = statement.where(ViolationRecord.employee_no == employee_no)
        return list(session.scalars(statement))
