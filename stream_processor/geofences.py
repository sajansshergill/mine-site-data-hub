"""Point-in-circle geofences loaded from road_network.yaml."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


class LocationKind(str, Enum):
    SHOVEL = "shovel"
    DUMP = "dump"
    OTHER = "other"


@dataclass(frozen=True)
class Geofence:
    node_id: str
    x: float
    y: float
    radius_m: float
    kind: LocationKind

    def contains(self, x: float, y: float) -> bool:
        return distance_m(self.x, self.y, x, y) <= self.radius_m


def distance_m(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def classify_node(node_id: str) -> LocationKind:
    """Classify PIT* as shovel/load; CRUSHER / WASTE_DUMP* as dump."""
    upper = node_id.upper()
    if upper.startswith("PIT"):
        return LocationKind.SHOVEL
    if upper.startswith("CRUSHER") or upper.startswith("WASTE_DUMP"):
        return LocationKind.DUMP
    return LocationKind.OTHER


def load_geofences(road_network: dict[str, Any]) -> list[Geofence]:
    """Load nodes that define geofence_radius_m."""
    fences: list[Geofence] = []
    for node_id, props in (road_network.get("nodes") or {}).items():
        radius = props.get("geofence_radius_m")
        if radius is None:
            continue
        fences.append(
            Geofence(
                node_id=node_id,
                x=float(props["x"]),
                y=float(props["y"]),
                radius_m=float(radius),
                kind=classify_node(node_id),
            )
        )
    return fences


@dataclass(frozen=True)
class LocationHit:
    node_id: str | None
    kind: LocationKind


class GeofenceIndex:
    def __init__(self, fences: list[Geofence]) -> None:
        self._fences = fences

    @classmethod
    def from_yaml(cls, road_network: dict[str, Any]) -> GeofenceIndex:
        return cls(load_geofences(road_network))

    def locate(self, x: float, y: float) -> LocationHit:
        """Return the containing geofence (nearest centre on ties), or outside."""
        best: Geofence | None = None
        best_dist = float("inf")
        for fence in self._fences:
            dist = distance_m(fence.x, fence.y, x, y)
            if dist <= fence.radius_m and dist < best_dist:
                best = fence
                best_dist = dist
        if best is None:
            return LocationHit(node_id=None, kind=LocationKind.OTHER)
        return LocationHit(node_id=best.node_id, kind=best.kind)

    def is_shovel(self, x: float, y: float) -> bool:
        return self.locate(x, y).kind is LocationKind.SHOVEL

    def is_dump(self, x: float, y: float) -> bool:
        return self.locate(x, y).kind is LocationKind.DUMP
