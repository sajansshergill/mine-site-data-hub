"""Haul-road network built from config/road_network.yaml."""
from __future__ import annotations

import math
from typing import Any

import networkx as nx


def _dist_m(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def build_road_graph(cfg: dict[str, Any]) -> nx.DiGraph:
    """Directed graph with bidirectional edges; edge attrs include length_m, grade_pct, speed_limit_kmh."""
    g = nx.DiGraph()
    nodes = cfg["nodes"]
    for name, meta in nodes.items():
        g.add_node(name, x=float(meta["x"]), y=float(meta["y"]), **{k: v for k, v in meta.items() if k not in ("x", "y")})

    for seg in cfg["segments"]:
        u, v = seg["from"], seg["to"]
        length = _dist_m(nodes[u], nodes[v])
        grade = float(seg.get("grade_pct", 0))
        speed = float(seg.get("speed_limit_kmh", 40))
        g.add_edge(u, v, length_m=length, grade_pct=grade, speed_limit_kmh=speed)
        # reverse direction: grade flips sign
        g.add_edge(v, u, length_m=length, grade_pct=-grade, speed_limit_kmh=speed)
    return g


def node_xy(g: nx.DiGraph, name: str) -> tuple[float, float]:
    return float(g.nodes[name]["x"]), float(g.nodes[name]["y"])


def shortest_path(g: nx.DiGraph, src: str, dst: str) -> list[str]:
    return nx.shortest_path(g, src, dst, weight="length_m")


def path_length_m(g: nx.DiGraph, path: list[str]) -> float:
    total = 0.0
    for a, b in zip(path, path[1:], strict=False):
        total += float(g.edges[a, b]["length_m"])
    return total


def travel_time_s(g: nx.DiGraph, path: list[str], speed_kmh: float) -> float:
    """Wall-clock travel time along path, capped by each segment's speed limit."""
    if len(path) < 2:
        return 0.0
    seconds = 0.0
    for a, b in zip(path, path[1:], strict=False):
        length = float(g.edges[a, b]["length_m"])
        limit = float(g.edges[a, b]["speed_limit_kmh"])
        v = min(speed_kmh, limit)
        if v <= 0:
            v = 1.0
        seconds += length / (v * 1000.0 / 3600.0)
    return seconds


def interpolate_xy(g: nx.DiGraph, path: list[str], progress: float) -> tuple[float, float]:
    """progress in [0, 1] along path → (x, y)."""
    if not path:
        return 0.0, 0.0
    if len(path) == 1 or progress <= 0:
        return node_xy(g, path[0])
    if progress >= 1:
        return node_xy(g, path[-1])

    total = path_length_m(g, path)
    target = progress * total
    walked = 0.0
    for a, b in zip(path, path[1:], strict=False):
        seg = float(g.edges[a, b]["length_m"])
        if walked + seg >= target:
            t = 0.0 if seg == 0 else (target - walked) / seg
            ax, ay = node_xy(g, a)
            bx, by = node_xy(g, b)
            return ax + t * (bx - ax), ay + t * (by - ay)
        walked += seg
    return node_xy(g, path[-1])
