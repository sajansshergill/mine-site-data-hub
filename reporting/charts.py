"""Matplotlib charts rendered as base64 PNGs for HTML/PDF embedding."""
from __future__ import annotations

import base64
import io
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def plan_vs_actual_bar(locations: Sequence[str], planned: Sequence[float], actual: Sequence[float]) -> str:
    fig, ax = plt.subplots(figsize=(8, 3.5))
    x = range(len(locations))
    width = 0.38
    ax.bar([i - width / 2 for i in x], planned, width, label="Planned", color="#3d5a4c")
    ax.bar([i + width / 2 for i in x], actual, width, label="Actual", color="#c4a35a")
    ax.set_xticks(list(x))
    ax.set_xticklabels(list(locations), rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Tonnes")
    ax.set_title("Plan vs actual by location")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return _to_b64(fig)


def fleet_loads_bar(trucks: Sequence[str], loads: Sequence[int]) -> str:
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(list(trucks), list(loads), color="#4a6fa5")
    ax.set_ylabel("Loads")
    ax.set_title("Loads per truck")
    ax.tick_params(axis="x", labelrotation=40)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return _to_b64(fig)


def delay_pie(labels: Sequence[str], hours: Sequence[float]) -> str:
    fig, ax = plt.subplots(figsize=(4.5, 4))
    if not labels or sum(hours) <= 0:
        ax.text(0.5, 0.5, "No delay data", ha="center", va="center")
        ax.axis("off")
    else:
        ax.pie(list(hours), labels=list(labels), autopct="%1.0f%%", startangle=90,
               colors=["#8b5e3c", "#c4a35a", "#6b7c6e", "#4a6fa5", "#a65d57"])
        ax.set_title("Delay hours by reason")
    return _to_b64(fig)
