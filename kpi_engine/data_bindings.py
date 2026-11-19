"""Read-only shift data exposed to Lua KPIs. Each binding is one named input."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

Binding = Callable[[Connection, str], Any]


def tonnes_by_material(conn: Connection, shift_id: str) -> dict[str, float]:
    rows = conn.execute(text("""
        SELECT material, sum(actual_tonnes) FROM marts.fct_plan_vs_actual
        WHERE shift_id = :s GROUP BY material"""), {"s": shift_id}).all()
    return {m: float(t or 0) for m, t in rows}


def total_tonnes(conn: Connection, shift_id: str) -> float:
    v = conn.execute(text("SELECT coalesce(sum(payload_t), 0) FROM marts.fct_truck_cycle WHERE shift_id = :s"),
                     {"s": shift_id}).scalar()
    return float(v or 0)


def truck_operating_hours(conn: Connection, shift_id: str) -> dict[str, float]:
    rows = conn.execute(text("""
        SELECT equipment_id, operating_hours FROM marts.fct_equipment_shift
        WHERE shift_id = :s AND equipment_class = 'truck'"""), {"s": shift_id}).all()
    return {e: float(h or 0) for e, h in rows}


def shovel_idle_minutes(conn: Connection, shift_id: str) -> dict[str, float]:
    rows = conn.execute(text("""
        SELECT equipment_id, standby_hours * 60 FROM marts.fct_equipment_shift
        WHERE shift_id = :s AND equipment_class = 'shovel'"""), {"s": shift_id}).all()
    return {e: float(m or 0) for e, m in rows}


BINDINGS: dict[str, Binding] = {
    "tonnes_by_material": tonnes_by_material,
    "total_tonnes": total_tonnes,
    "truck_operating_hours": truck_operating_hours,
    "shovel_idle_minutes": shovel_idle_minutes,
}


def gather(conn: Connection, shift_id: str, names: list[str]) -> dict[str, Any]:
    missing = [n for n in names if n not in BINDINGS]
    if missing:
        raise KeyError(f"unknown KPI inputs: {missing}")
    return {n: BINDINGS[n](conn, shift_id) for n in names}