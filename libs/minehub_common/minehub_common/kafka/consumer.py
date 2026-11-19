"""At-least-once Kafka consumer with manual commits."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from typing import Any

from confluent_kafka import Consumer, KafkaException, Message

from minehub_common.kafka.serde import AvroSerde

log = logging.getLogger("hub-consumer")


class HubConsumer:
    def __init__(
        self,
        bootstrap: str,
        group_id: str,
        topics: Iterable[str],
        registry_url: str,
        client_id: str | None = None,
    ) -> None:
        self._consumer = Consumer(
            {
                "bootstrap.servers": bootstrap,
                "group.id": group_id,
                "client.id": client_id or group_id,
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }
        )
        self._consumer.subscribe(list(topics))
        self.serde = AvroSerde(registry_url)

    def poll(self, timeout: float = 1.0) -> Message | None:
        return self._consumer.poll(timeout)

    def decode(self, msg: Message) -> dict[str, Any]:
        raw = msg.value()
        if raw is None:
            return {}
        if raw[:1] == b"\x00":
            return self.serde.decode(raw)
        return json.loads(raw)

    def commit(self, msg: Message | None = None, asynchronous: bool = False) -> None:
        self._consumer.commit(message=msg, asynchronous=asynchronous)

    def close(self) -> None:
        self._consumer.close()

    def run(self, handler: Callable[[Message, dict[str, Any]], None], stop_flag: Callable[[], bool] | None = None) -> None:
        try:
            while not (stop_flag and stop_flag()):
                msg = self.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    raise KafkaException(msg.error())
                try:
                    payload = self.decode(msg)
                    handler(msg, payload)
                    self.commit(msg)
                except Exception:  # noqa: BLE001
                    log.exception("handler failed", extra={"extra": {"topic": msg.topic(), "offset": msg.offset()}})
        finally:
            self.close()
