"""Lua KPI registry, validation and execution."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from app.auth import require
from app.deps import db
from app.schemas.models import KpiInfo, KpiRunResult, KpiValidateRequest
from kpi_engine.data_bindings import gather
from kpi_engine.engine import latest_closed_shift, run_all
from kpi_engine.registry import load_definitions
from kpi_engine.sandbox import KpiError, run_kpi
from minehub_common.db.engine import get_engine
from minehub_common.settings import get_settings

router = APIRouter(tags=["kpis"])


def _defs() -> dict:
    return load_definitions(get_settings().config_dir / "kpis")


@router.get("/kpis", response_model=list[KpiInfo])
def list_kpis(_: str = Depends(require("viewer"))) -> list[KpiInfo]:
    return [
        KpiInfo(
            name=d.name,
            version=d.version,
            owner=d.owner,
            unit=d.unit,
            description=d.description,
            inputs=list(d.inputs),
            params=dict(d.params),
        )
        for d in _defs().values()
    ]


@router.post("/kpis/validate", response_model=KpiRunResult)
def validate_kpi(
    body: KpiValidateRequest,
    conn: Connection = Depends(db),
    _: str = Depends(require("engineer")),
) -> KpiRunResult:
    engine = get_engine()
    shift_id = latest_closed_shift(engine) if body.shift_id == "latest" else body.shift_id
    try:
        inputs = gather(conn, shift_id, body.inputs)
        value = run_kpi(body.lua, inputs, body.params)
        return KpiRunResult(name="validate", version=0, shift_id=shift_id, value=value, ok=True)
    except (KpiError, KeyError) as exc:
        return KpiRunResult(
            name="validate", version=0, shift_id=shift_id, value=None, ok=False, error=str(exc)
        )


@router.post("/kpis/{name}/run", response_model=KpiRunResult)
def run_kpi_endpoint(
    name: str,
    shift_id: str = "latest",
    _: str = Depends(require("engineer")),
) -> KpiRunResult:
    defs = _defs()
    if name not in defs:
        raise HTTPException(status_code=404, detail=f"unknown KPI {name}")
    engine = get_engine()
    sid = latest_closed_shift(engine) if shift_id == "latest" else shift_id
    results = run_all(engine, sid, only=name)
    if not results:
        raise HTTPException(status_code=500, detail="KPI run produced no result")
    r = results[0]
    return KpiRunResult(
        name=r.name,
        version=r.version,
        shift_id=r.shift_id,
        value=r.value,
        ok=r.ok,
        error=r.error,
        duration_ms=r.duration_ms,
    )
