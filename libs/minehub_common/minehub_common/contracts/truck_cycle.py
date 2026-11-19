from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TruckCycle(BaseModel):
    cycle_id: UUID = Field(default_factory=uuid4)
    truck_id: str
    shift_id: str
    load_start: datetime
    load_end: datetime
    dump_start: datetime
    dump_end: datetime
    source_location: str
    dest_location: str
    payload_t: float = Field(gt=0, le=400)
    queue_load_s: float = Field(ge=0)
    queue_dump_s: float = Field(ge=0)
    haul_full_s: float = Field(ge=0)
    haul_empty_s: float = Field(ge=0)
    revision: int = 0

    def to_avro(self) -> dict[str, Any]:
        return {
            "cycle_id": str(self.cycle_id),
            "truck_id": self.truck_id,
            "shift_id": self.shift_id,
            "load_start": int(self.load_start.timestamp() * 1000),
            "load_end": int(self.load_end.timestamp() * 1000),
            "dump_start": int(self.dump_start.timestamp() * 1000),
            "dump_end": int(self.dump_end.timestamp() * 1000),
            "source_location": self.source_location,
            "dest_location": self.dest_location,
            "payload_t": self.payload_t,
            "queue_load_s": self.queue_load_s,
            "queue_dump_s": self.queue_dump_s,
            "haul_full_s": self.haul_full_s,
            "haul_empty_s": self.haul_empty_s,
            "revision": self.revision,
        }
