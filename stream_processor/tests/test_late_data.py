"""Watermark / revision tests for late-data handling."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from minehub_common.contracts.truck_cycle import TruckCycle
from stream_processor.late_data import (
    DEFAULT_ALLOWED_LATENESS,
    WatermarkBook,
    advance_watermark,
    bump_revision,
    classify_event,
    decide_action,
    merge_late_into_recent,
    revise_cycle,
    watermark_is_monotonic,
)


def _ts(minutes: int) -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC) + timedelta(minutes=minutes)


def _cycle(**kwargs) -> TruckCycle:
    base = dict(
        cycle_id=uuid4(),
        truck_id="HT01",
        shift_id="2026-01-01-D",
        load_start=_ts(0),
        load_end=_ts(3),
        dump_start=_ts(20),
        dump_end=_ts(22),
        source_location="PIT1_B1",
        dest_location="CRUSHER",
        payload_t=200.0,
        queue_load_s=30.0,
        queue_dump_s=20.0,
        haul_full_s=900.0,
        haul_empty_s=600.0,
        revision=0,
    )
    base.update(kwargs)
    return TruckCycle(**base)


def test_classify_on_time_when_no_watermark():
    assert classify_event(_ts(0), None) == "on_time"


def test_classify_on_time_at_watermark():
    assert classify_event(_ts(10), _ts(10)) == "on_time"


def test_classify_late_revisable_within_window():
    wm = _ts(10)
    late = wm - timedelta(minutes=2)
    assert classify_event(late, wm, DEFAULT_ALLOWED_LATENESS) == "late_revisable"


def test_classify_too_late_beyond_window():
    wm = _ts(10)
    late = wm - timedelta(minutes=30)
    assert classify_event(late, wm, DEFAULT_ALLOWED_LATENESS) == "too_late"


def test_advance_watermark_is_max():
    before = {"HT01": _ts(5)}
    after = advance_watermark(before, "HT01", _ts(3))
    assert after["HT01"] == _ts(5)
    after2 = advance_watermark(before, "HT01", _ts(8))
    assert after2["HT01"] == _ts(8)
    assert before["HT01"] == _ts(5)  # pure: input unchanged


def test_decide_action_drops_too_late_without_advancing():
    book = WatermarkBook(watermarks={"HT01": _ts(60)})
    klass, new_book = decide_action("HT01", _ts(0), book)
    assert klass == "too_late"
    assert new_book.watermarks["HT01"] == _ts(60)


def test_decide_action_advances_on_time():
    book = WatermarkBook(watermarks={})
    klass, new_book = decide_action("HT01", _ts(1), book)
    assert klass == "on_time"
    assert new_book.watermarks["HT01"] == _ts(1)


def test_bump_and_revise_increment_revision():
    c = _cycle()
    assert bump_revision(c).revision == 1
    revised = revise_cycle(c, payload_t=210.0)
    assert revised.revision == 1
    assert revised.payload_t == 210.0
    assert c.revision == 0


def test_merge_late_into_recent_revises_within_window():
    recent = _cycle(dump_end=_ts(30), payload_t=180.0)
    late_ts = _ts(28)
    out = merge_late_into_recent(
        recent,
        late_ts,
        DEFAULT_ALLOWED_LATENESS,
        field_updates={"payload_t": 195.0},
    )
    assert out is not None
    assert out.revision == 1
    assert out.payload_t == 195.0


def test_merge_late_into_recent_rejects_too_old():
    recent = _cycle(dump_end=_ts(30))
    out = merge_late_into_recent(recent, _ts(0), DEFAULT_ALLOWED_LATENESS)
    assert out is None


@given(
    truck=st.sampled_from(["HT01", "HT02", "HT03"]),
    times=st.lists(
        st.integers(min_value=0, max_value=10_000),
        min_size=1,
        max_size=40,
    ),
)
@settings(max_examples=40)
def test_watermark_monotonic_property(truck: str, times: list[int]):
    """Hypothesis: advancing watermarks never moves a truck's watermark backwards."""
    book = WatermarkBook(watermarks={})
    for minutes in times:
        before = dict(book.watermarks)
        _klass, book = decide_action(truck, _ts(minutes), book)
        assert watermark_is_monotonic(before, book.watermarks, truck)
