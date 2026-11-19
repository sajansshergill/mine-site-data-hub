"""Data-quality results and quarantine browse."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth import require
from app.deps import db
from app.schemas.models import DqResult, QuarantineRow

router = APIRouter(tags=["data-quality"])


@router.get("/dq/results", response_model=list[DqResult])
def dq_results(
    shift_id: str | None = Query(None),
    failed_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    conn: Connection = Depends(db),
    _: str = Depends(require("viewer")),
) -> list[DqResult]:
    rows = conn.execute(
        text("""
            SELECT id, check_name, severity, passed, failing_rows, details, shift_id, run_at
            FROM ops.dq_results
            WHERE (:sid IS NULL OR shift_id = :sid)
              AND (NOT :failed_only OR passed = false)
            ORDER BY run_at DESC
            LIMIT :lim
        """),
        {"sid": shift_id, "failed_only": failed_only, "lim": limit},
    ).mappings().all()
    return [DqResult(**dict(r)) for r in rows]


@router.get("/dq/quarantine", response_model=list[QuarantineRow])
def dq_quarantine(
    source: str | None = Query(None),
    unresolved_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    conn: Connection = Depends(db),
    _: str = Depends(require("viewer")),
) -> list[QuarantineRow]:
    rows = conn.execute(
        text("""
            SELECT id, source, reason, payload, quarantined_at, resolved
            FROM ops.quarantine
            WHERE (:source IS NULL OR source = :source)
              AND (NOT :unresolved_only OR resolved = false)
            ORDER BY quarantined_at DESC
            LIMIT :lim
        """),
        {"source": source, "unresolved_only": unresolved_only, "lim": limit},
    ).mappings().all()
    return [QuarantineRow(**dict(r)) for r in rows]
