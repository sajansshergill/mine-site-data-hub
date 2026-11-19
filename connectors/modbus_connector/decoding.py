"""Register decoding: word order, 32-bit types, and totalizer rollover."""
from __future__ import annotations

import struct


def words_to_u32(words: list[int], word_order: str = "little") -> int:
    lo, hi = (words[0], words[1]) if word_order == "little" else (words[1], words[0])
    return (hi << 16) | lo


def words_to_f32(words: list[int], word_order: str = "little") -> float:
    lo, hi = (words[0], words[1]) if word_order == "little" else (words[1], words[0])
    return struct.unpack(">f", struct.pack(">HH", hi, lo))[0]


def decode(words: list[int], typ: str, word_order: str, scale: float) -> float:
    if typ == "uint32":
        return words_to_u32(words, word_order) * scale
    if typ == "float32":
        return words_to_f32(words, word_order) * scale
    if typ == "uint16":
        return words[0] * scale
    raise ValueError(f"unsupported register type {typ}")


class Totalizer:
    """Turns a raw counter that rolls over into a monotonic running total."""

    def __init__(self, rollover_raw: int, scale: float) -> None:
        self.rollover = rollover_raw
        self.scale = scale
        self.last_raw: int | None = None
        self.accumulated = 0.0

    def update(self, raw: int) -> float:
        """Return the increment (in engineering units) since the last reading."""
        if self.last_raw is None:
            self.last_raw = raw
            return 0.0
        delta = raw - self.last_raw
        if delta < 0:  # rolled over (or the PLC was reset)
            delta = (self.rollover - self.last_raw) + raw + 1
            if delta * self.scale > 1000:  # implausible jump -> treat as reset, not rollover
                delta = raw
        self.last_raw = raw
        inc = delta * self.scale
        self.accumulated += inc
        return inc