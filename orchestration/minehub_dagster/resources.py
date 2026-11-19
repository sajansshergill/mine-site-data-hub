"""Dagster resources: database, Redis and dbt."""

from pathlib import Path

import psycopg
import redis
from dagster import ConfigurableResource
from dagster_dbt import DbtCliResource

from minehub_common.settings import get_settings

DBT_DIR = Path(__file__).resolve().parents[2] / "warehouse" / "dbt"


class PostgresResource(ConfigurableResource):
    dsn: str = get_settings().psycopg_dsn

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn)


class RedisResource(ConfigurableResource):
    url: str = get_settings().redis_url

    def client(self) -> redis.Redis:
        return redis.Redis.from_url(self.url, decode_responses=True)


dbt_resource = DbtCliResource(project_dir=str(DBT_DIR), profiles_dir=str(DBT_DIR))