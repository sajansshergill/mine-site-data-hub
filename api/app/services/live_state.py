from __future__ import annotations

import redis

from app.schemas.models import LiveShift


def read_live(r: redis.Redis) -> LiveShift:
    sid = r.get("live:current_shift")
    totals = r.hgetall(f"shift:{sid}:totals") if sid else {}
    loads = r.hgetall(f"shift:{sid}:truck_loads") if sid else {}
    return LiveShift(
        shift_id=sid,
        tonnes_total=float(totals.get("tonnes_total", 0)),
        loads=int(totals.get("loads", 0)),
        tonnes_by_material={k.split(":", 1)[1]: float(v) for k, v in totals.items() if k.startswith("tonnes:")},
        tonnes_by_location={k.split(":", 1)[1]: float(v) for k, v in totals.items() if k.startswith("tonnes_loc:")},
        truck_loads={k: int(v) for k, v in loads.items()},
        queues={k: int(v) for k, v in r.hgetall("live:queues").items()},
    )