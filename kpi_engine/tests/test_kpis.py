from pathlib import Path

from kpi_engine.registry import load_definitions
from kpi_engine.sandbox import run_kpi

DEFS = load_definitions(Path(__file__).resolve().parents[2] / "config" / "kpis")


def test_all_definitions_load():
    assert {"strip_ratio", "shovel_hang_time", "fuel_burn_per_tonne"} <= set(DEFS)


def test_strip_ratio():
    d = DEFS["strip_ratio"]
    assert run_kpi(d.lua, {"tonnes_by_material": {"ORE": 40000, "WASTE": 76000}}) == 1.9
    assert run_kpi(d.lua, {"tonnes_by_material": {"WASTE": 10}}) is None


def test_shovel_hang_time():
    d = DEFS["shovel_hang_time"]
    assert run_kpi(d.lua, {"shovel_idle_minutes": {"SH01": 30, "SH02": 50}}) == 40


def test_fuel_burn_per_tonne():
    d = DEFS["fuel_burn_per_tonne"]
    v = run_kpi(d.lua, {"truck_operating_hours": {"HT01": 10, "HT02": 10}, "total_tonnes": 38000}, d.params)
    assert abs(v - 0.1) < 1e-9