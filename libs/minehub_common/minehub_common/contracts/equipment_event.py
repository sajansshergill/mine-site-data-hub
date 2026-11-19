from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EquipmentEvent(BaseModel):
    ts: datetime
    equipment_id: str
    status: Literal["RUNNING", "STANDBY", "DELAY", "DOWN"]
    reason: str | None = None
    fault_code: str | None = None
    vendor: str
    raw_code: str

    def to_avro(self) -> dict[str, Any]:
        return {
            "ts": int(self.ts.timestamp() * 1000),
            "equipment_id": self.equipment_id,
            "status": self.status,
            "reason": self.reason,
            "fault_code": self.fault_code,
            "vendor": self.vendor,
            "raw_code": self.raw_code,
        }
