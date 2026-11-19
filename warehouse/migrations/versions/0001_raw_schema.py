"""raw schema + hypertables

Revision ID: 0001
"""
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE SCHEMA IF NOT EXISTS raw")
    op.execute("""
        CREATE TABLE raw.truck_telemetry (
            ts timestamptz NOT NULL,
            msg_id text NOT NULL,
            truck_id text NOT NULL,
            x_m double precision NOT NULL,
            y_m double precision NOT NULL,
            speed_kmh double precision NOT NULL,
            payload_t double precision NOT NULL,
            engine_on boolean NOT NULL,
            fuel_pct double precision,
            ingested_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (ts, msg_id)
        )""")
    op.execute("SELECT create_hypertable('raw.truck_telemetry', 'ts', chunk_time_interval => interval '1 day')")
    op.execute("CREATE INDEX ON raw.truck_telemetry (truck_id, ts DESC)")

    op.execute("""
        CREATE TABLE raw.plant_tags (
            ts timestamptz NOT NULL,
            tag text NOT NULL,
            source text NOT NULL,
            value double precision NOT NULL,
            quality text NOT NULL,
            ingested_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (ts, tag, source)
        )""")
    op.execute("SELECT create_hypertable('raw.plant_tags', 'ts', chunk_time_interval => interval '1 day')")
    op.execute("CREATE INDEX ON raw.plant_tags (tag, ts DESC)")

    op.execute("""
        CREATE TABLE raw.equipment_events (
            ts timestamptz NOT NULL,
            equipment_id text NOT NULL,
            status text NOT NULL,
            reason text,
            fault_code text,
            vendor text NOT NULL,
            raw_code text NOT NULL,
            ingested_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (ts, equipment_id, raw_code)
        )""")
    op.execute("SELECT create_hypertable('raw.equipment_events', 'ts', chunk_time_interval => interval '7 days')")

    op.execute("""
        CREATE TABLE raw.truck_cycles (
            cycle_id uuid PRIMARY KEY,
            truck_id text NOT NULL,
            shift_id text NOT NULL,
            load_start timestamptz NOT NULL,
            load_end timestamptz NOT NULL,
            dump_start timestamptz NOT NULL,
            dump_end timestamptz NOT NULL,
            source_location text NOT NULL,
            dest_location text NOT NULL,
            payload_t double precision NOT NULL,
            queue_load_s double precision NOT NULL,
            queue_dump_s double precision NOT NULL,
            haul_full_s double precision NOT NULL,
            haul_empty_s double precision NOT NULL,
            revision int NOT NULL DEFAULT 0,
            ingested_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX ON raw.truck_cycles (shift_id)")

    op.execute("""
        CREATE TABLE raw.mine_plan (
            shift_id text NOT NULL,
            location text NOT NULL,
            material text NOT NULL,
            planned_tonnes double precision NOT NULL,
            planned_grade_gpt double precision,
            planned_truck_hours double precision,
            plan_version text NOT NULL,
            loaded_at timestamptz NOT NULL DEFAULT now(),
            source_file text,
            PRIMARY KEY (shift_id, location, material, plan_version)
        )""")
    op.execute("""
        CREATE TABLE raw.work_orders (
            wo_number text PRIMARY KEY,
            equipment_id text NOT NULL,
            wo_type text NOT NULL,
            description text,
            opened_at timestamptz NOT NULL,
            closed_at timestamptz,
            downtime_hours double precision,
            failure_code text,
            loaded_at timestamptz NOT NULL DEFAULT now()
        )""")
    op.execute("""
        CREATE TABLE raw.assays (
            sample_id text PRIMARY KEY,
            location text NOT NULL,
            block_id text NOT NULL,
            sampled_on date NOT NULL,
            au_gpt double precision NOT NULL,
            tonnes_represented double precision NOT NULL,
            loaded_at timestamptz NOT NULL DEFAULT now()
        )""")


def downgrade() -> None:
    op.execute("DROP SCHEMA raw CASCADE")