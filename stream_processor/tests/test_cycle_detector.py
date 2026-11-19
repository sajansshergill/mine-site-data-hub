"""Unit tests for cycle detection, including a Hypothesis property."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from minehub_common.contracts.truck_telemetry import TruckTelemetry
from stream_processor.cycle_detector import CycleDetector, Phase
from stream_processor.enrichment import Enricher
from stream_processor.geofences import GeofenceIndex, LocationKind, classify_node, distance_m

ROOT = Path(__file__).resolve().parents[2]
ROAD = yaml.safe_load((ROOT / "config" / "road_network.yaml").read_text())
SITE = yaml.safe_load((ROOT / "config" / "site.yaml").read_text())
EQUIP = yaml.safe_load((ROOT / "config" / "equipment.yaml").read_text())

PIT = ROAD["nodes"]["PIT1_B1"]
CRUSHER = ROAD["nodes"]["CRUSHER"]


def _detector() -> CycleDetector:
    return CycleDetector(GeofenceIndex.from_yaml(ROAD), Enricher(site=SITE, equipment=EQUIP))


def _telem(
    truck_id: str,
    ts: datetime,
    x: float,
    y: float,
    payload: float,
    speed: float = 10.0,
) -> TruckTelemetry:
    return TruckTelemetry(
        ts=ts,
        truck_id=truck_id,
        x_m=x,
        y_m=y,
        speed_kmh=speed,
        payload_t=payload,
    )


def test_classify_nodes():
    assert classify_node("PIT1_B1") is LocationKind.SHOVEL
    assert classify_node("CRUSHER") is LocationKind.DUMP
    assert classify_node("WASTE_DUMP_N") is LocationKind.DUMP
    assert classify_node("JUNCTION") is LocationKind.OTHER


def test_geofence_contains_centre():
    idx = GeofenceIndex.from_yaml(ROAD)
    hit = idx.locate(PIT["x"], PIT["y"])
    assert hit.node_id == "PIT1_B1"
    assert hit.kind is LocationKind.SHOVEL
    outside = idx.locate(PIT["x"] + 500, PIT["y"] + 500)
    assert outside.node_id is None


def test_full_cycle_emits_truck_cycle():
    det = _detector()
    t0 = datetime(2026, 6, 15, 14, 0, tzinfo=UTC)

    # Approach shovel empty
    assert det.process(_telem("HT01", t0, PIT["x"] - 200, PIT["y"], 0)).cycle is None
    # Enter shovel / queue
    assert det.process(_telem("HT01", t0 + timedelta(seconds=60), PIT["x"], PIT["y"], 0)).cycle is None
    assert det.get_state("HT01").phase is Phase.QUEUE_LOAD

    # Payload jump = load
    r = det.process(_telem("HT01", t0 + timedelta(seconds=180), PIT["x"], PIT["y"], 220))
    assert r.cycle is None
    assert r.load_event is not None
    assert r.load_event["material"] == "ORE"
    assert det.get_state("HT01").phase is Phase.LOAD

    # Leave shovel → haul full
    mid_x = (PIT["x"] + CRUSHER["x"]) / 2
    mid_y = (PIT["y"] + CRUSHER["y"]) / 2
    assert det.process(_telem("HT01", t0 + timedelta(seconds=200), mid_x, mid_y, 220)).cycle is None
    assert det.get_state("HT01").phase is Phase.HAUL_FULL

    # Enter crusher / queue dump
    assert det.process(_telem("HT01", t0 + timedelta(seconds=500), CRUSHER["x"], CRUSHER["y"], 220)).cycle is None
    assert det.get_state("HT01").phase is Phase.QUEUE_DUMP

    # Payload drop = dump → completed cycle
    done = det.process(_telem("HT01", t0 + timedelta(seconds=560), CRUSHER["x"], CRUSHER["y"], 0))
    assert done.cycle is not None
    c = done.cycle
    assert c.truck_id == "HT01"
    assert c.source_location == "PIT1_B1"
    assert c.dest_location == "CRUSHER"
    assert c.payload_t == 220
    assert c.queue_load_s >= 0
    assert c.haul_full_s >= 0
    assert c.queue_dump_s >= 0
    assert c.haul_empty_s >= 0
    assert c.shift_id.endswith("-D")
    assert det.get_state("HT01").phase is Phase.HAUL_EMPTY


def test_waste_dump_cycle():
    det = _detector()
    pit = ROAD["nodes"]["PIT1_B2"]
    dump = ROAD["nodes"]["WASTE_DUMP_N"]
    t0 = datetime(2026, 6, 16, 3, 0, tzinfo=UTC)  # 20:00 PDT → night shift

    det.process(_telem("HT02", t0, pit["x"], pit["y"], 0))
    det.process(_telem("HT02", t0 + timedelta(seconds=10), pit["x"], pit["y"], 200))
    det.process(_telem("HT02", t0 + timedelta(seconds=20), (pit["x"] + dump["x"]) / 2, (pit["y"] + dump["y"]) / 2, 200))
    det.process(_telem("HT02", t0 + timedelta(seconds=100), dump["x"], dump["y"], 200))
    done = det.process(_telem("HT02", t0 + timedelta(seconds=130), dump["x"], dump["y"], 0))
    assert done.cycle is not None
    assert done.cycle.dest_location == "WASTE_DUMP_N"
    assert done.cycle.shift_id.endswith("-N")


@given(
    xs=st.lists(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), min_size=1, max_size=20),
    ys=st.lists(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), min_size=1, max_size=20),
)
@settings(max_examples=50)
def test_distance_non_negative_and_symmetric(xs, ys):
    """Hypothesis: Euclidean distance is non-negative and symmetric."""
    n = min(len(xs), len(ys))
    for i in range(n):
        for j in range(n):
            d1 = distance_m(xs[i], ys[i], xs[j], ys[j])
            d2 = distance_m(xs[j], ys[j], xs[i], ys[i])
            assert d1 >= 0
            assert d1 == pytest.approx(d2, abs=1e-9)


@given(payload=st.floats(min_value=60, max_value=350, allow_nan=False, allow_infinity=False))
@settings(max_examples=25)
def test_load_then_dump_always_one_cycle(payload: float):
    """Any valid loaded payload at shovel then empty at dump yields exactly one cycle."""
    det = _detector()
    t0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    seq = [
        _telem("HT09", t0, PIT["x"], PIT["y"], 0),
        _telem("HT09", t0 + timedelta(seconds=30), PIT["x"], PIT["y"], float(payload)),
        _telem("HT09", t0 + timedelta(seconds=60), (PIT["x"] + CRUSHER["x"]) / 2, (PIT["y"] + CRUSHER["y"]) / 2, float(payload)),
        _telem("HT09", t0 + timedelta(seconds=120), CRUSHER["x"], CRUSHER["y"], float(payload)),
        _telem("HT09", t0 + timedelta(seconds=150), CRUSHER["x"], CRUSHER["y"], 0),
    ]
    cycles = [det.process(s).cycle for s in seq]
    emitted = [c for c in cycles if c is not None]
    assert len(emitted) == 1
    assert emitted[0].payload_t == pytest.approx(float(payload))
