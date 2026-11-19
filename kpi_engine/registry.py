"""Load KPI definitions from config/kpis/*.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class KpiDefinition:
    name: str
    version: int
    owner: str
    unit: str
    description: str
    inputs: list[str]
    lua: str
    params: dict[str, Any] = field(default_factory=dict)


def load_definitions(kpi_dir: Path) -> dict[str, KpiDefinition]:
    out: dict[str, KpiDefinition] = {}
    for f in sorted(kpi_dir.glob("*.yaml")):
        d = yaml.safe_load(f.read_text())
        out[d["name"]] = KpiDefinition(
            name=d["name"], version=int(d["version"]), owner=d.get("owner", "unknown"), unit=d.get("unit", ""),
            description=d.get("description", ""), inputs=list(d.get("inputs", [])), lua=d["lua"],
            params=d.get("params", {}) or {},
        )
    return out