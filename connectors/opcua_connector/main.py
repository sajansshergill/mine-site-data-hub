"""OPC UA subscription connector → plant.tags with reconnect/backoff."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from asyncua import Client, Node, ua
from asyncua.common.subscription import DataChangeNotif

from connectors.opcua_connector.browser import verify_tags
from connectors.opcua_connector.quality import map_ua_status
from minehub_common.contracts.plant_tag import PlantTag
from minehub_common.kafka.producer import HubProducer
from minehub_common.logging import setup_logging
from minehub_common.metrics import LAST_MESSAGE_TS, MESSAGES_IN, RECONNECTS, start_metrics_server
from minehub_common.settings import get_settings

SERVICE = "opcua-connector"
TOPIC = "plant.tags"
log = logging.getLogger(SERVICE)


class TagHandler:
    def __init__(self, producer: HubProducer, node_to_canonical: dict[str, str]) -> None:
        self.producer = producer
        self.node_to_canonical = node_to_canonical

    def datachange_notification(self, node: Node, val: Any, data: DataChangeNotif) -> None:
        try:
            node_id = node.nodeid.to_string()
        except Exception:  # noqa: BLE001
            node_id = str(node)
        canonical = self.node_to_canonical.get(node_id)
        if canonical is None:
            # try suffix match (ns index may differ)
            for key, name in self.node_to_canonical.items():
                if key.endswith(node_id.split(";", 1)[-1]) or node_id.endswith(key.split(";", 1)[-1]):
                    canonical = name
                    break
        if canonical is None:
            log.debug("unmapped node", extra={"extra": {"node": node_id}})
            return

        quality = "GOOD"
        try:
            status = data.monitored_item.Value.StatusCode
            quality = map_ua_status(status)
        except Exception:  # noqa: BLE001
            quality = "UNCERTAIN"

        try:
            value = float(val) if val is not None else float("nan")
        except (TypeError, ValueError):
            value = 1.0 if bool(val) else 0.0

        MESSAGES_IN.labels(SERVICE, "opcua").inc()
        LAST_MESSAGE_TS.labels(SERVICE, "opcua").set(time.time())
        rec = PlantTag(tag=canonical, ts=datetime.now(UTC), value=value, source="opcua", quality=quality)
        self.producer.send(TOPIC, rec.to_avro(), key=rec.tag)


async def run_once(s: Any, producer: HubProducer) -> None:
    cfg = s.load_yaml("tags.yaml")["opcua"]
    tags = cfg["tags"]
    node_to_canonical = {t["node"]: t["canonical"] for t in tags}

    client = Client(url=s.opcua_endpoint)
    client.session_timeout = 60000
    await client.connect()
    try:
        missing = await verify_tags(client, tags)
        if missing:
            log.warning("some tags missing at connect", extra={"extra": {"missing": missing}})

        handler = TagHandler(producer, node_to_canonical)
        sub = await client.create_subscription(500, handler)
        nodes: list[Node] = []
        for tag in tags:
            try:
                nodes.append(client.get_node(tag["node"]))
            except Exception as exc:  # noqa: BLE001
                log.warning("cannot resolve node", extra={"extra": {"node": tag["node"], "error": str(exc)}})
        if not nodes:
            raise RuntimeError("no OPC UA nodes subscribed")
        await sub.subscribe_data_change(nodes)
        log.info("subscribed", extra={"extra": {"nodes": len(nodes), "endpoint": s.opcua_endpoint}})
        while True:
            await asyncio.sleep(1.0)
    finally:
        await client.disconnect()


async def main_async() -> None:
    setup_logging(SERVICE)
    s = get_settings()
    start_metrics_server(s.metrics_port)
    producer = HubProducer(s.kafka_bootstrap, s.schema_registry_url, SERVICE)
    backoff = 1.0
    while True:
        try:
            await run_once(s, producer)
            backoff = 1.0
        except (OSError, asyncio.TimeoutError, ua.UaError, ConnectionError, RuntimeError) as exc:
            RECONNECTS.labels(SERVICE, "opcua").inc()
            log.warning(
                "opcua session failed",
                extra={"extra": {"error": str(exc), "retry_s": backoff}},
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
