from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.schemas.models import PlanVsActual, PlanVsActualRow, ShiftSummary
from minehub_common.units import pct


def list_shifts(conn: Connection, limit: int) -> list[ShiftSummary]:
    rows = conn.execute(text("""
        SELECT shift_id, sum(planned_tonnes), sum(actual_tonnes)
        FROM marts.fct_plan_vs_actual GROUP BY shift_id ORDER BY shift_id DESC LIMIT :l"""), {"l": limit}).all()
    return [ShiftSummary(shift_id=s, planned_tonnes=p or 0, actual_tonnes=a or 0, compliance_pct=pct(a or 0, p or 0))
            for s, p, a in rows]


def plan_vs_actual(conn: Connection, shift_id: str) -> PlanVsActual | None:
    rows = conn.execute(text("""
        SELECT location, material, planned_tonnes, actual_tonnes
        FROM marts.fct_plan_vs_actual WHERE shift_id = :s ORDER BY location, material"""), {"s": shift_id}).all()
    if not rows:
        return None
    out = [PlanVsActualRow(location=l, material=m, planned_tonnes=p or 0, actual_tonnes=a or 0,
                           variance_t=(a or 0) - (p or 0), variance_pct=pct((a or 0) - (p or 0), p or 0))
           for l, m, p, a in rows]
    tp, ta = sum(r.planned_tonnes for r in out), sum(r.actual_tonnes for r in out)
    return PlanVsActual(shift_id=shift_id, rows=out, total_planned=tp, total_actual=ta, compliance_pct=pct(ta, tp))