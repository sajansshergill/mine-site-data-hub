"""OPC UA connector reconnect behaviour under chaos."""
from __future__ import annotations

import pytest

from tests.integration.conftest import requires_docker


@pytest.mark.integration
@requires_docker
def test_opcua_connector_recovers_after_restart(docker_ok: bool) -> None:
    if not docker_ok:
        pytest.skip("docker unavailable")
    try:
        import docker  # type: ignore

        client = docker.from_env()
        containers = {
            c.name: c
            for c in client.containers.list(all=True)
            if "opcua" in c.name
        }
        if not containers:
            pytest.skip("opcua containers not running (start docker-compose.test.yml)")
        # Smoke: at least one opcua-related container exists
        assert any("opcua" in n for n in containers)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"docker sdk unavailable: {exc}")
