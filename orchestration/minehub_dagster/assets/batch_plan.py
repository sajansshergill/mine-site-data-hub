"""Load the shift-level mine plan XLSX from the drop folder."""

import pandas as pd
from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset

from minehub_common.contracts.plan_row import PlanRow
from minehub_common.db.bulk import upsert_via_staging
from minehub_common.settings import get_settings
from orchestration.minehub_dagster.assets._loading import archive, latest, quarantine, validate_rows
from orchestration.minehub_dagster.resources import PostgresResource

COLUMNS = {"Shift Date": "shift_date", "Shift": "shift_code", "Location": "location", "Material": "material",
           "Planned Tonnes": "planned_tonnes", "Planned Grade (g/t)": "planned_grade_gpt",
           "Planned Truck Hours": "planned_truck_hours", "Plan Version": "plan_version"}


@asset(group_name="batch", compute_kind="python", description="Mine plan rows (raw.mine_plan)")
def raw_mine_plan(context: AssetExecutionContext, postgres: PostgresResource) -> MaterializeResult:
    path = latest(get_settings().drop_dir, "*plan*.xlsx")
    if path is None:
        context.log.info("no plan file in drop folder")
        return MaterializeResult(metadata={"rows": 0})
    df = pd.read_excel(path, sheet_name="Shift Plan").rename(columns=COLUMNS)
    df = df.where(pd.notnull(df), None)
    df["shift_date"] = pd.to_datetime(df["shift_date"]).dt.date
    good, bad = validate_rows(df.to_dict("records"), PlanRow)
    cols = ["shift_id", "location", "material", "planned_tonnes", "planned_grade_gpt", "planned_truck_hours",
            "plan_version", "source_file"]
    rows = [(r.shift_id, r.location, r.material, r.planned_tonnes, r.planned_grade_gpt, r.planned_truck_hours,
             r.plan_version, path.name) for r in good]
    with postgres.connect() as conn, conn.transaction():
        upsert_via_staging(conn, "raw.mine_plan", cols, ["shift_id", "location", "material", "plan_version"], rows)
        quarantine(conn, f"plan:{path.name}", bad)
    archive(path)
    return MaterializeResult(metadata={"file": path.name, "rows": len(good), "quarantined": len(bad),
                                       "preview": MetadataValue.md(df.head(10).to_markdown())})