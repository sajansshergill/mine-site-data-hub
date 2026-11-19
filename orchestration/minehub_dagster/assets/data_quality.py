"""Scheduled / end-of-shift data-quality checks written to ops.dq_results."""

import json
from datetime import UTC, datetime

from dagster import AssetExecutionContext, MaterializeResult, asset

from orchestration.minehub_dagster.resources import PostgresResource

CHECKS: list[tuple[str, str, str]] = [
    (
        "stale_tags",
        "warning",
        """
        SELECT count(*)::int FROM (
            SELECT tag FROM raw.plant_tags
            GROUP BY tag
            HAVING max(ts) < now() - interval '10 minutes'
        ) s
        """,
    ),
    (
        "missing_shifts",
        "critical",
        """
        SELECT count(*)::int FROM (
            SELECT p.shift_id
            FROM raw.mine_plan p
            LEFT JOIN marts.fct_plan_vs_actual a ON a.shift_id = p.shift_id
            WHERE a.shift_id IS NULL
            GROUP BY p.shift_id
        ) s
        """,
    ),
    (
        "quarantine_growth",
        "warning",
        """
        SELECT count(*)::int FROM ops.quarantine
        WHERE resolved = false
          AND quarantined_at > now() - interval '24 hours'
        """,
    ),
]


@asset(
    group_name="quality",
    compute_kind="sql",
    description="Run warehouse DQ checks and insert into ops.dq_results",
)
def data_quality_results(context: AssetExecutionContext, postgres: PostgresResource) -> MaterializeResult:
    results: list[dict] = []
    with postgres.connect() as conn, conn.transaction():
        with conn.cursor() as cur:
            for name, severity, sql in CHECKS:
                try:
                    cur.execute(sql)
                    failing = int(cur.fetchone()[0] or 0)
                    threshold = 50 if name == "quarantine_growth" else 0
                    passed = failing <= threshold
                    details = {"failing_rows": failing, "threshold": threshold}
                    cur.execute(
                        """
                        INSERT INTO ops.dq_results
                            (check_name, severity, passed, failing_rows, details, run_at)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        (name, severity, passed, failing, json.dumps(details), datetime.now(UTC)),
                    )
                    results.append({"check": name, "passed": passed, "failing_rows": failing})
                except Exception as exc:  # noqa: BLE001 — record check failure, continue
                    context.log.exception("dq check %s failed", name)
                    cur.execute(
                        """
                        INSERT INTO ops.dq_results
                            (check_name, severity, passed, failing_rows, details, run_at)
                        VALUES (%s, %s, false, -1, %s::jsonb, %s)
                        """,
                        (name, severity, json.dumps({"error": str(exc)}), datetime.now(UTC)),
                    )
                    results.append({"check": name, "passed": False, "error": str(exc)})
    return MaterializeResult(metadata={"checks": len(results), "results": results})
