"""Rule-based shift commentary for the PDF report."""
from __future__ import annotations

from typing import Any


def build_commentary(
    *,
    compliance_pct: float | None,
    crusher_downtime_h: float,
    crusher_nameplate_tph: float,
    top_delay_reason: str | None,
    top_delay_hours: float,
    dq_failures: int,
) -> list[str]:
    notes: list[str] = []

    if compliance_pct is None:
        notes.append("Plan compliance could not be calculated (missing planned tonnes).")
    elif compliance_pct >= 100:
        notes.append(f"Shift met or exceeded plan ({compliance_pct:.1f}% compliance).")
    elif compliance_pct >= 90:
        notes.append(f"Shift finished slightly under plan at {compliance_pct:.1f}% compliance.")
    else:
        notes.append(f"Shift finished materially under plan at {compliance_pct:.1f}% compliance.")

    if crusher_downtime_h > 0:
        lost = crusher_downtime_h * crusher_nameplate_tph
        notes.append(
            f"Crusher downtime of {crusher_downtime_h:.1f} h implies roughly "
            f"{lost:,.0f} t of lost nameplate throughput."
        )
    else:
        notes.append("No crusher downtime recorded for the shift.")

    if top_delay_reason and top_delay_hours > 0:
        notes.append(
            f"Largest delay bucket was '{top_delay_reason}' ({top_delay_hours:.1f} h fleet-wide)."
        )

    if dq_failures:
        notes.append(f"{dq_failures} data-quality check(s) failed — review quarantine before locking numbers.")
    else:
        notes.append("All scheduled data-quality checks passed for this shift.")

    return notes


def from_report_context(ctx: dict[str, Any]) -> list[str]:
    return build_commentary(
        compliance_pct=ctx.get("compliance_pct"),
        crusher_downtime_h=float(ctx.get("crusher_downtime_h") or 0),
        crusher_nameplate_tph=float(ctx.get("crusher_nameplate_tph") or 2200),
        top_delay_reason=ctx.get("top_delay_reason"),
        top_delay_hours=float(ctx.get("top_delay_hours") or 0),
        dq_failures=int(ctx.get("dq_failures") or 0),
    )
