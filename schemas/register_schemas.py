"""Register Avro schemas with Redpanda Schema Registry and ensure topics exist."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import httpx
from confluent_kafka.admin import AdminClient, NewTopic

from minehub_common.logging import setup_logging
from minehub_common.settings import get_settings

log = logging.getLogger("register-schemas")

SUBJECTS = {
    "fleet.telemetry-value": "truck_telemetry.v1.avsc",
    "plant.tags-value": "plant_tag.v1.avsc",
    "equipment.events-value": "equipment_event.v1.avsc",
    "fleet.cycles-value": "truck_cycle.v1.avsc",
}

TOPICS = [
    "fleet.telemetry",
    "fleet.telemetry.dlq",
    "plant.tags",
    "plant.tags.dlq",
    "equipment.events",
    "equipment.events.dlq",
    "fleet.cycles",
    "fleet.cycles.dlq",
]


def ensure_topics(bootstrap: str) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap})
    existing = set(admin.list_topics(timeout=10).topics)
    new = [NewTopic(t, num_partitions=3, replication_factor=1) for t in TOPICS if t not in existing]
    if not new:
        return
    futures = admin.create_topics(new)
    for name, fut in futures.items():
        try:
            fut.result()
            log.info("created topic", extra={"extra": {"topic": name}})
        except Exception as exc:  # noqa: BLE001
            log.warning("topic create", extra={"extra": {"topic": name, "error": str(exc)}})


def register(registry: str, schema_dir: Path) -> None:
    client = httpx.Client(base_url=registry.rstrip("/"), timeout=15)
    for subject, filename in SUBJECTS.items():
        schema = (schema_dir / filename).read_text(encoding="utf-8")
        # validate JSON
        json.loads(schema)
        for attempt in range(10):
            try:
                resp = client.post(f"/subjects/{subject}/versions", json={"schema": schema})
                if resp.status_code in (200, 201):
                    log.info("registered", extra={"extra": {"subject": subject, "id": resp.json().get("id")}})
                    break
                log.warning("register failed", extra={"extra": {"subject": subject, "status": resp.status_code}})
            except httpx.HTTPError as exc:
                log.warning("registry unreachable", extra={"extra": {"error": str(exc), "attempt": attempt}})
            time.sleep(2)


def main() -> None:
    setup_logging("register-schemas")
    s = get_settings()
    ensure_topics(s.kafka_bootstrap)
    register(s.schema_registry_url, s.schema_dir)


if __name__ == "__main__":
    main()
