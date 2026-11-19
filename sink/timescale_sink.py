"""Batched Redpanda -> TimescaleDB sink with exactly-once offset commits."""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import psycopg
from confluent_kafka import Message, TopicPartition

from minehub_common.db.bulk import upsert_via_staging
from minehub_common.kafka.consumer import HubConsumer
from minehub_common.logging import setup_logging
from minehub_common.metrics import LAST_MESSAGE_TS, MESSAGES_IN, PROCESS_SECONDS, VALIDATION_FAIL, start_metrics_server
from minehub_common.settings import get_settings

SERVICE = "timescale-sink"
GROUP_ID = "timescale-sink"
TOPICS = ("fleet.telemetry", "plant.tags", "equipment.events", "fleet.cycles")

BATCH_SIZE = 500
BATCH_TIMEOUT_S = 2.0

log = logging.getLogger(SERVICE)


def _ts(value: Any) -> datetime:
    """Convert Avro/JSON ms-epoch (or datetime) to aware timestamptz."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, (int, float)):
        raise TypeError(f"unsupported timestamp: {value!r}")
    v = float(value)
    # Avro logicalType timestamp-millis → ms since epoch.
    if abs(v) >= 1e11:
        return datetime.fromtimestamp(v / 1000.0, tz=UTC)
    return datetime.fromtimestamp(v, tz=UTC)


def row_telemetry(p: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _ts(p["ts"]),
        str(p["msg_id"]),
        str(p["truck_id"]),
        float(p["x_m"]),
        float(p["y_m"]),
        float(p["speed_kmh"]),
        float(p["payload_t"]),
        bool(p.get("engine_on", True)),
        None if p.get("fuel_pct") is None else float(p["fuel_pct"]),
    )


def row_plant_tag(p: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _ts(p["ts"]),
        str(p["tag"]),
        str(p.get("source", "unknown")),
        float(p["value"]),
        str(p.get("quality", "GOOD")),
    )


def row_equipment_event(p: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _ts(p["ts"]),
        str(p["equipment_id"]),
        str(p["status"]),
        p.get("reason"),
        p.get("fault_code"),
        str(p["vendor"]),
        str(p["raw_code"]),
    )


def row_truck_cycle(p: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(p["cycle_id"]),
        str(p["truck_id"]),
        str(p["shift_id"]),
        _ts(p["load_start"]),
        _ts(p["load_end"]),
        _ts(p["dump_start"]),
        _ts(p["dump_end"]),
        str(p["source_location"]),
        str(p["dest_location"]),
        float(p["payload_t"]),
        float(p["queue_load_s"]),
        float(p["queue_dump_s"]),
        float(p["haul_full_s"]),
        float(p["haul_empty_s"]),
        int(p.get("revision", 0)),
    )


TELEMETRY_COLS = ("ts", "msg_id", "truck_id", "x_m", "y_m", "speed_kmh", "payload_t", "engine_on", "fuel_pct")
PLANT_COLS = ("ts", "tag", "source", "value", "quality")
EQUIP_COLS = ("ts", "equipment_id", "status", "reason", "fault_code", "vendor", "raw_code")
CYCLE_COLS = (
    "cycle_id",
    "truck_id",
    "shift_id",
    "load_start",
    "load_end",
    "dump_start",
    "dump_end",
    "source_location",
    "dest_location",
    "payload_t",
    "queue_load_s",
    "queue_dump_s",
    "haul_full_s",
    "haul_empty_s",
    "revision",
)


class OffsetTracker:
    """Track high-water next_offset per (topic, partition) for the batch."""

    def __init__(self) -> None:
        self._next: dict[tuple[str, int], int] = {}

    def observe(self, topic: str, partition: int, offset: int) -> None:
        key = (topic, partition)
        nxt = offset + 1
        prev = self._next.get(key)
        if prev is None or nxt > prev:
            self._next[key] = nxt

    def items(self) -> list[tuple[str, int, int]]:
        return [(t, p, o) for (t, p), o in self._next.items()]

    def clear(self) -> None:
        self._next.clear()

    def __bool__(self) -> bool:
        return bool(self._next)


class TimescaleSink:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.consumer = HubConsumer(
            self.settings.kafka_bootstrap,
            GROUP_ID,
            TOPICS,
            self.settings.schema_registry_url,
            client_id=SERVICE,
        )
        self._conn = psycopg.connect(self.settings.psycopg_dsn, autocommit=False)
        self._seek_from_offsets()

        self._telemetry: list[tuple[Any, ...]] = []
        self._plant: list[tuple[Any, ...]] = []
        self._equipment: list[tuple[Any, ...]] = []
        self._cycles: list[tuple[Any, ...]] = []
        self._offsets = OffsetTracker()
        self._pending_msgs: list[Message] = []
        self._last_flush = time.monotonic()

    def _seek_from_offsets(self) -> None:
        """On startup, seek each partition to ops.ingest_offsets.next_offset when present."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT topic, partition, next_offset FROM ops.ingest_offsets WHERE consumer_group = %s",
                (GROUP_ID,),
            )
            rows = cur.fetchall()
        self._conn.commit()
        if not rows:
            return
        # Assignments are not ready until the first poll; seek after subscribe via on_assign callback.
        stored = {(t, int(p)): int(o) for t, p, o in rows}

        def on_assign(consumer: Any, partitions: list[TopicPartition]) -> None:
            for tp in partitions:
                key = (tp.topic, tp.partition)
                if key in stored:
                    tp.offset = stored[key]
                    log.info(
                        "seeking from ingest_offsets",
                        extra={"extra": {"topic": tp.topic, "partition": tp.partition, "offset": tp.offset}},
                    )
            consumer.assign(partitions)

        # Re-subscribe with on_assign. confluent_kafka Consumer.subscribe supports on_assign.
        self.consumer._consumer.subscribe(list(TOPICS), on_assign=on_assign)

    def run(self) -> None:
        log.info("sink starting", extra={"extra": {"group": GROUP_ID, "topics": list(TOPICS)}})
        try:
            while True:
                msg = self.consumer.poll(0.5)
                if msg is None:
                    if self._should_flush():
                        self.flush()
                    continue
                if msg.error():
                    log.error("kafka error", extra={"extra": {"error": str(msg.error())}})
                    continue
                self._ingest(msg)
                if len(self._pending_msgs) >= BATCH_SIZE or self._should_flush():
                    self.flush()
        finally:
            try:
                self.flush()
            finally:
                self.consumer.close()
                self._conn.close()

    def _should_flush(self) -> bool:
        if not self._pending_msgs:
            return False
        return (time.monotonic() - self._last_flush) >= BATCH_TIMEOUT_S

    def _ingest(self, msg: Message) -> None:
        topic = msg.topic() or ""
        MESSAGES_IN.labels(SERVICE, topic).inc()
        LAST_MESSAGE_TS.labels(SERVICE, topic).set(time.time())
        try:
            payload = self.consumer.decode(msg)
        except Exception as exc:  # noqa: BLE001
            VALIDATION_FAIL.labels(SERVICE, "decode").inc()
            log.warning("decode failed", extra={"extra": {"error": str(exc), "topic": topic}})
            return

        try:
            if topic == "fleet.telemetry":
                self._telemetry.append(row_telemetry(payload))
            elif topic == "plant.tags":
                self._plant.append(row_plant_tag(payload))
            elif topic == "equipment.events":
                self._equipment.append(row_equipment_event(payload))
            elif topic == "fleet.cycles":
                self._cycles.append(row_truck_cycle(payload))
            else:
                return
        except Exception as exc:  # noqa: BLE001
            VALIDATION_FAIL.labels(SERVICE, topic).inc()
            log.warning("row map failed", extra={"extra": {"error": str(exc), "topic": topic}})
            return

        self._offsets.observe(topic, msg.partition(), msg.offset())
        self._pending_msgs.append(msg)

    def flush(self) -> None:
        if not self._pending_msgs:
            return
        t0 = time.perf_counter()
        n = len(self._pending_msgs)
        try:
            with self._conn.cursor() as cur:
                if self._telemetry:
                    # COPY-friendly staging upsert so redelivery is idempotent on (ts, msg_id).
                    upsert_via_staging(
                        self._conn,
                        "raw.truck_telemetry",
                        TELEMETRY_COLS,
                        ("ts", "msg_id"),
                        self._telemetry,
                    )
                if self._plant:
                    upsert_via_staging(
                        self._conn,
                        "raw.plant_tags",
                        PLANT_COLS,
                        ("ts", "tag", "source"),
                        self._plant,
                    )
                if self._equipment:
                    upsert_via_staging(
                        self._conn,
                        "raw.equipment_events",
                        EQUIP_COLS,
                        ("ts", "equipment_id", "raw_code"),
                        self._equipment,
                    )
                if self._cycles:
                    # Upsert on cycle_id; only apply when incoming revision >= existing.
                    self._upsert_cycles(cur)

                for topic, partition, next_offset in self._offsets.items():
                    cur.execute(
                        """
                        INSERT INTO ops.ingest_offsets (consumer_group, topic, partition, next_offset, updated_at)
                        VALUES (%s, %s, %s, %s, now())
                        ON CONFLICT (consumer_group, topic, partition)
                        DO UPDATE SET next_offset = EXCLUDED.next_offset, updated_at = now()
                        """,
                        (GROUP_ID, topic, partition, next_offset),
                    )
            self._conn.commit()
            # Commit Kafka offsets after the DB transaction succeeds.
            self.consumer.commit(asynchronous=False)
        except Exception:
            self._conn.rollback()
            log.exception("flush failed")
            raise
        else:
            self._telemetry.clear()
            self._plant.clear()
            self._equipment.clear()
            self._cycles.clear()
            self._offsets.clear()
            self._pending_msgs.clear()
            self._last_flush = time.monotonic()
            PROCESS_SECONDS.labels(SERVICE, "flush").observe(time.perf_counter() - t0)
            log.info("flushed batch", extra={"extra": {"messages": n}})

    def _upsert_cycles(self, cur: psycopg.Cursor) -> None:
        """Upsert truck cycles by cycle_id, keeping the higher revision."""
        cols = ", ".join(CYCLE_COLS)
        placeholders = ", ".join(["%s"] * len(CYCLE_COLS))
        updates = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in CYCLE_COLS if c != "cycle_id"
        )
        sql = f"""
            INSERT INTO raw.truck_cycles ({cols})
            VALUES ({placeholders})
            ON CONFLICT (cycle_id) DO UPDATE SET {updates}
            WHERE raw.truck_cycles.revision <= EXCLUDED.revision
        """
        # Deduplicate by cycle_id keeping max revision within the batch.
        best: dict[str, tuple[Any, ...]] = {}
        for row in self._cycles:
            cid = str(row[0])
            prev = best.get(cid)
            if prev is None or int(row[-1]) >= int(prev[-1]):
                best[cid] = row
        cur.executemany(sql, list(best.values()))


def main() -> None:
    setup_logging(SERVICE)
    s = get_settings()
    start_metrics_server(s.metrics_port)
    TimescaleSink().run()


if __name__ == "__main__":
    main()
