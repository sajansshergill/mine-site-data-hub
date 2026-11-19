"""Subscribe to vendor MQTT fleet topics, validate, publish to fleet.telemetry."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from connectors.mqtt_connector.vendor_mapping import map_vendor_message
from minehub_common.kafka.producer import HubProducer
from minehub_common.logging import setup_logging
from minehub_common.metrics import LAST_MESSAGE_TS, MESSAGES_IN, RECONNECTS, VALIDATION_FAIL, start_metrics_server
from minehub_common.settings import get_settings

SERVICE = "mqtt-connector"
TOPIC = "fleet.telemetry"
log = logging.getLogger(SERVICE)


class MqttConnector:
    def __init__(self) -> None:
        self.s = get_settings()
        self.producer = HubProducer(self.s.kafka_bootstrap, self.s.schema_registry_url, SERVICE)
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=SERVICE)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._backoff = 1.0

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        del userdata, flags, properties
        if reason_code.is_failure if hasattr(reason_code, "is_failure") else int(reason_code) != 0:
            log.warning("mqtt connect refused", extra={"extra": {"rc": str(reason_code)}})
            return
        self._backoff = 1.0
        client.subscribe(self.s.mqtt_topic)
        log.info("subscribed", extra={"extra": {"topic": self.s.mqtt_topic}})

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, disconnect_flags: Any, reason_code: Any, properties: Any = None) -> None:
        del client, userdata, disconnect_flags, properties
        RECONNECTS.labels(SERVICE, "mqtt").inc()
        log.warning("mqtt disconnected", extra={"extra": {"rc": str(reason_code)}})

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        del client, userdata
        MESSAGES_IN.labels(SERVICE, "mqtt").inc()
        LAST_MESSAGE_TS.labels(SERVICE, "mqtt").set(time.time())
        raw_text = msg.payload.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_text)
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
            telem = map_vendor_message(payload)
            self.producer.send(TOPIC, telem.to_avro(), key=telem.truck_id)
        except (json.JSONDecodeError, ValueError, ValidationError, TypeError) as exc:
            reason = type(exc).__name__
            VALIDATION_FAIL.labels(SERVICE, reason).inc()
            log.warning("validation failed", extra={"extra": {"error": str(exc), "topic": msg.topic}})
            self.producer.send_dlq(TOPIC, {"mqtt_topic": msg.topic, "payload": raw_text}, reason=str(exc))

    def run(self) -> None:
        start_metrics_server(self.s.metrics_port)
        while True:
            try:
                self._client.connect(self.s.mqtt_host, self.s.mqtt_port, keepalive=60)
                self._client.loop_forever(retry_first_connection=True)
            except OSError as exc:
                RECONNECTS.labels(SERVICE, "mqtt").inc()
                log.warning(
                    "mqtt connect error",
                    extra={"extra": {"error": str(exc), "retry_s": self._backoff}},
                )
                time.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, 60.0)


def main() -> None:
    setup_logging(SERVICE)
    MqttConnector().run()


if __name__ == "__main__":
    main()
