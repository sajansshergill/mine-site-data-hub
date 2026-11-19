from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class TruckTelemetry(BaseModel):
    ts: datetime
    truck_id: str
    x_m: float
    y_m: float
    speed_kmh: float = Field(ge=0, le=120)
    payload_t: float = Field(ge=0, le=400)
    engine_on: bool = True
    fuel_pct: float | None = Field(default=None, ge=0, le=100)
    msg_id: str = Field(default_factory=lambda: uuid4().hex)

    @field_validator("truck_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("truck_id required")
        return v

    def to_avro(self) -> dict[str, Any]:
        return {
            "ts": int(self.ts.timestamp() * 1000),
            "msg_id": self.msg_id,
            "truck_id": self.truck_id,
            "x_m": self.x_m,
            "y_m": self.y_m,
            "speed_kmh": self.speed_kmh,
            "payload_t": self.payload_t,
            "engine_on": self.engine_on,
            "fuel_pct": self.fuel_pct,
        }
