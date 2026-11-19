"""Map vendor FMS JSON payloads to the canonical TruckTelemetry contract."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dateutil import parser as date_parser

from minehub_common.contracts.truck_telemetry import TruckTelemetry


def _parse_ts(raw: Any) -> datetime:
    if isinstance(raw, (int, float)):
        # assume ms if large
        ts = float(raw)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=UTC)
    if isinstance(raw, str):
        dt = date_parser.isoparse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    raise ValueError(f"unsupported timestamp: {raw!r}")


def map_vendor_message(payload: dict[str, Any]) -> TruckTelemetry:
    """Translate vendor field names into TruckTelemetry.

    Vendor fields (examples): equipmentId, lat/long (mine-grid metres), speedKph,
    payloadTons, engineOn, fuelLevelPct, msgId, timestamp.
    """
    truck_id = str(payload.get("equipmentId") or payload.get("truck_id") or "").strip()
    x = payload.get("lat", payload.get("x_m", payload.get("x")))
    y = payload.get("long", payload.get("y_m", payload.get("y")))
    if x is None or y is None:
        raise ValueError("missing position fields")
    try:
        x_m = float(x)
        y_m = float(y)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid position: {x!r},{y!r}") from exc

    speed = payload.get("speedKph", payload.get("speed_kmh", 0))
    payload_t = payload.get("payloadTons", payload.get("payload_t", 0))
    engine_on = payload.get("engineOn", payload.get("engine_on", True))
    fuel = payload.get("fuelLevelPct", payload.get("fuel_pct"))
    msg_id = payload.get("msgId") or payload.get("msg_id")
    ts_raw = payload.get("timestamp") or payload.get("ts")
    if ts_raw is None:
        raise ValueError("missing timestamp")

    kwargs: dict[str, Any] = {
        "ts": _parse_ts(ts_raw),
        "truck_id": truck_id,
        "x_m": x_m,
        "y_m": y_m,
        "speed_kmh": float(speed),
        "payload_t": float(payload_t),
        "engine_on": bool(engine_on),
    }
    if fuel is not None:
        kwargs["fuel_pct"] = float(fuel)
    if msg_id:
        kwargs["msg_id"] = str(msg_id)
    return TruckTelemetry(**kwargs)
