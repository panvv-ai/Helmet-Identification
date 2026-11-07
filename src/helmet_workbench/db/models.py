from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcNow() -> datetime:
    return datetime.now(UTC)


def newId() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    employee_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcNow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcNow,
        onupdate=utcNow,
    )

    samples: Mapped[list[FaceSample]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )


class FaceSample(Base):
    __tablename__ = "face_samples"
    __table_args__ = (UniqueConstraint("sha256", name="uq_face_sample_sha256"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    relative_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcNow)

    employee: Mapped[Employee] = relationship(back_populates="samples")


class RecognitionModel(Base):
    __tablename__ = "recognition_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    name: Mapped[str] = mapped_column(String(100))
    artifact_path: Mapped[str] = mapped_column(Text)
    threshold: Mapped[float] = mapped_column(Float, default=0.7)
    input_size: Mapped[int] = mapped_column(Integer, default=128)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcNow)

    labels: Mapped[list[ModelLabel]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="ModelLabel.class_index",
    )


class ModelLabel(Base):
    __tablename__ = "model_labels"

    model_id: Mapped[str] = mapped_column(
        ForeignKey("recognition_models.id", ondelete="CASCADE"),
        primary_key=True,
    )
    class_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    employee_no: Mapped[str] = mapped_column(String(40))
    employee_name: Mapped[str] = mapped_column(String(80))

    model: Mapped[RecognitionModel] = relationship(back_populates="labels")


class TaskJob(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(240), default="")
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcNow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcNow,
        onupdate=utcNow,
    )


class CameraSession(Base):
    __tablename__ = "camera_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    mode: Mapped[str] = mapped_column(String(24))
    model_id: Mapped[str | None] = mapped_column(
        ForeignKey("recognition_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    employee_id: Mapped[str | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcNow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frames_processed: Mapped[int] = mapped_column(Integer, default=0)
    alerts: Mapped[int] = mapped_column(Integer, default=0)
    saved_samples: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("camera_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(24))
    helmet_state: Mapped[str] = mapped_column(String(30), index=True)
    employee_id: Mapped[str | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    employee_no: Mapped[str | None] = mapped_column(String(40), nullable=True)
    employee_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    identity_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    boxes: Mapped[list[dict[str, int]]] = mapped_column(JSON, default=list)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcNow)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("employee_id", "business_date", name="uq_attendance_employee_day"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    employee_no: Mapped[str] = mapped_column(String(40))
    employee_name: Mapped[str] = mapped_column(String(80))
    business_date: Mapped[date] = mapped_column(Date, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    late: Mapped[bool] = mapped_column(Boolean, default=False)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("camera_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class ViolationRecord(Base):
    __tablename__ = "violation_records"
    __table_args__ = (
        UniqueConstraint("employee_id", "business_date", name="uq_violation_employee_day"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=newId)
    employee_id: Mapped[str | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    employee_no: Mapped[str] = mapped_column(String(40))
    employee_name: Mapped[str] = mapped_column(String(80))
    business_date: Mapped[date] = mapped_column(Date, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("camera_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
