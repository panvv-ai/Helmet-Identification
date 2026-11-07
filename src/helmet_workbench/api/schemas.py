from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def toCamel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=toCamel, populate_by_name=True)


class EmployeeCreate(ApiModel):
    employee_no: str
    name: str


class EmployeeUpdate(ApiModel):
    employee_no: str
    name: str


class EmployeeView(ApiModel):
    id: str
    employee_no: str
    name: str
    active: bool
    sample_count: int = 0
    created_at: datetime


class SettingsView(ApiModel):
    shift_start: str
    evidence_enabled: bool
    threshold: float
    camera_max_fps: int


class SettingsUpdate(ApiModel):
    shift_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    evidence_enabled: bool | None = None
    threshold: float | None = Field(default=None, gt=0, le=1)

    @field_validator("shift_start")
    @classmethod
    def validateShiftStart(cls, value: str | None) -> str | None:
        if value is None:
            return value
        hour, minute = (int(part) for part in value.split(":"))
        if hour > 23 or minute > 59:
            raise ValueError("班次时间必须是有效的 24 小时时间")
        return value


class ModelView(ApiModel):
    id: str
    name: str
    active: bool
    threshold: float
    metrics: dict[str, float]
    created_at: datetime


class SampleView(ApiModel):
    id: str
    image_url: str
    created_at: datetime


class CollectView(ApiModel):
    detected: int
    saved: int
    duplicates: int


class JobView(ApiModel):
    id: str
    kind: str
    status: str
    progress: int
    message: str
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime


class AttendanceView(ApiModel):
    id: str
    employee_no: str
    employee_name: str
    date: str
    occurred_at: datetime
    late: bool
    evidence_url: str | None


class ViolationView(ApiModel):
    id: str
    employee_no: str
    employee_name: str
    date: str
    occurred_at: datetime
    evidence_url: str | None


class BootstrapView(ApiModel):
    employees: list[EmployeeView]
    models: list[ModelView]
    active_model: ModelView | None
    helmet_model_ready: bool
    settings: SettingsView
    attendance_today: int
    violations_today: int
