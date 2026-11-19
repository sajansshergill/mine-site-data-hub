"""1-minute and 1-hour plant tag rollups

Revision ID: 0004
"""
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    for name, bucket, offset in (("plant_tags_1m", "1 minute", "1 hour"), ("plant_tags_1h", "1 hour", "3 days")):
        op.execute(f"""
            CREATE MATERIALIZED VIEW raw.{name} WITH (timescaledb.continuous) AS
            SELECT time_bucket('{bucket}', ts) AS bucket, tag,
                   avg(value) AS avg_value, min(value) AS min_value, max(value) AS max_value,
                   count(*) AS samples,
                   count(*) FILTER (WHERE quality <> 'GOOD') AS bad_samples
            FROM raw.plant_tags GROUP BY 1, 2 WITH NO DATA""")
        op.execute(f"""SELECT add_continuous_aggregate_policy('raw.{name}',
            start_offset => interval '{offset}', end_offset => interval '{bucket}',
            schedule_interval => interval '{bucket}')""")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS raw.plant_tags_1h")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS raw.plant_tags_1m")