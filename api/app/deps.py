from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

import redis
from sqlalchemy.engine import Connection

from minehub_common.db.engine import get_engine
from minehub_common.settings import get_settings
from minehub_common.shifts import ShiftCalendar


def db() -> Iterator[Connection]:
    with get_engine().connect() as conn:
        yield conn


@lru_cache
def redis_client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


@lru_cache
def calendar() -> ShiftCalendar:
    return ShiftCalendar(get_settings().load_yaml("site.yaml"))