from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkOrder(BaseModel):
    wo_number: str
    equipment_id: str
    wo_type: Literal["PLANNED", "UNPLANNED"]
    description: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    downtime_hours: float | None = Field(default=None, ge=0)
    failure_code: str | None = None
