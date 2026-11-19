"""Poll the belt scale over Modbus TCP and publish canonical tags to plant.tags."""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from connectors.modbus_connector.decoding import Totalizer, decode, words_to_u32
from minehub_common.contracts.plant_tag import PlantTag
from minehub_common.kafka.producer import HubProducer
from minehub_common.logging import setup_logging
from minehub_common.metrics import LAST_MESSAGE_TS, MESSAGES_IN, RECONNECTS, start_metrics_server
from minehub_common.settings import get_settings

SERVICE = "modbus-connector"
TOPIC = "plant.tags"
log = logging.getLogger(SERVICE)


def main() -> None:
    setup_logging(SERVICE)
    s = get_settings()
    start_metrics_server(s.metrics_port)
    cfg = s.load_yaml("tags.yaml")["modbus"]
    producer = HubProducer(s.kafka_bootstrap, s.schema_registry_url, SERVICE)
    client = ModbusTcpClient(s.modbus_host, port=s.modbus_port, timeout=3)
    totals = {
        r["canonical"]: Totalizer(r["rollover"], r["scale"]) for r in cfg["registers"] if r.get("totalizer")
    }
    backoff = 1.0
    while True:
        if not client.connected and not client.connect():
            RECONNECTS.labels(SERVICE, "modbus").inc()
            log.warning("modbus not reachable", extra={"extra": {"retry_s": backoff}})
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        backoff = 1.0
        try:
            span = max(r["address"] for r in cfg["registers"]) + 2
            resp = client.read_holding_registers(0, count=span, slave=cfg["unit_id"])
            if resp.isError():
                raise ModbusException(str(resp))
            now = datetime.now(UTC)
            MESSAGES_IN.labels(SERVICE, "modbus").inc()
            LAST_MESSAGE_TS.labels(SERVICE, "modbus").set(time.time())
            for r in cfg["registers"]:
                words = resp.registers[r["address"] : r["address"] + 2]
                if r.get("totalizer"):
                    inc = totals[r["canonical"]].update(words_to_u32(words, cfg["word_order"]))
                    # publish the increment; the warehouse sums increments, which survives rollover
                    rec = PlantTag(tag=r["canonical"] + "_INC", ts=now, value=inc, source="modbus")
                else:
                    value = decode(words, r["type"], cfg["word_order"], r["scale"])
                    rec = PlantTag(tag=r["canonical"], ts=now, value=value, source="modbus")
                producer.send(TOPIC, rec.to_avro(), key=rec.tag)
        except (ModbusException, ConnectionError, OSError) as exc:
            log.warning("modbus read failed", extra={"extra": {"error": str(exc)}})
            client.close()
        time.sleep(cfg["poll_interval_s"])


if __name__ == "__main__":
    main()