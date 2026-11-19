"""Load CMMS work order exports. CMMS codes PM/BD are mapped to PLANNED/UNPLANNED."""

import pandas as pd
from dagster import AssetExecutionContext, MaterializeResult, asset

from minehub_common.contracts.work_order import WorkOrder
from minehub_common.db.bulk import upsert_via_staging
from minehub_common.settings import get_settings
from minehub_common.shifts import ShiftCalendar
from orchestration.minehub_dagster.assets._loading import archive, latest, quarantine, validate_rows
from orchestration.minehub_dagster.resources import PostgresResource

TYPE_MAP = {"PM": "PLANNED", "BD": "UNPLANNED"}


@asset(group_name="batch", compute_kind="python", description="CMMS work orders (raw.work_orders)")
def raw_work_orders(context: AssetExecutionContext, postgres: PostgresResource) -> MaterializeResult:
    s = get_settings()
    path = latest(s.drop_dir, "*work_order*.csv")
    if path is None:
        return MaterializeResult(metadata={"rows": 0})
    tz = ShiftCalendar(s.load_yaml("site.yaml")).tz
    df = pd.read_csv(path, dtype=str).fillna("")
    records = []
    for r in df.to_dict("records"):
        records.append({
            "wo_number": r["WO Number"], "equipment_id": r["Asset"], "wo_type": TYPE_MAP.get(r["Type"], r["Type"]),
            "description": r["Description"],
            "opened_at": pd.Timestamp(r["Opened"]).tz_localize(tz).to_pydatetime() if r["Opened"] else None,
            "closed_at": pd.Timestamp(r["Closed"]).tz_localize(tz).to_pydatetime() if r["Closed"] else None,
            "downtime_hours": float(r["Downtime (h)"]) if r["Downtime (h)"] else None,
            "failure_code": r["Failure Code"] or None,
        })
    good, bad = validate_rows(records, WorkOrder)
    cols = ["wo_number", "equipment_id", "wo_type", "description", "opened_at", "closed_at", "downtime_hours",
            "failure_code"]
    with postgres.connect() as conn, conn.transaction():
        upsert_via_staging(conn, "raw.work_orders", cols, ["wo_number"],
                           [tuple(getattr(w, c) for c in cols) for w in good])
        quarantine(conn, f"cmms:{path.name}", bad)
    archive(path)
    return MaterializeResult(metadata={"file": path.name, "rows": len(good), "quarantined": len(bad)})