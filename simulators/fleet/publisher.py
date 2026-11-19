"""MQTT publisher that emits vendor-style (non-canonical) fleet JSON."""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import paho.mqtt.client as mqtt

log = logging.getLogger("fleet-publisher")


def to_vendor_payload(telem: dict[str, Any], ts: datetime | None = None) -> dict[str, Any]:
    """Map internal telemetry to a vendor FMS-style document."""
    when = ts or datetime.now(UTC)
    return {
        "equipmentId": telem["truck_id"],
        "timestamp": when.isoformat().replace("+00:00", "Z"),
        "lat": telem["x"],  # vendor mislabels mine-grid metres as lat/long
        "long": telem["y"],
        "speedKph": telem["speed_kmh"],
        "payloadTons": telem["payload_t"],
        "engineOn": telem["engine_on"],
        "fuelLevelPct": telem.get("fuel_pct"),
        "msgId": uuid4().hex,
        "cycleState": telem.get("state"),
    }


class FleetPublisher:
    def __init__(self, host: str, port: int, topic_prefix: str = "fleet/trucks") -> None:
        self.topic_prefix = topic_prefix.rstrip("/")
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-fleet-{uuid4().hex[:8]}")
        self._host = host
        self._port = port
        self._connected = False

    def connect(self, retries: int = 30, delay_s: float = 2.0) -> None:
        for attempt in range(1, retries + 1):
            try:
                self._client.connect(self._host, self._port, keepalive=60)
                self._client.loop_start()
                self._connected = True
                log.info("mqtt connected", extra={"extra": {"host": self._host, "port": self._port}})
                return
            except OSError as exc:
                log.warning(
                    "mqtt connect failed",
                    extra={"extra": {"attempt": attempt, "error": str(exc)}},
                )
                time.sleep(delay_s)
        raise ConnectionError(f"could not connect to mqtt://{self._host}:{self._port}")

    def publish(self, truck_id: str, payload: dict[str, Any]) -> None:
        topic = f"{self.topic_prefix}/{truck_id}"
        body = json.dumps(payload, default=str)
        self._client.publish(topic, body, qos=0)

    def close(self) -> None:
        if self._connected:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
