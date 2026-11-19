"""Shift calendar: timestamp -> shift_id and crew.

Matches the dbt `shift_id` macro: local 06:00-18:00 = Day, 18:00-06:00 = Night
(labelled with the date the shift starts).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ShiftInfo:
    shift_id: str
    code: str
    name: str
    start: datetime
    end: datetime
    crew: str


class ShiftCalendar:
    def __init__(self, site: dict[str, Any]) -> None:
        self.tz = ZoneInfo(site.get("timezone", "America/Los_Angeles"))
        self.pattern = {p["code"]: p for p in site.get("shift_pattern", [])}
        self.crews = list(site.get("crews", ["A"]))
        start = site.get("crew_rotation_start", "2026-01-01")
        self.rotation_start = date.fromisoformat(start) if isinstance(start, str) else start

    def shift_for(self, ts: datetime) -> ShiftInfo:
        local = ts.astimezone(self.tz) if ts.tzinfo else ts.replace(tzinfo=self.tz)
        hour = local.hour
        if 6 <= hour < 18:
            code, day = "D", local.date()
            start = datetime.combine(day, time(6, 0), tzinfo=self.tz)
        elif hour >= 18:
            code, day = "N", local.date()
            start = datetime.combine(day, time(18, 0), tzinfo=self.tz)
        else:
            code, day = "N", local.date() - timedelta(days=1)
            start = datetime.combine(day, time(18, 0), tzinfo=self.tz)
        entry = self.pattern.get(code, {"code": code, "name": "Day" if code == "D" else "Night", "hours": 12})
        end = start + timedelta(hours=int(entry.get("hours", 12)))
        days = (start.date() - self.rotation_start).days
        crew = self.crews[(days // 2) % len(self.crews)]
        return ShiftInfo(
            shift_id=f"{start.date().isoformat()}-{code}",
            code=code,
            name=entry.get("name", code),
            start=start,
            end=end,
            crew=crew,
        )

    def shift_id(self, ts: datetime) -> str:
        return self.shift_for(ts).shift_id

    def current(self, now: datetime | None = None) -> ShiftInfo:
        return self.shift_for(now or datetime.now(UTC))

    def plan_shift_id(self, shift_date: date, shift_code: str) -> str:
        return f"{shift_date.isoformat()}-{shift_code}"
