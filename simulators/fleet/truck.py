"""Truck state machine for the haul fleet simulator."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TruckState(str, Enum):
    QUEUE = "QUEUE"
    SPOT = "SPOT"
    LOAD = "LOAD"
    HAUL_FULL = "HAUL_FULL"
    QUEUE_DUMP = "QUEUE_DUMP"
    DUMP = "DUMP"
    HAUL_EMPTY = "HAUL_EMPTY"
    BREAKDOWN = "BREAKDOWN"


@dataclass
class Truck:
    truck_id: str
    empty_speed_kmh: float
    loaded_speed_kmh: float
    nominal_payload_t: float
    state: TruckState = TruckState.QUEUE
    x: float = 0.0
    y: float = 0.0
    speed_kmh: float = 0.0
    payload_t: float = 0.0
    engine_on: bool = True
    fuel_pct: float = 85.0
    location: str | None = None
    assigned_shovel: str | None = None
    assigned_dump: str | None = None
    material: str | None = None
    path: list[str] = field(default_factory=list)
    path_progress: float = 0.0
    state_until: float = 0.0  # simulation clock seconds when current timed state ends
    breakdown_until: float = 0.0

    def telemetry(self) -> dict[str, Any]:
        return {
            "truck_id": self.truck_id,
            "x": self.x,
            "y": self.y,
            "speed_kmh": self.speed_kmh,
            "payload_t": self.payload_t,
            "engine_on": self.engine_on,
            "fuel_pct": self.fuel_pct,
            "state": self.state.value,
        }

    def burn_fuel(self, dt_s: float, rate_pct_per_hour: float = 1.2) -> None:
        if self.engine_on and dt_s > 0:
            self.fuel_pct = max(0.0, self.fuel_pct - rate_pct_per_hour * (dt_s / 3600.0))
