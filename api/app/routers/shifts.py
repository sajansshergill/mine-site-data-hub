"""Shift listing and plan-vs-actual reconciliation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.engine import Connection

from app.auth import require
from app.deps import db
from app.schemas.models import PlanVsActual, ShiftSummary
from app.services import reconciliation

router = APIRouter(tags=["shifts"])


@router.get("/shifts", response_model=list[ShiftSummary])
def list_shifts(
    limit: int = Query(20, ge=1, le=200),
    conn: Connection = Depends(db),
    _: str = Depends(require("viewer")),
) -> list[ShiftSummary]:
    return reconciliation.list_shifts(conn, limit)


@router.get("/shifts/{shift_id}/plan-vs-actual", response_model=PlanVsActual)
def get_plan_vs_actual(
    shift_id: str,
    conn: Connection = Depends(db),
    _: str = Depends(require("viewer")),
) -> PlanVsActual:
    result = reconciliation.plan_vs_actual(conn, shift_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"no plan-vs-actual for shift {shift_id}")
    return result
