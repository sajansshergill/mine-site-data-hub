"""Map OPC UA status codes to canonical GOOD / UNCERTAIN / BAD."""
from __future__ import annotations

from typing import Literal

Quality = Literal["GOOD", "UNCERTAIN", "BAD"]

# asyncua / OPC UA StatusCode bit classes
# Good: 0x00000000 - 0x3FFFFFFF, Uncertain: 0x40000000 - 0x7FFFFFFF, Bad: 0x80000000+


def map_quality(status_code: int | None) -> Quality:
    if status_code is None:
        return "BAD"
    code = int(status_code) & 0xFFFFFFFF
    severity = code >> 30
    if severity == 0:
        return "GOOD"
    if severity == 1:
        return "UNCERTAIN"
    return "BAD"


def map_ua_status(status: object) -> Quality:
    """Accept asyncua StatusCode / DataValue.status or raw int."""
    if status is None:
        return "BAD"
    if hasattr(status, "value"):
        return map_quality(int(status.value))
    if hasattr(status, "is_good") and callable(status.is_good):
        if status.is_good():
            return "GOOD"
        if hasattr(status, "is_uncertain") and status.is_uncertain():
            return "UNCERTAIN"
        return "BAD"
    try:
        return map_quality(int(status))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "BAD"
