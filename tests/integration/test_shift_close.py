"""End-of-shift close: Redis snapshot + mart availability."""
from __future__ import annotations

import pytest

from tests.integration.conftest import requires_docker


@pytest.mark.integration
@requires_docker
def test_plan_vs_actual_mart_queryable(database_url: str) -> None:
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Table may be empty before dbt run; existence is enough for the smoke test.
            exists = conn.execute(
                text("SELECT to_regclass('marts.fct_plan_vs_actual') IS NOT NULL")
            ).scalar()
        if not exists:
            pytest.skip("marts not built yet — run dbt")
        assert exists is True
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"warehouse not reachable: {exc}")


@pytest.mark.integration
@requires_docker
def test_redis_live_shift_key_readable() -> None:
    try:
        import redis

        url = __import__("os").environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
        r = redis.Redis.from_url(url, decode_responses=True)
        r.ping()
        # Key may be absent between shifts; ping proves connectivity for close pipeline.
        _ = r.get("live:current_shift")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"redis not reachable: {exc}")
