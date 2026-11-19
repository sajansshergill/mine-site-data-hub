"""Work-order listing with filters."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth import require
from app.deps import db
from app.schemas.models import WorkOrderOut

router = APIRouter(tags=["maintenance"])


@router.get("/maintenance/work-orders", response_model=list[WorkOrderOut])
def list_work_orders(
    equipment_id: str | None = Query(None),
    wo_type: str | None = Query(None, description="PLANNED or UNPLANNED"),
    open_only: bool = Query(False),
    since: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    conn: Connection = Depends(db),
    _: str = Depends(require("viewer")),
) -> list[WorkOrderOut]:
    rows = conn.execute(
        text("""
            SELECT wo_number, equipment_id, wo_type, description,
                   opened_at, closed_at, downtime_hours, failure_code
            FROM raw.work_orders
            WHERE (:eid IS NULL OR equipment_id = :eid)
              AND (:wotype IS NULL OR wo_type = :wotype)
              AND (NOT :open_only OR closed_at IS NULL)
              AND (:since IS NULL OR opened_at >= :since)
            ORDER BY opened_at DESC
            LIMIT :lim
        """),
        {
            "eid": equipment_id,
            "wotype": wo_type,
            "open_only": open_only,
            "since": since,
            "lim": limit,
        },
    ).mappings().all()
    return [WorkOrderOut(**dict(r)) for r in rows]
