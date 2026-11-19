"""CLI: build HTML + PDF shift report, optionally email it."""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import text
from sqlalchemy.engine import Engine

from minehub_common.db.engine import get_engine
from minehub_common.logging import setup_logging
from minehub_common.settings import get_settings
from minehub_common.units import pct
from reporting import charts, commentary, mailer

log = logging.getLogger("reporting")
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class DelayRow:
    reason: str
    hours: float


@dataclass
class FleetRow:
    equipment_id: str
    availability_pct: float | None
    utilization_pct: float | None
    operating_hours: float | None
    downtime_hours: float | None


def resolve_shift(engine: Engine, shift: str) -> str:
    if shift != "latest":
        return shift
    with engine.connect() as conn:
        sid = conn.execute(text("SELECT max(shift_id) FROM marts.fct_plan_vs_actual")).scalar()
    if not sid:
        raise SystemExit("no shifts found in marts.fct_plan_vs_actual")
    return str(sid)


def load_context(engine: Engine, shift_id: str) -> dict:
    settings = get_settings()
    site = settings.load_yaml("site.yaml")
    with engine.connect() as conn:
        pva = conn.execute(text("""
            SELECT location, material, planned_tonnes, actual_tonnes
            FROM marts.fct_plan_vs_actual WHERE shift_id = :s
            ORDER BY location, material"""), {"s": shift_id}).mappings().all()

        fleet = conn.execute(text("""
            SELECT equipment_id,
                   availability * 100 AS availability_pct,
                   utilization * 100 AS utilization_pct,
                   operating_hours,
                   downtime_hours
            FROM marts.fct_equipment_shift
            WHERE shift_id = :s AND equipment_class IN ('truck', 'shovel')
            ORDER BY equipment_id"""), {"s": shift_id}).mappings().all()

        delays = conn.execute(text("""
            SELECT coalesce(nullif(failure_code, ''), wo_type) AS reason,
                   coalesce(sum(downtime_hours), 0) AS hours
            FROM marts.fct_maintenance
            WHERE shift_id = :s
            GROUP BY 1 ORDER BY hours DESC LIMIT 8"""), {"s": shift_id}).mappings().all()

        dq = conn.execute(text("""
            SELECT check_name, severity, passed, failing_rows
            FROM ops.dq_results
            WHERE shift_id = :s OR shift_id IS NULL
            ORDER BY run_at DESC LIMIT 50"""), {"s": shift_id}).mappings().all()

        crusher_dt = conn.execute(text("""
            SELECT coalesce(sum(downtime_hours), 0)
            FROM marts.fct_equipment_shift
            WHERE shift_id = :s AND equipment_class = 'crusher'"""), {"s": shift_id}).scalar()

        loads = conn.execute(text("""
            SELECT count(*) FROM marts.fct_truck_cycle WHERE shift_id = :s
        """), {"s": shift_id}).scalar()

        truck_loads = conn.execute(text("""
            SELECT truck_id, count(*) AS loads
            FROM marts.fct_truck_cycle
            WHERE shift_id = :s
            GROUP BY truck_id
            ORDER BY truck_id"""), {"s": shift_id}).all()

    rows = []
    for r in pva:
        planned = float(r["planned_tonnes"] or 0)
        actual = float(r["actual_tonnes"] or 0)
        rows.append({
            "location": r["location"],
            "material": r["material"],
            "planned_tonnes": planned,
            "actual_tonnes": actual,
            "variance_t": actual - planned,
            "variance_pct": pct(actual - planned, planned),
        })
    total_planned = sum(r["planned_tonnes"] for r in rows)
    total_actual = sum(r["actual_tonnes"] for r in rows)
    compliance = pct(total_actual, total_planned)

    delay_rows = [DelayRow(reason=str(d["reason"]), hours=float(d["hours"] or 0)) for d in delays]
    fleet_rows = [FleetRow(**dict(f)) for f in fleet]
    dq_list = [dict(d) for d in dq]
    dq_failures = sum(1 for d in dq_list if not d.get("passed"))

    # Charts — aggregate plan/actual by location
    by_loc: dict[str, list[float]] = {}
    for r in rows:
        by_loc.setdefault(r["location"], [0.0, 0.0])
        by_loc[r["location"]][0] += r["planned_tonnes"]
        by_loc[r["location"]][1] += r["actual_tonnes"]
    locs = list(by_loc.keys())
    chart_pva = charts.plan_vs_actual_bar(locs, [by_loc[l][0] for l in locs], [by_loc[l][1] for l in locs]) if locs else ""
    chart_fleet = charts.fleet_loads_bar(
        [t[0] for t in truck_loads], [int(t[1]) for t in truck_loads]
    ) if truck_loads else ""
    chart_delays = charts.delay_pie(
        [d.reason for d in delay_rows], [d.hours for d in delay_rows]
    ) if delay_rows else ""

    top = delay_rows[0] if delay_rows else None
    notes = commentary.build_commentary(
        compliance_pct=compliance,
        crusher_downtime_h=float(crusher_dt or 0),
        crusher_nameplate_tph=float(site.get("crusher_nameplate_tph", 2200)),
        top_delay_reason=top.reason if top else None,
        top_delay_hours=top.hours if top else 0.0,
        dq_failures=dq_failures,
    )

    return {
        "site_name": site.get("site_name", "Mine Site"),
        "shift_id": shift_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rows": rows,
        "total_planned": total_planned,
        "total_actual": total_actual,
        "compliance_pct": compliance,
        "total_loads": int(loads or 0),
        "fleet": fleet_rows,
        "delays": delay_rows,
        "dq": dq_list,
        "commentary": notes,
        "chart_pva": chart_pva,
        "chart_fleet": chart_fleet,
        "chart_delays": chart_delays,
        "styles": (TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8"),
    }


def render_html(ctx: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env.get_template("shift_report.html").render(**ctx)


def write_pdf(html: str, out_path: Path) -> bool:
    try:
        from weasyprint import HTML
    except ImportError:
        log.warning("weasyprint not installed; skipping PDF (pip install 'mine-site-data-hub[pdf]')")
        return False
    HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(out_path)
    return True


def build(shift_id: str = "latest", out_dir: Path | None = None, email: bool = False) -> dict[str, str]:
    """Build HTML (+ PDF when weasyprint is available) for a shift. Used by Dagster and CLI."""
    settings = get_settings()
    engine = get_engine()
    resolved = resolve_shift(engine, shift_id)
    ctx = load_context(engine, resolved)
    html = render_html(ctx)

    dest = out_dir or settings.report_dir
    dest.mkdir(parents=True, exist_ok=True)
    html_path = dest / f"shift_report_{resolved}.html"
    pdf_path = dest / f"shift_report_{resolved}.pdf"
    html_path.write_text(html, encoding="utf-8")
    wrote_pdf = write_pdf(html, pdf_path)
    log.info("report written", extra={"extra": {"html": str(html_path), "pdf": str(pdf_path) if wrote_pdf else None}})

    if email:
        attachments = [pdf_path] if wrote_pdf else [html_path]
        mailer.send_report(
            subject=f"[{ctx['site_name']}] Shift report {resolved}",
            body_text=f"Attached: plan vs actual report for shift {resolved}.",
            attachments=attachments,
            settings=settings,
        )
    return {"shift_id": resolved, "html": str(html_path), "pdf": str(pdf_path) if wrote_pdf else ""}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate shift plan-vs-actual PDF report")
    parser.add_argument("--shift", default="latest", help="shift id or 'latest'")
    parser.add_argument("--email", action="store_true", help="send PDF via SMTP")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    setup_logging("reporting")
    paths = build(args.shift, out_dir=args.out_dir, email=args.email)
    print(f"wrote {paths['html']}")
    if paths["pdf"]:
        print(f"wrote {paths['pdf']}")


if __name__ == "__main__":
    main()
