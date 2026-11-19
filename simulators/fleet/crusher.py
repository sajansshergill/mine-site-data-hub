"""Dump point (crusher or waste dump) with a service queue."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DumpPoint:
    dump_id: str
    dump_type: str
    location: str
    dump_time_s: tuple[float, float]
    accepts: list[str]
    queue: deque[str] = field(default_factory=deque)
    serving: str | None = None
    busy_until: float = 0.0

    @property
    def queue_length(self) -> int:
        return len(self.queue) + (1 if self.serving else 0)

    def accepts_material(self, material: str) -> bool:
        return material in self.accepts

    def sample_dump_time(self, rng: random.Random) -> float:
        lo, hi = self.dump_time_s
        return float(rng.uniform(lo, hi))

    def enqueue(self, truck_id: str) -> None:
        if truck_id not in self.queue and truck_id != self.serving:
            self.queue.append(truck_id)

    def try_start_service(self, now: float, rng: random.Random) -> str | None:
        if self.serving is not None or not self.queue:
            return None
        truck_id = self.queue.popleft()
        self.serving = truck_id
        self.busy_until = now + self.sample_dump_time(rng)
        return truck_id

    def finish_if_due(self, now: float) -> str | None:
        if self.serving is None or now < self.busy_until:
            return None
        done = self.serving
        self.serving = None
        self.busy_until = 0.0
        return done

    @classmethod
    def from_cfg(cls, row: dict[str, Any]) -> DumpPoint:
        dt = row["dump_time_s"]
        return cls(
            dump_id=row["id"],
            dump_type=row.get("type", "dump"),
            location=row["location"],
            dump_time_s=(float(dt[0]), float(dt[1])),
            accepts=list(row.get("accepts", [])),
        )
