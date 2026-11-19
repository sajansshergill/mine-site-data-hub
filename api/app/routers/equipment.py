"""Equipment KPIs from warehouse marts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth import require
from app.deps import db
from app.schemas.models import EquipmentKpis

router = APIRouter(tags=["equipment"])


@router.get("/equipment/{equipment_id}/kpis", response_model=EquipmentKpis)
def equipment_kpis(
    equipment_id: str,
    shift_id: str | None = Query(None, description="Defaults to latest shift for the unit"),
    conn: Connection = Depends(db),
    _: str = Depends(require("viewer")),
) -> EquipmentKpis:
    row = conn.execute(
        text("""
            SELECT e.shift_id,
                   e.availability * 100 AS availability_pct,
                   e.utilization * 100 AS utilization_pct,
                   e.operating_hours,
                   e.downtime_hours,
                   (
                     SELECT m.mtbf_hours FROM marts.fct_maintenance m
                     WHERE m.equipment_id = e.equipment_id
                     ORDER BY m.opened_at DESC NULLS LAST LIMIT 1
                   ) AS mtbf_hours,
                   (
                     SELECT m.mttr_hours FROM marts.fct_maintenance m
                     WHERE m.equipment_id = e.equipment_id
                     ORDER BY m.opened_at DESC NULLS LAST LIMIT 1
                   ) AS mttr_hours
            FROM marts.fct_equipment_shift e
            WHERE e.equipment_id = :eid
              AND (:sid IS NULL OR e.shift_id = :sid)
            ORDER BY e.shift_id DESC
            LIMIT 1
        """),
        {"eid": equipment_id, "sid": shift_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"no KPIs for equipment {equipment_id}")
    return EquipmentKpis(equipment_id=equipment_id, **dict(row))
