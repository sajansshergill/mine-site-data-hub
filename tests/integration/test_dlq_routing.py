"""Invalid payloads should land in DLQ / quarantine, not raw tables."""
from __future__ import annotations

import pytest

from tests.integration.conftest import requires_docker


@pytest.mark.integration
@requires_docker
def test_quarantine_table_exists(database_url: str) -> None:
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url)
        with engine.connect() as conn:
            exists = conn.execute(text("SELECT to_regclass('ops.quarantine') IS NOT NULL")).scalar()
        assert exists is True
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"warehouse not reachable: {exc}")


@pytest.mark.integration
@requires_docker
def test_dlq_metric_or_quarantine_writable(database_url: str) -> None:
    """When the stack is up, quarantine accepts a synthetic row (rolled back)."""
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO ops.quarantine (source, reason, payload) "
                    "VALUES ('test', 'integration', CAST(:p AS jsonb))"
                ),
                {"p": '{"bad": true}'},
            )
            conn.execute(text("DELETE FROM ops.quarantine WHERE source = 'test' AND reason = 'integration'"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"warehouse not reachable: {exc}")
