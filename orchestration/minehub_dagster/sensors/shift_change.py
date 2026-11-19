"""Fire end-of-shift job when Redis live:current_shift rolls over."""

from dagster import (
    AssetKey,
    AssetSelection,
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SensorResult,
    define_asset_job,
    sensor,
)

from orchestration.minehub_dagster.resources import RedisResource

end_of_shift_job = define_asset_job(
    "end_of_shift_job",
    selection=(
        AssetSelection.groups("warehouse")
        | AssetSelection.groups("quality")
        | AssetSelection.assets(AssetKey("shift_report"))
    ),
)


@sensor(
    job=end_of_shift_job,
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.RUNNING,
    description="When live:current_shift changes, run dbt + DQ + shift report",
)
def shift_closed(context: SensorEvaluationContext, redis: RedisResource) -> SensorResult | None:
    client = redis.client()
    current = client.get("live:current_shift")
    previous = context.cursor or None

    if current is None:
        return None

    if previous is None:
        # First observation — seed cursor without running.
        return SensorResult(cursor=current)

    if current == previous:
        return None

    # Shift rolled: `previous` just closed.
    return SensorResult(
        run_requests=[
            RunRequest(
                run_key=f"shift-closed-{previous}-to-{current}",
                tags={"closed_shift": previous, "new_shift": current},
            )
        ],
        cursor=current,
    )
