"""compression + retention policies

Revision ID: 0003
"""
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.execute("ALTER TABLE raw.truck_telemetry SET (timescaledb.compress, timescaledb.compress_segmentby = 'truck_id')")
    op.execute("SELECT add_compression_policy('raw.truck_telemetry', interval '7 days')")
    op.execute("SELECT add_retention_policy('raw.truck_telemetry', interval '365 days')")
    op.execute("ALTER TABLE raw.plant_tags SET (timescaledb.compress, timescaledb.compress_segmentby = 'tag')")
    op.execute("SELECT add_compression_policy('raw.plant_tags', interval '7 days')")
    op.execute("SELECT add_retention_policy('raw.plant_tags', interval '730 days')")


def downgrade() -> None:
    op.execute("SELECT remove_retention_policy('raw.plant_tags')")
    op.execute("SELECT remove_compression_policy('raw.plant_tags')")
    op.execute("SELECT remove_retention_policy('raw.truck_telemetry')")
    op.execute("SELECT remove_compression_policy('raw.truck_telemetry')")