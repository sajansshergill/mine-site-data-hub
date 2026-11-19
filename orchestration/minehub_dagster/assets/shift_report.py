"""Build the PDF/HTML shift report for the latest closed shift."""

from dagster import AssetExecutionContext, MaterializeResult, asset

from orchestration.minehub_dagster.assets.data_quality import data_quality_results
from orchestration.minehub_dagster.resources import PostgresResource, RedisResource


def _closed_shift_id(postgres: PostgresResource, redis: RedisResource) -> str | None:
    current = None
    try:
        current = redis.client().get("live:current_shift")
    except Exception:  # noqa: BLE001
        current = None
    with postgres.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT shift_id
            FROM marts.dim_shift
            WHERE (%s::text IS NULL OR shift_id <> %s)
              AND end_ts <= now()
            ORDER BY end_ts DESC NULLS LAST, shift_id DESC
            LIMIT 1
            """,
            (current, current),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            """
            SELECT max(shift_id) FROM marts.fct_plan_vs_actual
            WHERE (%s::text IS NULL OR shift_id <> %s)
            """,
            (current, current),
        )
        row = cur.fetchone()
        return row[0] if row else None


@asset(
    group_name="reporting",
    deps=[data_quality_results],
    compute_kind="python",
    description="End-of-shift report for the latest closed shift",
)
def shift_report(
    context: AssetExecutionContext,
    postgres: PostgresResource,
    redis: RedisResource,
) -> MaterializeResult:
    shift_id = _closed_shift_id(postgres, redis)
    if not shift_id:
        context.log.warning("no closed shift found for report")
        return MaterializeResult(metadata={"shift_id": None, "built": False})

    # Lazy import — reporting package may be filled independently.
    from reporting import shift_report as sr

    build_fn = getattr(sr, "build", None) or getattr(sr, "build_shift_report", None)
    if build_fn is None:
        raise RuntimeError("reporting.shift_report has no build() or build_shift_report()")

    try:
        out = build_fn(shift_id)
    except TypeError:
        out = build_fn(shift_id=shift_id)

    return MaterializeResult(
        metadata={
            "shift_id": shift_id,
            "built": True,
            "output": str(out) if out is not None else "",
        }
    )
