
import pandas as pd
from dagster import AssetExecutionContext, MaterializeResult, asset

from minehub_common.contracts.assay import Assay
from minehub_common.db.bulk import upsert_via_staging
from minehub_common.settings import get_settings
from orchestration.minehub_dagster.assets._loading import archive, latest, quarantine, validate_rows
from orchestration.minehub_dagster.resources import PostgresResource


@asset(group_name="batch", compute_kind="python", description="Grade control assays (raw.assays)")
def raw_assays(context: AssetExecutionContext, postgres: PostgresResource) -> MaterializeResult:
    path = latest(get_settings().drop_dir, "*assay*.csv")
    if path is None:
        return MaterializeResult(metadata={"rows": 0})
    df = pd.read_csv(path)
    df["sampled_on"] = pd.to_datetime(df["sampled_on"]).dt.date
    good, bad = validate_rows(df.to_dict("records"), Assay)
    cols = ["sample_id", "location", "block_id", "sampled_on", "au_gpt", "tonnes_represented"]
    with postgres.connect() as conn, conn.transaction():
        upsert_via_staging(conn, "raw.assays", cols, ["sample_id"], [tuple(getattr(a, c) for c in cols) for a in good])
        quarantine(conn, f"lab:{path.name}", bad)
    archive(path)
    return MaterializeResult(metadata={"file": path.name, "rows": len(good), "quarantined": len(bad)})