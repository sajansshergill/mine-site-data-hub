"""Unit helpers and safe percentage calculations."""
from __future__ import annotations


def pct(numerator: float, denominator: float) -> float | None:
    if denominator in (0, 0.0) or denominator is None:
        return None
    return 100.0 * float(numerator) / float(denominator)


def tph(tonnes: float, hours: float) -> float | None:
    if hours in (0, 0.0):
        return None
    return float(tonnes) / float(hours)


def kmh_to_ms(kmh: float) -> float:
    return float(kmh) / 3.6


def ms_to_kmh(ms: float) -> float:
    return float(ms) * 3.6
