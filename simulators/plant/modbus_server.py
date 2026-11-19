"""Modbus TCP belt-scale simulator: totalizer + rate + speed holding registers."""
from __future__ import annotations

import logging
import math
import random
import struct
import threading
import time

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer

from minehub_common.logging import setup_logging
from minehub_common.settings import get_settings

SERVICE = "sim-plant-modbus"
log = logging.getLogger(SERVICE)


def _f32_to_words(value: float, word_order: str) -> tuple[int, int]:
    hi, lo = struct.unpack(">HH", struct.pack(">f", float(value)))
    return (lo, hi) if word_order == "little" else (hi, lo)


def _u32_to_words(value: int, word_order: str) -> tuple[int, int]:
    value = int(value) & 0xFFFFFFFF
    lo, hi = value & 0xFFFF, (value >> 16) & 0xFFFF
    return (lo, hi) if word_order == "little" else (hi, lo)


class BeltScaleState:
    def __init__(self, word_order: str, scale: float = 0.1) -> None:
        self.word_order = word_order
        self.scale = scale
        self.raw_total = 0  # engineering tonnes / scale
        self.rate_tph = 1400.0
        self.speed_ms = 2.4
        self._lock = threading.Lock()
        self.rng = random.Random(11)

    def tick(self, dt_s: float) -> None:
        with self._lock:
            self.rate_tph = max(0.0, 1400.0 + 80.0 * math.sin(time.time() / 45.0) + self.rng.gauss(0, 15))
            self.speed_ms = max(0.5, 2.4 + 0.1 * math.sin(time.time() / 30.0) + self.rng.gauss(0, 0.02))
            tonnes = self.rate_tph * (dt_s / 3600.0)
            self.raw_total = (self.raw_total + int(round(tonnes / self.scale))) & 0xFFFFFFFF

    def registers(self) -> list[int]:
        with self._lock:
            t0, t1 = _u32_to_words(self.raw_total, self.word_order)
            r0, r1 = _f32_to_words(self.rate_tph, self.word_order)
            s0, s1 = _f32_to_words(self.speed_ms, self.word_order)
            return [t0, t1, r0, r1, s0, s1]


def main() -> None:
    setup_logging(SERVICE)
    s = get_settings()
    cfg = s.load_yaml("tags.yaml")["modbus"]
    word_order = cfg.get("word_order", "little")
    unit_id = int(cfg.get("unit_id", 1))
    scale = 0.1
    for reg in cfg.get("registers", []):
        if reg.get("totalizer"):
            scale = float(reg.get("scale", 0.1))
            break

    state = BeltScaleState(word_order=word_order, scale=scale)
    block = ModbusSequentialDataBlock(0, [0] * 16)
    store = ModbusSlaveContext(hr=block, zero_mode=True)
    context = ModbusServerContext(slaves={unit_id: store}, single=False)

    def updater() -> None:
        dt = 1.0
        while True:
            state.tick(dt / max(s.sim_speed, 0.01))
            regs = state.registers()
            store.setValues(3, 0, regs)  # holding registers
            time.sleep(dt / max(s.sim_speed, 0.01))

    threading.Thread(target=updater, daemon=True).start()
    host = "0.0.0.0"
    port = s.modbus_port
    log.info("modbus server starting", extra={"extra": {"host": host, "port": port, "unit_id": unit_id}})
    StartTcpServer(context=context, address=(host, port))


if __name__ == "__main__":
    main()
