"""Write messy multi-vendor equipment status logs under --out-dir."""
from __future__ import annotations

import argparse
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from minehub_common.logging import setup_logging
from minehub_common.settings import get_settings

SERVICE = "sim-logs"
log = logging.getLogger(SERVICE)

# equipment ids split across vendors
VENDOR_EQUIPMENT = {
    "VENDOR_A": ["HT01", "HT02", "HT03", "HT04"],
    "VENDOR_B": ["SH01", "SH02", "SH03", "HT05", "HT06"],
    "VENDOR_C": ["CR01", "ML01", "CV01", "HT07"],
}


def _codes_for(vendor: str, status_cfg: dict) -> list[str]:
    return list(status_cfg[vendor].keys())


def format_vendor_a(ts: datetime, equipment_id: str, code: str) -> str:
    # numeric status; space-separated; local wall clock without TZ
    return f"{ts.strftime('%Y-%m-%d %H:%M:%S')} {equipment_id} STATUS={code}"


def format_vendor_b(ts: datetime, equipment_id: str, code: str) -> str:
    # US-style datetime with AM/PM and TZ abbreviation
    stamp = ts.strftime("%m/%d/%Y %I:%M:%S %p %Z")
    return f"[{stamp}] {equipment_id} {code}"


def format_vendor_c(ts: datetime, equipment_id: str, code: str) -> str:
    # pipe-delimited with numeric offset (no colon) for Fluent Bit %z
    stamp = ts.strftime("%d-%b-%YT%H:%M:%S%z")
    return f"{stamp}|{equipment_id}|{code}|ok"


FORMATTERS = {
    "VENDOR_A": format_vendor_a,
    "VENDOR_B": format_vendor_b,
    "VENDOR_C": format_vendor_c,
}


def write_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate multi-vendor equipment log writers")
    parser.add_argument("--out-dir", type=Path, default=Path("/var/log/equipment"))
    parser.add_argument("--interval-s", type=float, default=3.0)
    args = parser.parse_args()

    setup_logging(SERVICE)
    s = get_settings()
    status_cfg = s.load_yaml("status_codes.yaml")
    site = s.load_yaml("site.yaml")
    tz = ZoneInfo(site.get("timezone", s.site_tz))
    rng = random.Random(99)

    files = {
        "VENDOR_A": args.out_dir / "vendor_a_status.log",
        "VENDOR_B": args.out_dir / "vendor_b_status.log",
        "VENDOR_C": args.out_dir / "vendor_c_status.log",
    }
    log.info("log writer started", extra={"extra": {"out_dir": str(args.out_dir)}})

    try:
        while True:
            now = datetime.now(tz)
            for vendor, path in files.items():
                equip = rng.choice(VENDOR_EQUIPMENT[vendor])
                code = rng.choice(_codes_for(vendor, status_cfg))
                # messy timestamps: sometimes drift clock by a few minutes
                ts = now if rng.random() > 0.15 else now.replace(second=rng.randint(0, 59))
                line = FORMATTERS[vendor](ts, equip, code)
                # occasional garbage line
                if rng.random() < 0.03:
                    write_line(path, "BROKEN,,,line!!!")
                write_line(path, line)
            time.sleep(args.interval_s / max(s.sim_speed, 0.01))
    except KeyboardInterrupt:
        log.info("log writer stopping")


if __name__ == "__main__":
    main()
