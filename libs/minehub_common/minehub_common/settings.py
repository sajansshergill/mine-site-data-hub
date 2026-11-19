"""pydantic-settings + YAML config loader used by every service."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://minehub:change-me@timescaledb:5432/minehub"
    psycopg_dsn: str = "postgresql://minehub:change-me@timescaledb:5432/minehub"
    postgres_user: str = "minehub"
    postgres_password: str = "change-me"
    postgres_db: str = "minehub"
    postgres_host: str = "timescaledb"
    postgres_port: int = 5432

    # Redis / Kafka
    redis_url: str = "redis://redis:6379/0"
    kafka_bootstrap: str = "redpanda:9092"
    schema_registry_url: str = "http://redpanda:8081"

    # Protocols
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_topic: str = "fleet/#"
    opcua_endpoint: str = "opc.tcp://sim-plant-opcua:4840/minehub/plant"
    modbus_host: str = "sim-plant-modbus"
    modbus_port: int = 5020

    # Paths
    config_dir: Path = Path("/app/config")
    schema_dir: Path = Path("/app/schemas")
    drop_dir: Path = Path("/app/data/drop")
    report_dir: Path = Path("/app/reporting/output")

    # Auth / ops
    api_keys: str = "viewer:viewer-key,engineer:engineer-key,admin:admin-key"
    metrics_port: int = 9100
    log_level: str = "INFO"
    site_tz: str = "America/Los_Angeles"

    # SMTP
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "minehub@demo.local"
    smtp_to: str = "shift-superintendent@demo.local"
    smtp_user: str = ""
    smtp_password: str = ""

    # Simulator
    fault_rate: float = 0.05
    sim_speed: float = 1.0

    def load_yaml(self, name: str) -> dict[str, Any]:
        path = self.config_dir / name
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a mapping at the top level")
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
