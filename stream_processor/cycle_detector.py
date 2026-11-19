"""Per-truck cycle state machine driven by geofences + payload changes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from minehub_common.contracts.truck_cycle import TruckCycle
from minehub_common.contracts.truck_telemetry import TruckTelemetry

from stream_processor.enrichment import Enricher
from stream_processor.geofences import GeofenceIndex, LocationKind

# Payload jump/drop thresholds (tonnes) to detect load / dump edges.
LOAD_JUMP_T = 40.0
DUMP_DROP_T = 40.0
EMPTY_PAYLOAD_T = 20.0
LOADED_PAYLOAD_T = 50.0


class Phase(str, Enum):
    HAUL_EMPTY = "haul_empty"
    QUEUE_LOAD = "queue_load"
    LOAD = "load"
    HAUL_FULL = "haul_full"
    QUEUE_DUMP = "queue_dump"
    DUMP = "dump"


@dataclass
class TruckMachine:
    truck_id: str
    phase: Phase = Phase.HAUL_EMPTY
    phase_entered_at: datetime | None = None
    last_ts: datetime | None = None
    last_payload: float = 0.0
    last_node: str | None = None
    last_kind: LocationKind = LocationKind.OTHER

    # Open-cycle accumulators
    haul_empty_enter: datetime | None = None
    queue_load_enter: datetime | None = None
    load_start: datetime | None = None
    load_end: datetime | None = None
    source_location: str | None = None
    payload_t: float = 0.0
    haul_full_enter: datetime | None = None
    queue_dump_enter: datetime | None = None
    dump_start: datetime | None = None
    dump_end: datetime | None = None
    dest_location: str | None = None
    haul_empty_s: float = 0.0
    queue_load_s: float = 0.0
    queue_dump_s: float = 0.0
    haul_full_s: float = 0.0
    open_cycle_id: Any = None
    revision: int = 0


@dataclass
class DetectorResult:
    cycle: TruckCycle | None = None
    load_event: dict[str, Any] | None = None  # for Redis record_load
    queue_deltas: list[tuple[str, int]] = field(default_factory=list)  # (location, delta)


class CycleDetector:
    """Detect completed truck cycles from telemetry samples."""

    def __init__(self, geofences: GeofenceIndex, enricher: Enricher | None = None) -> None:
        self.geofences = geofences
        self.enricher = enricher or Enricher()
        self._trucks: dict[str, TruckMachine] = {}

    def get_state(self, truck_id: str) -> TruckMachine:
        if truck_id not in self._trucks:
            self._trucks[truck_id] = TruckMachine(truck_id=truck_id)
        return self._trucks[truck_id]

    def process(self, telem: TruckTelemetry) -> DetectorResult:
        st = self.get_state(telem.truck_id)
        hit = self.geofences.locate(telem.x_m, telem.y_m)
        result = DetectorResult()
        prev_payload = st.last_payload
        prev_kind = st.last_kind
        prev_node = st.last_node
        delta = telem.payload_t - prev_payload

        # Queue length: entering / leaving shovel or dump geofences while waiting.
        if hit.node_id and hit.node_id != prev_node:
            if hit.kind is LocationKind.SHOVEL and telem.payload_t < LOADED_PAYLOAD_T:
                result.queue_deltas.append((hit.node_id, 1))
            if prev_node and prev_kind is LocationKind.SHOVEL and prev_payload < LOADED_PAYLOAD_T:
                result.queue_deltas.append((prev_node, -1))
            if hit.kind is LocationKind.DUMP and telem.payload_t >= LOADED_PAYLOAD_T:
                result.queue_deltas.append((hit.node_id, 1))
            if prev_node and prev_kind is LocationKind.DUMP and prev_payload >= LOADED_PAYLOAD_T:
                result.queue_deltas.append((prev_node, -1))

        if st.phase is Phase.HAUL_EMPTY:
            self._on_haul_empty(st, telem, hit, result)
        elif st.phase is Phase.QUEUE_LOAD:
            self._on_queue_load(st, telem, hit, delta, result)
        elif st.phase is Phase.LOAD:
            self._on_load(st, telem, hit, result)
        elif st.phase is Phase.HAUL_FULL:
            self._on_haul_full(st, telem, hit, result)
        elif st.phase is Phase.QUEUE_DUMP:
            self._on_queue_dump(st, telem, hit, delta, result)
        elif st.phase is Phase.DUMP:
            self._on_dump(st, telem, hit, result)

        st.last_ts = telem.ts
        st.last_payload = telem.payload_t
        st.last_node = hit.node_id
        st.last_kind = hit.kind
        return result

    def revise_open(
        self,
        truck_id: str,
        *,
        load_start: datetime | None = None,
        load_end: datetime | None = None,
        dump_start: datetime | None = None,
        dump_end: datetime | None = None,
        payload_t: float | None = None,
        source_location: str | None = None,
        dest_location: str | None = None,
    ) -> TruckCycle | None:
        """Apply late-data corrections to an open/recent cycle and bump revision."""
        st = self.get_state(truck_id)
        if st.load_start is None:
            return None
        if load_start is not None:
            st.load_start = load_start
        if load_end is not None:
            st.load_end = load_end
        if dump_start is not None:
            st.dump_start = dump_start
        if dump_end is not None:
            st.dump_end = dump_end
        if payload_t is not None:
            st.payload_t = payload_t
        if source_location is not None:
            st.source_location = source_location
        if dest_location is not None:
            st.dest_location = dest_location
        st.revision += 1
        if st.dump_end is not None and st.dump_start is not None and st.load_end is not None:
            return self._emit(st)
        return None

    # ---- phase handlers ----

    def _on_haul_empty(self, st: TruckMachine, telem: TruckTelemetry, hit: Any, result: DetectorResult) -> None:
        if st.haul_empty_enter is None:
            st.haul_empty_enter = telem.ts
            st.phase_entered_at = telem.ts
        if hit.kind is LocationKind.SHOVEL and telem.payload_t < LOADED_PAYLOAD_T:
            if st.haul_empty_enter is not None:
                st.haul_empty_s = max(0.0, (telem.ts - st.haul_empty_enter).total_seconds())
            st.queue_load_enter = telem.ts
            st.phase = Phase.QUEUE_LOAD
            st.phase_entered_at = telem.ts

    def _on_queue_load(
        self, st: TruckMachine, telem: TruckTelemetry, hit: Any, delta: float, result: DetectorResult
    ) -> None:
        if hit.kind is LocationKind.SHOVEL and delta >= LOAD_JUMP_T and telem.payload_t >= LOADED_PAYLOAD_T:
            self._start_load(st, telem, hit, result)
            return
        # Left shovel without loading — keep queuing intent if still empty elsewhere.
        if hit.kind is not LocationKind.SHOVEL and telem.payload_t < LOADED_PAYLOAD_T:
            st.phase = Phase.HAUL_EMPTY
            st.haul_empty_enter = telem.ts
            st.phase_entered_at = telem.ts
            st.queue_load_enter = None

    def _on_load(self, st: TruckMachine, telem: TruckTelemetry, hit: Any, result: DetectorResult) -> None:
        # Leave shovel geofence while loaded → haul full.
        if hit.kind is not LocationKind.SHOVEL and telem.payload_t >= LOADED_PAYLOAD_T:
            if st.load_end is None:
                st.load_end = telem.ts
            st.haul_full_enter = telem.ts
            st.phase = Phase.HAUL_FULL
            st.phase_entered_at = telem.ts

    def _on_haul_full(self, st: TruckMachine, telem: TruckTelemetry, hit: Any, result: DetectorResult) -> None:
        if hit.kind is LocationKind.DUMP and telem.payload_t >= LOADED_PAYLOAD_T:
            st.queue_dump_enter = telem.ts
            st.phase = Phase.QUEUE_DUMP
            st.phase_entered_at = telem.ts

    def _on_queue_dump(
        self, st: TruckMachine, telem: TruckTelemetry, hit: Any, delta: float, result: DetectorResult
    ) -> None:
        if hit.kind is LocationKind.DUMP and delta <= -DUMP_DROP_T and telem.payload_t <= EMPTY_PAYLOAD_T:
            self._complete_dump(st, telem, hit, result)
            return
        if hit.kind is not LocationKind.DUMP and telem.payload_t >= LOADED_PAYLOAD_T:
            st.phase = Phase.HAUL_FULL
            st.phase_entered_at = telem.ts
            st.queue_dump_enter = None

    def _on_dump(self, st: TruckMachine, telem: TruckTelemetry, hit: Any, result: DetectorResult) -> None:
        # After dump completion we immediately reset; this is a safety net.
        if hit.kind is not LocationKind.DUMP or telem.payload_t <= EMPTY_PAYLOAD_T:
            st.phase = Phase.HAUL_EMPTY
            st.haul_empty_enter = telem.ts
            st.phase_entered_at = telem.ts

    def _start_load(self, st: TruckMachine, telem: TruckTelemetry, hit: Any, result: DetectorResult) -> None:
        load_start = st.last_ts or telem.ts
        if st.queue_load_enter is not None:
            st.queue_load_s = max(0.0, (load_start - st.queue_load_enter).total_seconds())
        else:
            st.queue_load_s = 0.0
        st.load_start = load_start
        st.load_end = telem.ts
        st.source_location = hit.node_id
        st.payload_t = telem.payload_t
        st.open_cycle_id = uuid4()
        st.revision = 0
        st.phase = Phase.LOAD
        st.phase_entered_at = telem.ts
        shift_id = self.enricher.shift_id(telem.ts)
        material = self.enricher.material(st.source_location) or "UNKNOWN"
        result.load_event = {
            "shift_id": shift_id,
            "truck_id": st.truck_id,
            "payload": st.payload_t,
            "material": material,
            "location": st.source_location,
        }
        # Leaving the shovel queue when load starts.
        if hit.node_id:
            result.queue_deltas.append((hit.node_id, -1))

    def _complete_dump(self, st: TruckMachine, telem: TruckTelemetry, hit: Any, result: DetectorResult) -> None:
        dump_start = st.last_ts or telem.ts
        if st.queue_dump_enter is not None:
            queue_dump_s = max(0.0, (dump_start - st.queue_dump_enter).total_seconds())
        else:
            queue_dump_s = 0.0
        st.dump_start = dump_start
        st.dump_end = telem.ts
        st.dest_location = hit.node_id
        if hit.node_id:
            result.queue_deltas.append((hit.node_id, -1))

        haul_full_s = 0.0
        if st.haul_full_enter is not None and st.queue_dump_enter is not None:
            haul_full_s = max(0.0, (st.queue_dump_enter - st.haul_full_enter).total_seconds())
        elif st.load_end is not None and st.queue_dump_enter is not None:
            haul_full_s = max(0.0, (st.queue_dump_enter - st.load_end).total_seconds())

        st.queue_dump_s = queue_dump_s
        st.haul_full_s = haul_full_s
        result.cycle = self._emit(st)

        # Reset for next cycle (empty haul begins now).
        st.phase = Phase.HAUL_EMPTY
        st.phase_entered_at = telem.ts
        st.haul_empty_enter = telem.ts
        st.queue_load_enter = None
        st.load_start = None
        st.load_end = None
        st.source_location = None
        st.payload_t = 0.0
        st.haul_full_enter = None
        st.queue_dump_enter = None
        st.dump_start = None
        st.dump_end = None
        st.dest_location = None
        st.haul_empty_s = 0.0
        st.queue_load_s = 0.0
        st.queue_dump_s = 0.0
        st.haul_full_s = 0.0
        st.open_cycle_id = None
        st.revision = 0

    def _emit(self, st: TruckMachine) -> TruckCycle | None:
        if (
            st.load_start is None
            or st.load_end is None
            or st.dump_start is None
            or st.dump_end is None
            or not st.source_location
            or not st.dest_location
            or st.payload_t <= 0
        ):
            return None
        shift_id = self.enricher.shift_id(st.load_start)
        return TruckCycle(
            cycle_id=st.open_cycle_id or uuid4(),
            truck_id=st.truck_id,
            shift_id=shift_id,
            load_start=st.load_start,
            load_end=st.load_end,
            dump_start=st.dump_start,
            dump_end=st.dump_end,
            source_location=st.source_location,
            dest_location=st.dest_location,
            payload_t=st.payload_t,
            queue_load_s=max(0.0, st.queue_load_s),
            queue_dump_s=max(0.0, st.queue_dump_s),
            haul_full_s=max(0.0, st.haul_full_s),
            haul_empty_s=max(0.0, st.haul_empty_s),
            revision=st.revision,
        )


def telemetry_from_dict(payload: dict[str, Any]) -> TruckTelemetry:
    """Build TruckTelemetry from Avro/JSON dict (ms epoch or datetime)."""
    ts = payload["ts"]
    if isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts / 1000.0, tz=UTC)
    elif isinstance(ts, datetime) and ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return TruckTelemetry(
        ts=ts,
        truck_id=str(payload["truck_id"]),
        x_m=float(payload["x_m"]),
        y_m=float(payload["y_m"]),
        speed_kmh=float(payload.get("speed_kmh", 0)),
        payload_t=float(payload.get("payload_t", 0)),
        engine_on=bool(payload.get("engine_on", True)),
        fuel_pct=payload.get("fuel_pct"),
        msg_id=str(payload.get("msg_id") or uuid4().hex),
    )
