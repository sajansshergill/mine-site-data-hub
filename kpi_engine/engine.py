"""Evaluate all registered KPIs for a shift and store results in ops.kpi_runs."""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

from kpi_engine.data_bindings import gather
from kpi_engine.registry import KpiDefinition, load_definitions
from kpi_engine.sandbox import KpiError, run_kpi
from minehub_common.db.engine import get_engine
from minehub_common.logging import setup_logging
from minehub_common.settings import get_settings

log = logging.getLogger("kpi-engine")


@dataclass
class KpiResult:
    name: str
    version: int
    shift_id: str
    value: float | None
    ok: bool
    error: str | None
    duration_ms: float


def evaluate(defn: KpiDefinition, inputs: dict, shift_id: str) -> KpiResult:
    started = time.perf_counter()
    try:
        value, ok, err = run_kpi(defn.lua, inputs, defn.params), True, None
    except KpiError as exc:
        value, ok, err = None, False, str(exc)
    return KpiResult(defn.name, defn.version, shift_id, value, ok, err, (time.perf_counter() - started) * 1000)


def run_all(engine: Engine, shift_id: str, only: str | None = None) -> list[KpiResult]:
    defs = load_definitions(get_settings().config_dir / "kpis")
    results = []
    with engine.begin() as conn:
        for name, d in defs.items():
            if only and name != only:
                continue
            try:
                inputs = gather(conn, shift_id, d.inputs)
                r = evaluate(d, inputs, shift_id)
            except KeyError as exc:
                r = KpiResult(d.name, d.version, shift_id, None, False, str(exc), 0.0)
            conn.execute(text("""
                INSERT INTO ops.kpi_runs (kpi_name, kpi_version, shift_id, value, ok, error, duration_ms)
                VALUES (:n, :v, :s, :val, :ok, :err, :ms)
                ON CONFLICT (kpi_name, kpi_version, shift_id)
                DO UPDATE SET value = EXCLUDED.value, ok = EXCLUDED.ok, error = EXCLUDED.error,
                              duration_ms = EXCLUDED.duration_ms, run_at = now()"""),
                dict(n=r.name, v=r.version, s=r.shift_id, val=r.value, ok=r.ok, err=r.error, ms=r.duration_ms))
            results.append(r)
            log.info("kpi evaluated", extra={"extra": r.__dict__})
    return results


def latest_closed_shift(engine: Engine) -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT max(shift_id) FROM marts.fct_plan_vs_actual")).scalar_one()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--shift", default="latest")
    p.add_argument("--kpi")
    a = p.parse_args()
    setup_logging("kpi-engine")
    engine = get_engine()
    shift_id = latest_closed_shift(engine) if a.shift == "latest" else a.shift
    for r in run_all(engine, shift_id, a.kpi):
        print(f"{r.name} v{r.version} [{shift_id}] = {r.value} {'' if r.ok else 'ERROR: ' + str(r.error)}")


if __name__ == "__main__":
    main()