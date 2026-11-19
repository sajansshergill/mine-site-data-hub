"""Redis live-state updates via Lua scripts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import redis

LUA_DIR = Path(__file__).resolve().parent / "redis_lua"


def _load_script(name: str) -> str:
    path = LUA_DIR / name
    return path.read_text(encoding="utf-8")


class LiveState:
    """Thin wrapper around Redis + registered Lua scripts."""

    def __init__(self, redis_url: str) -> None:
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._record_load = self.client.register_script(_load_script("record_load.lua"))
        self._update_queue = self.client.register_script(_load_script("update_queue.lua"))
        self._close_shift = self.client.register_script(_load_script("close_shift.lua"))

    def record_load(
        self,
        shift_id: str,
        truck_id: str,
        payload: float,
        material: str,
        location: str,
    ) -> Any:
        return self._record_load(
            keys=[
                f"shift:{shift_id}:totals",
                f"shift:{shift_id}:truck_loads",
                f"shift:{shift_id}:last_payload",
            ],
            args=[truck_id, float(payload), material, location],
        )

    def update_queue(self, location: str, delta: int) -> int:
        result = self._update_queue(keys=["live:queues"], args=[location, int(delta)])
        return int(result)

    def close_shift(self, old_shift_id: str, new_shift_id: str) -> str:
        result = self._close_shift(
            keys=[
                "live:current_shift",
                f"shift:{old_shift_id}:totals",
                f"shift:{old_shift_id}:truck_loads",
                f"shift:{old_shift_id}:last_payload",
                f"shift:{old_shift_id}:snapshot",
                "live:queues",
            ],
            args=[new_shift_id],
        )
        return str(result)

    def ensure_current_shift(self, shift_id: str) -> str | None:
        """Set live:current_shift if missing; on change, snapshot the previous shift."""
        current = self.client.get("live:current_shift")
        if current is None:
            self.client.set("live:current_shift", shift_id)
            return None
        if current != shift_id:
            self.close_shift(current, shift_id)
            return current
        return None
