"""Simple dispatch: assign trucks to the shovel/dump with the shortest queue."""
from __future__ import annotations

from simulators.fleet.crusher import DumpPoint
from simulators.fleet.shovel import Shovel
from simulators.fleet.truck import Truck


def assign_shovel(truck: Truck, shovels: list[Shovel]) -> Shovel | None:
    if not shovels:
        return None
    best = min(shovels, key=lambda s: (s.queue_length, s.shovel_id))
    truck.assigned_shovel = best.shovel_id
    truck.material = best.material
    return best


def assign_dump(truck: Truck, dumps: list[DumpPoint]) -> DumpPoint | None:
    material = truck.material or "ORE"
    candidates = [d for d in dumps if d.accepts_material(material)]
    if not candidates:
        candidates = list(dumps)
    if not candidates:
        return None
    best = min(candidates, key=lambda d: (d.queue_length, d.dump_id))
    truck.assigned_dump = best.dump_id
    return best


def shovel_by_id(shovels: list[Shovel], shovel_id: str | None) -> Shovel | None:
    if shovel_id is None:
        return None
    for s in shovels:
        if s.shovel_id == shovel_id:
            return s
    return None


def dump_by_id(dumps: list[DumpPoint], dump_id: str | None) -> DumpPoint | None:
    if dump_id is None:
        return None
    for d in dumps:
        if d.dump_id == dump_id:
            return d
    return None
