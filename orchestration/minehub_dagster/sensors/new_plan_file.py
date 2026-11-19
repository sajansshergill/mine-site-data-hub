"""Watch the drop folder and materialize batch load assets when files arrive."""

from pathlib import Path

from dagster import (
    AssetSelection,
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SensorResult,
    define_asset_job,
    sensor,
)

from minehub_common.settings import get_settings

batch_load_job = define_asset_job(
    "batch_load_job",
    selection=AssetSelection.groups("batch"),
)

_PATTERNS = ("*plan*.xlsx", "*work_order*.csv", "*assay*.csv")


@sensor(
    job=batch_load_job,
    minimum_interval_seconds=30,
    default_status=DefaultSensorStatus.RUNNING,
    description="Trigger batch loads when new plan/CMMS/assay files land in drop_dir",
)
def new_drop_file(context: SensorEvaluationContext) -> SensorResult:
    drop_dir = Path(get_settings().drop_dir)
    drop_dir.mkdir(parents=True, exist_ok=True)

    try:
        last_mtime = float(context.cursor) if context.cursor else 0.0
    except (TypeError, ValueError):
        last_mtime = 0.0

    newest = last_mtime
    found: list[str] = []
    for pattern in _PATTERNS:
        for path in drop_dir.glob(pattern):
            mtime = path.stat().st_mtime
            if mtime > last_mtime:
                found.append(path.name)
                newest = max(newest, mtime)

    if not found:
        return SensorResult(cursor=str(newest))

    return SensorResult(
        run_requests=[
            RunRequest(
                run_key=f"drop-{newest}-{'-'.join(sorted(found))}",
                tags={"drop_files": ",".join(sorted(found))},
            )
        ],
        cursor=str(newest),
    )
