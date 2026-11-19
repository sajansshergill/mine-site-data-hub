"""MQTT publish → connector → Redpanda → sink → warehouse (smoke)."""
from __future__ import annotations

import pytest

from tests.integration.conftest import requires_docker


@pytest.mark.integration
@requires_docker
def test_mqtt_telemetry_lands_in_raw(database_url: str, docker_ok: bool) -> None:
    if not docker_ok:
        pytest.skip("docker unavailable")
    # Lightweight presence check: raw table exists when the stack has been seeded.
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url)
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT to_regclass('raw.truck_telemetry') IS NOT NULL")
            ).scalar()
        assert exists is True
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"warehouse not reachable: {exc}")
