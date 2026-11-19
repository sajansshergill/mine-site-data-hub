"""Attach shift_id and material to cycles from site / equipment config."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from minehub_common.settings import get_settings
from minehub_common.shifts import ShiftCalendar


def build_shift_calendar(site: dict[str, Any] | None = None) -> ShiftCalendar:
    cfg = site if site is not None else get_settings().load_yaml("site.yaml")
    return ShiftCalendar(cfg)


def shift_id_for(ts: datetime, calendar: ShiftCalendar | None = None) -> str:
    cal = calendar or build_shift_calendar()
    return cal.shift_id(ts)


def material_by_location(equipment: dict[str, Any] | None = None) -> dict[str, str]:
    """Map location id -> material from shovel locations and dump accepts."""
    cfg = equipment if equipment is not None else get_settings().load_yaml("equipment.yaml")
    mapping: dict[str, str] = {}
    for shovel in cfg.get("shovels") or []:
        loc = shovel.get("location")
        material = shovel.get("material")
        if loc and material:
            mapping[str(loc)] = str(material)
    for dump in cfg.get("dumps") or []:
        loc = dump.get("location")
        accepts = dump.get("accepts") or []
        if loc and accepts:
            mapping[str(loc)] = str(accepts[0])
    return mapping


def material_for(
    source_location: str | None,
    dest_location: str | None,
    location_materials: dict[str, str] | None = None,
) -> str | None:
    mats = location_materials if location_materials is not None else material_by_location()
    if source_location and source_location in mats:
        return mats[source_location]
    if dest_location and dest_location in mats:
        return mats[dest_location]
    return None


class Enricher:
    """Stateful helper holding calendar + material maps."""

    def __init__(
        self,
        site: dict[str, Any] | None = None,
        equipment: dict[str, Any] | None = None,
    ) -> None:
        self.calendar = build_shift_calendar(site)
        self.materials = material_by_location(equipment)

    def shift_id(self, ts: datetime) -> str:
        return self.calendar.shift_id(ts)

    def material(self, source_location: str | None, dest_location: str | None = None) -> str | None:
        return material_for(source_location, dest_location, self.materials)
