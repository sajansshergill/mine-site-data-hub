"""Generate grade-control assay CSV."""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

COLUMNS = ["sample_id", "location", "block_id", "sampled_on", "au_gpt", "tonnes_represented"]

BLOCKS = [
    ("PIT1_B1", "P1B1-12"),
    ("PIT1_B1", "P1B1-13"),
    ("PIT1_B2", "P1B2-08"),
    ("PIT2_B1", "P2B1-04"),
    ("PIT2_B1", "P2B1-05"),
]


def build_rows(n: int, start: date, rng: random.Random) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(1, n + 1):
        loc, block = rng.choice(BLOCKS)
        grade = round(rng.uniform(0.35, 1.8) if "B2" not in loc else rng.uniform(0.05, 0.25), 3)
        tonnes = round(rng.uniform(800, 3500), 1)
        sampled = start + timedelta(days=rng.randint(0, 13))
        rows.append(
            {
                "sample_id": f"ASM-{2026000 + i}",
                "location": loc,
                "block_id": block,
                "sampled_on": sampled.isoformat(),
                "au_gpt": f"{grade}",
                "tonnes_represented": f"{tonnes}",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate assay CSV")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--start", type=str, default="2026-11-01")
    args = parser.parse_args()

    rows = build_rows(args.count, date.fromisoformat(args.start), random.Random(33))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
