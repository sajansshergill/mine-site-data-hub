"""Integration test fixtures.

Prefer lightweight skips when Docker is unavailable. Full testcontainers
wiring can be layered on later without changing test signatures.
"""
from __future__ import annotations

import os
import shutil
import socket

import pytest


def _docker_available() -> bool:
    if os.environ.get("MINEHUB_FORCE_INTEGRATION") == "1":
        return True
    if shutil.which("docker") is None:
        return False
    try:
        import docker  # type: ignore

        client = docker.from_env()
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        # Fall back to a cheap daemon socket probe
        sock_path = os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")
        if sock_path.startswith("unix://"):
            path = sock_path.removeprefix("unix://")
            return os.path.exists(path)
        return False


DOCKER_AVAILABLE = _docker_available()

requires_docker = pytest.mark.skipif(
    not DOCKER_AVAILABLE,
    reason="Docker not available — skipping integration tests",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: end-to-end tests that need docker/testcontainers"
    )


@pytest.fixture(scope="session")
def docker_ok() -> bool:
    return DOCKER_AVAILABLE


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.environ.get("MINEHUB_API_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def kafka_bootstrap() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP", "127.0.0.1:9092")


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://minehub:change-me@127.0.0.1:5432/minehub",
    )


def port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
