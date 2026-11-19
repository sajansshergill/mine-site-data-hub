"""Stream processor: telemetry -> cycles + Redis live state."""
from __future__ import annotations

import logging
import time
from typing import Any

from confluent_kafka import Message

from minehub_common.kafka.consumer import HubConsumer
from minehub_common.kafka.producer import HubProducer
from minehub_common.logging import setup_logging
from minehub_common.metrics import LAST_MESSAGE_TS, MESSAGES_IN, PROCESS_SECONDS, VALIDATION_FAIL, start_metrics_server
from minehub_common.settings import get_settings

from stream_processor.cycle_detector import CycleDetector, telemetry_from_dict
from stream_processor.enrichment import Enricher
from stream_processor.geofences import GeofenceIndex
from stream_processor.late_data import WatermarkBook, decide_action, merge_late_into_recent
from stream_processor.live_state import LiveState

SERVICE = "stream-processor"
TELEMETRY_TOPIC = "fleet.telemetry"
EVENTS_TOPIC = "equipment.events"
CYCLES_TOPIC = "fleet.cycles"
GROUP_ID = "stream-processor"

log = logging.getLogger(SERVICE)


class Processor:
    def __init__(self) -> None:
        self.settings = get_settings()
        road = self.settings.load_yaml("road_network.yaml")
        site = self.settings.load_yaml("site.yaml")
        equipment = self.settings.load_yaml("equipment.yaml")
        self.enricher = Enricher(site=site, equipment=equipment)
        self.detector = CycleDetector(GeofenceIndex.from_yaml(road), self.enricher)
        self.live = LiveState(self.settings.redis_url)
        self.watermarks = WatermarkBook(watermarks={})
        self.recent_cycles: dict[str, Any] = {}
        self.producer = HubProducer(
            self.settings.kafka_bootstrap,
            self.settings.schema_registry_url,
            SERVICE,
        )
        self.consumer = HubConsumer(
            self.settings.kafka_bootstrap,
            GROUP_ID,
            [TELEMETRY_TOPIC, EVENTS_TOPIC],
            self.settings.schema_registry_url,
            client_id=SERVICE,
        )

    def handle(self, msg: Message, payload: dict[str, Any]) -> None:
        topic = msg.topic()
        MESSAGES_IN.labels(SERVICE, topic or "unknown").inc()
        LAST_MESSAGE_TS.labels(SERVICE, topic or "unknown").set(time.time())
        if topic == TELEMETRY_TOPIC:
            self._handle_telemetry(payload)
        elif topic == EVENTS_TOPIC:
            # Equipment events are consumed for lag awareness; cycle logic is telemetry-driven.
            log.debug("equipment event", extra={"extra": {"equipment_id": payload.get("equipment_id")}})

    def _handle_telemetry(self, payload: dict[str, Any]) -> None:
        t0 = time.perf_counter()
        try:
            telem = telemetry_from_dict(payload)
        except Exception as exc:  # noqa: BLE001
            VALIDATION_FAIL.labels(SERVICE, "telemetry").inc()
            log.warning("invalid telemetry", extra={"extra": {"error": str(exc)}})
            self.producer.send_dlq(TELEMETRY_TOPIC, payload, str(exc))
            return

        klass, self.watermarks = decide_action(telem.truck_id, telem.ts, self.watermarks)
        if klass == "too_late":
            log.info(
                "dropping too-late event",
                extra={"extra": {"truck_id": telem.truck_id, "ts": telem.ts.isoformat()}},
            )
            PROCESS_SECONDS.labels(SERVICE, "telemetry").observe(time.perf_counter() - t0)
            return

        if klass == "late_revisable":
            revised = self.detector.revise_open(
                telem.truck_id,
                payload_t=telem.payload_t if telem.payload_t > 0 else None,
            )
            if revised is None:
                revised = merge_late_into_recent(
                    self.recent_cycles.get(telem.truck_id),
                    telem.ts,
                    self.watermarks.allowed_lateness,
                    field_updates={"payload_t": telem.payload_t} if telem.payload_t > 0 else None,
                )
            if revised is not None:
                self.producer.send(CYCLES_TOPIC, revised.to_avro(), key=telem.truck_id)
                self.recent_cycles[telem.truck_id] = revised
            PROCESS_SECONDS.labels(SERVICE, "telemetry").observe(time.perf_counter() - t0)
            return

        result = self.detector.process(telem)

        # Shift rollover for live Redis counters.
        shift_id = self.enricher.shift_id(telem.ts)
        self.live.ensure_current_shift(shift_id)

        for location, delta in result.queue_deltas:
            if location and delta:
                self.live.update_queue(location, delta)

        if result.load_event:
            ev = result.load_event
            self.live.record_load(
                ev["shift_id"],
                ev["truck_id"],
                ev["payload"],
                ev["material"],
                ev["location"],
            )

        if result.cycle is not None:
            self.producer.send(CYCLES_TOPIC, result.cycle.to_avro(), key=result.cycle.truck_id)
            self.recent_cycles[result.cycle.truck_id] = result.cycle
            log.info(
                "cycle completed",
                extra={
                    "extra": {
                        "truck_id": result.cycle.truck_id,
                        "cycle_id": str(result.cycle.cycle_id),
                        "payload_t": result.cycle.payload_t,
                        "source": result.cycle.source_location,
                        "dest": result.cycle.dest_location,
                    }
                },
            )

        PROCESS_SECONDS.labels(SERVICE, "telemetry").observe(time.perf_counter() - t0)

    def run(self) -> None:
        log.info("stream processor starting", extra={"extra": {"group": GROUP_ID}})
        try:
            self.consumer.run(self.handle)
        finally:
            self.producer.flush()


def main() -> None:
    setup_logging(SERVICE)
    s = get_settings()
    start_metrics_server(s.metrics_port)
    Processor().run()


if __name__ == "__main__":
    main()
