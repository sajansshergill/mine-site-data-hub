"""Pydantic models shared by API routers and services."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ShiftSummary(BaseModel):
    shift_id: str
    planned_tonnes: float
    actual_tonnes: float
    compliance_pct: float | None


class PlanVsActualRow(BaseModel):
    location: str
    material: str
    planned_tonnes: float
    actual_tonnes: float
    variance_t: float
    variance_pct: float | None


class PlanVsActual(BaseModel):
    shift_id: str
    rows: list[PlanVsActualRow]
    total_planned: float
    total_actual: float
    compliance_pct: float | None


class LiveShift(BaseModel):
    shift_id: str | None
    tonnes_total: float = 0.0
    loads: int = 0
    tonnes_by_material: dict[str, float] = Field(default_factory=dict)
    tonnes_by_location: dict[str, float] = Field(default_factory=dict)
    truck_loads: dict[str, int] = Field(default_factory=dict)
    queues: dict[str, int] = Field(default_factory=dict)


class EquipmentKpis(BaseModel):
    equipment_id: str
    shift_id: str | None = None
    availability_pct: float | None = None
    utilization_pct: float | None = None
    operating_hours: float | None = None
    downtime_hours: float | None = None
    mtbf_hours: float | None = None
    mttr_hours: float | None = None


class WorkOrderOut(BaseModel):
    wo_number: str
    equipment_id: str
    wo_type: str
    description: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    downtime_hours: float | None = None
    failure_code: str | None = None


class KpiInfo(BaseModel):
    name: str
    version: int
    owner: str
    unit: str
    description: str
    inputs: list[str]
    params: dict[str, Any] = Field(default_factory=dict)


class KpiValidateRequest(BaseModel):
    lua: str
    inputs: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    shift_id: str = "latest"


class KpiRunResult(BaseModel):
    name: str
    version: int
    shift_id: str
    value: float | None
    ok: bool
    error: str | None = None
    duration_ms: float = 0.0


class DqResult(BaseModel):
    id: int
    check_name: str
    severity: str
    passed: bool
    failing_rows: int = 0
    details: dict[str, Any] | None = None
    shift_id: str | None = None
    run_at: datetime


class QuarantineRow(BaseModel):
    id: int
    source: str
    reason: str
    payload: dict[str, Any]
    quarantined_at: datetime
    resolved: bool = False
