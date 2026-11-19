"""Watermarking and late-event revision helpers (pure where possible)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Mapping

from minehub_common.contracts.truck_cycle import TruckCycle

EventClass = Literal["on_time", "late_revisable", "too_late"]

DEFAULT_ALLOWED_LATENESS = timedelta(minutes=5)


@dataclass(frozen=True)
class WatermarkBook:
    """Per-truck event-time watermarks (max observed ts)."""

    watermarks: Mapping[str, datetime]
    allowed_lateness: timedelta = DEFAULT_ALLOWED_LATENESS

    def watermark_for(self, truck_id: str) -> datetime | None:
        return self.watermarks.get(truck_id)


def advance_watermark(
    watermarks: Mapping[str, datetime],
    truck_id: str,
    event_ts: datetime,
) -> dict[str, datetime]:
    """Return a new dict with truck watermark = max(old, event_ts)."""
    out = dict(watermarks)
    prev = out.get(truck_id)
    if prev is None or event_ts > prev:
        out[truck_id] = event_ts
    return out


def classify_event(
    event_ts: datetime,
    watermark: datetime | None,
    allowed_lateness: timedelta = DEFAULT_ALLOWED_LATENESS,
) -> EventClass:
    """Classify an event relative to the truck watermark."""
    if watermark is None or event_ts >= watermark:
        return "on_time"
    lag = watermark - event_ts
    if lag <= allowed_lateness:
        return "late_revisable"
    return "too_late"


def with_advanced_watermark(book: WatermarkBook, truck_id: str, event_ts: datetime) -> WatermarkBook:
    return WatermarkBook(
        watermarks=advance_watermark(book.watermarks, truck_id, event_ts),
        allowed_lateness=book.allowed_lateness,
    )


def decide_action(
    truck_id: str,
    event_ts: datetime,
    book: WatermarkBook,
) -> tuple[EventClass, WatermarkBook]:
    """Pure: classify then advance watermark for on-time / revisable events."""
    klass = classify_event(event_ts, book.watermark_for(truck_id), book.allowed_lateness)
    if klass == "too_late":
        return klass, book
    return klass, with_advanced_watermark(book, truck_id, event_ts)


def bump_revision(cycle: TruckCycle) -> TruckCycle:
    return cycle.model_copy(update={"revision": cycle.revision + 1})


def revise_cycle(cycle: TruckCycle, **updates: Any) -> TruckCycle:
    """Return a revised cycle with revision incremented. Rejects unknown fields via model."""
    data = cycle.model_dump()
    data.update(updates)
    data["revision"] = cycle.revision + 1
    return TruckCycle(**data)


def merge_late_into_recent(
    recent: TruckCycle | None,
    late_ts: datetime,
    allowed_lateness: timedelta,
    *,
    field_updates: Mapping[str, Any] | None = None,
) -> TruckCycle | None:
    """
    If `recent` is within the lateness window of `late_ts`, apply updates and bump revision.
    Returns None when there is nothing to revise.
    """
    if recent is None:
        return None
    # Use dump_end as the cycle's event-time anchor.
    anchor = recent.dump_end
    if late_ts > anchor:
        return None
    if anchor - late_ts > allowed_lateness:
        return None
    return revise_cycle(recent, **dict(field_updates or {}))


def apply_book_event(book: WatermarkBook, truck_id: str, event_ts: datetime) -> tuple[EventClass, WatermarkBook]:
    """Alias kept for hypothesis-friendly API stability."""
    return decide_action(truck_id, event_ts, book)


# Convenience for immutable Mapping updates in property tests
def watermark_is_monotonic(before: Mapping[str, datetime], after: Mapping[str, datetime], truck_id: str) -> bool:
    if truck_id not in after:
        return truck_id not in before
    if truck_id not in before:
        return True
    return after[truck_id] >= before[truck_id]
