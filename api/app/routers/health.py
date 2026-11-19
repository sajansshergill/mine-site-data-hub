from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.deps import db, redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health(conn: Connection = Depends(db)) -> JSONResponse:
    checks = {}
    try:
        conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"
    try:
        redis_client().ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse({"status": "ok" if healthy else "degraded", "checks": checks}, status_code=200 if healthy else 503)