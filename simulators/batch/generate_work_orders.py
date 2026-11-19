"""Generate a CMMS-style work order CSV."""
from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

COLUMNS = [
    "WO Number",
    "Asset",
    "Type",
    "Description",
    "Opened",
    "Closed",
    "Downtime (h)",
    "Failure Code",
]

ASSETS = ["HT01", "HT03", "HT07", "SH01", "SH02", "CR01", "ML01", "CV01"]
PM_DESC = [
    "Scheduled 250-hr service",
    "Filter change",
    "Grease and inspect",
]
BD_DESC = [
    "Hydraulic hose failure",
    "Engine overheat shutdown",
    "Final drive leak",
    "Crusher liner changeout (unplanned)",
    "Conveyor belt tear",
]
FAILURE_CODES = ["HYD", "ENG", "DRIVE", "LINER", "BELT", "ELEC", ""]


def build_rows(n: int, start: datetime, tz: ZoneInfo, rng: random.Random) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(1, n + 1):
        wo_type = "PM" if rng.random() < 0.45 else "BD"
        opened = start + timedelta(hours=rng.randint(0, 14 * 24), minutes=rng.randint(0, 59))
        downtime = round(rng.uniform(0.5, 8.0) if wo_type == "BD" else rng.uniform(1.0, 4.0), 1)
        closed = opened + timedelta(hours=downtime)
        rows.append(
            {
                "WO Number": f"WO-{10000 + i}",
                "Asset": rng.choice(ASSETS),
                "Type": wo_type,
                "Description": rng.choice(PM_DESC if wo_type == "PM" else BD_DESC),
                "Opened": opened.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S"),
                "Closed": closed.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S"),
                "Downtime (h)": f"{downtime}",
                "Failure Code": "" if wo_type == "PM" else rng.choice(FAILURE_CODES),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CMMS work order CSV")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--start", type=str, default="2026-11-01T06:00:00")
    args = parser.parse_args()

    tz = ZoneInfo("America/Los_Angeles")
    start = datetime.fromisoformat(args.start).replace(tzinfo=tz)
    rows = build_rows(args.count, start, tz, random.Random(21))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
