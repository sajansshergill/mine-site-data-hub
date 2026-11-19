"""ops schema: offsets, quarantine, data-quality results, KPI runs

Revision ID: 0002
"""
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ops")
    op.execute("""
        CREATE TABLE ops.ingest_offsets (
            consumer_group text NOT NULL,
            topic text NOT NULL,
            partition int NOT NULL,
            next_offset bigint NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (consumer_group, topic, partition)
        )""")
    op.execute("""
        CREATE TABLE ops.quarantine (
            id bigserial PRIMARY KEY,
            source text NOT NULL,
            reason text NOT NULL,
            payload jsonb NOT NULL,
            quarantined_at timestamptz NOT NULL DEFAULT now(),
            resolved boolean NOT NULL DEFAULT false
        )""")
    op.execute("CREATE INDEX ON ops.quarantine (source, quarantined_at DESC)")
    op.execute("""
        CREATE TABLE ops.dq_results (
            id bigserial PRIMARY KEY,
            check_name text NOT NULL,
            severity text NOT NULL CHECK (severity IN ('critical', 'warning')),
            passed boolean NOT NULL,
            failing_rows int NOT NULL DEFAULT 0,
            details jsonb,
            shift_id text,
            run_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX ON ops.dq_results (run_at DESC)")
    op.execute("""
        CREATE TABLE ops.kpi_runs (
            id bigserial PRIMARY KEY,
            kpi_name text NOT NULL,
            kpi_version int NOT NULL,
            shift_id text NOT NULL,
            value double precision,
            ok boolean NOT NULL,
            error text,
            duration_ms double precision NOT NULL,
            run_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (kpi_name, kpi_version, shift_id)
        )""")


def downgrade() -> None:
    op.execute("DROP SCHEMA ops CASCADE")