"""Loading unit with uniform service-time distribution."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Shovel:
    shovel_id: str
    location: str
    load_time_s: tuple[float, float]
    material: str
    model: str = ""
    queue: deque[str] = field(default_factory=deque)
    serving: str | None = None
    busy_until: float = 0.0

    @property
    def queue_length(self) -> int:
        return len(self.queue) + (1 if self.serving else 0)

    def sample_load_time(self, rng: random.Random) -> float:
        lo, hi = self.load_time_s
        return float(rng.uniform(lo, hi))

    def enqueue(self, truck_id: str) -> None:
        if truck_id not in self.queue and truck_id != self.serving:
            self.queue.append(truck_id)

    def try_start_service(self, now: float, rng: random.Random | None = None) -> str | None:
        """If idle and queue non-empty, pull next truck into the spotter; return truck_id or None."""
        del rng  # load duration is sampled when loading actually starts
        if self.serving is not None or not self.queue:
            return None
        truck_id = self.queue.popleft()
        self.serving = truck_id
        self.busy_until = float("inf")  # set when loading begins after spot
        return truck_id

    def begin_load(self, now: float, rng: random.Random) -> float:
        """Start the load clock for the truck currently being served; return busy_until."""
        self.busy_until = now + self.sample_load_time(rng)
        return self.busy_until

    def finish_if_due(self, now: float) -> str | None:
        if self.serving is None or now < self.busy_until:
            return None
        done = self.serving
        self.serving = None
        self.busy_until = 0.0
        return done

    @classmethod
    def from_cfg(cls, row: dict[str, Any]) -> Shovel:
        lt = row["load_time_s"]
        return cls(
            shovel_id=row["id"],
            location=row["location"],
            load_time_s=(float(lt[0]), float(lt[1])),
            material=row["material"],
            model=row.get("model", ""),
        )
