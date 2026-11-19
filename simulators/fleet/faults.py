"""Fault injector: breakdowns, GPS dropouts, duplicates, OOO timestamps, bad payloads."""
from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal


FaultKind = Literal["breakdown", "gps_dropout", "duplicate", "ooo", "bad_payload", "none"]


@dataclass
class FaultDecision:
    kind: FaultKind
    breakdown_s: float = 0.0
    drop_publish: bool = False
    duplicate: bool = False
    ooo_offset_s: float = 0.0
    mutate: dict[str, Any] | None = None


class FaultInjector:
    def __init__(self, fault_rate: float, rng: random.Random | None = None) -> None:
        self.fault_rate = max(0.0, min(1.0, fault_rate))
        self.rng = rng or random.Random()

    def roll(self) -> FaultDecision:
        if self.rng.random() >= self.fault_rate:
            return FaultDecision(kind="none")
        kind = self.rng.choice(["breakdown", "gps_dropout", "duplicate", "ooo", "bad_payload"])
        if kind == "breakdown":
            return FaultDecision(kind="breakdown", breakdown_s=self.rng.uniform(30.0, 180.0))
        if kind == "gps_dropout":
            return FaultDecision(kind="gps_dropout", drop_publish=True)
        if kind == "duplicate":
            return FaultDecision(kind="duplicate", duplicate=True)
        if kind == "ooo":
            return FaultDecision(kind="ooo", ooo_offset_s=-self.rng.uniform(5.0, 45.0))
        # bad_payload: impossible numbers that should fail contract validation
        mutate = self.rng.choice(
            [
                {"payloadTons": 9999.0},
                {"speedKph": -10.0},
                {"fuelLevelPct": 250.0},
                {"equipmentId": ""},
                {"lat": "NaN"},
            ]
        )
        return FaultDecision(kind="bad_payload", mutate=mutate)

    def apply_to_payload(self, payload: dict[str, Any], decision: FaultDecision, now: datetime) -> list[dict[str, Any]]:
        """Return zero or more vendor payloads to publish (may be empty for GPS dropout)."""
        if decision.drop_publish:
            return []
        msg = copy.deepcopy(payload)
        if decision.mutate:
            msg.update(decision.mutate)
        if decision.ooo_offset_s:
            ts = now + timedelta(seconds=decision.ooo_offset_s)
            msg["timestamp"] = ts.isoformat().replace("+00:00", "Z")
        out = [msg]
        if decision.duplicate:
            out.append(copy.deepcopy(msg))
        return out
