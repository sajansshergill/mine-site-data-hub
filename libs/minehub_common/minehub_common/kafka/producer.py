"""Idempotent Kafka producer with Avro encoding and DLQ routing."""
from __future__ import annotations

import json
import logging
from typing import Any

from confluent_kafka import Producer

from minehub_common.kafka.serde import AvroSerde
from minehub_common.metrics import DLQ_TOTAL, MESSAGES_OUT
from minehub_common.settings import get_settings

log = logging.getLogger("hub-producer")


class HubProducer:
    def __init__(self, bootstrap: str, registry_url: str, client_id: str) -> None:
        self.client_id = client_id
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap,
                "client.id": client_id,
                "enable.idempotence": True,
                "acks": "all",
                "retries": 5,
                "linger.ms": 20,
            }
        )
        self.serde = AvroSerde(registry_url, get_settings().schema_dir)
        self._json_fallback = True

    def send(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        payload = self._encode(topic, value)
        self._producer.produce(topic, value=payload, key=key.encode() if key else None, on_delivery=self._on_delivery)
        self._producer.poll(0)
        MESSAGES_OUT.labels(self.client_id, topic).inc()

    def send_dlq(self, topic: str, raw: Any, reason: str) -> None:
        dlq = f"{topic}.dlq"
        body = json.dumps({"reason": reason, "payload": raw}, default=str).encode()
        self._producer.produce(dlq, value=body)
        self._producer.poll(0)
        DLQ_TOTAL.labels(self.client_id, dlq).inc()

    def flush(self, timeout: float = 10.0) -> None:
        self._producer.flush(timeout)

    def _encode(self, topic: str, value: dict[str, Any]) -> bytes:
        subject = f"{topic}-value"
        try:
            schema_path = get_settings().schema_dir / f"{topic.split('.')[-1] if False else ''}"
            # Prefer JSON for local/dev when schemas are not yet registered; try Avro first.
            return self.serde.encode(subject, value)
        except Exception:  # noqa: BLE001
            if self._json_fallback:
                return json.dumps(value, default=str).encode()
            raise

    @staticmethod
    def _on_delivery(err: Any, msg: Any) -> None:  # noqa: ANN401
        if err is not None:
            log.error("delivery failed", extra={"extra": {"error": str(err), "topic": msg.topic()}})
