"""Generate a shift-level mine plan XLSX (sheet 'Shift Plan')."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

# Must match orchestration.minehub_dagster.assets.batch_plan.COLUMNS keys
COLUMNS = [
    "Shift Date",
    "Shift",
    "Location",
    "Material",
    "Planned Tonnes",
    "Planned Grade (g/t)",
    "Planned Truck Hours",
    "Plan Version",
]

LOCATIONS = [
    ("PIT1_B1", "ORE", 12000, 1.15),
    ("PIT1_B2", "WASTE", 9000, 0.0),
    ("PIT2_B1", "ORE", 8000, 0.95),
]


def build_rows(start: date, days: int, version: str) -> list[list]:
    rows: list[list] = []
    for offset in range(days):
        d = start + timedelta(days=offset)
        for shift in ("D", "N"):
            factor = 1.0 if shift == "D" else 0.85
            for loc, material, tonnes, grade in LOCATIONS:
                truck_hours = round((tonnes * factor) / 220.0, 1)  # ~payload / cycle heuristic
                rows.append(
                    [
                        d.isoformat(),
                        shift,
                        loc,
                        material,
                        round(tonnes * factor),
                        grade if material == "ORE" else 0.0,
                        truck_hours,
                        version,
                    ]
                )
    return rows


def write_xlsx(path: Path, rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Shift Plan"
    ws.append(COLUMNS)
    for row in rows:
        ws.append(row)
    wb.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mine plan XLSX")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--start", type=str, default="2026-11-01")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--version", type=str, default="v1")
    args = parser.parse_args()
    start = date.fromisoformat(args.start)
    rows = build_rows(start, args.days, args.version)
    write_xlsx(args.out, rows)
    print(f"wrote {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
