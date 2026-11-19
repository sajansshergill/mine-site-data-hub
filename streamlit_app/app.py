"""Mine Site Data Hub — Streamlit operations dashboard."""
from __future__ import annotations

import os
from datetime import date, timedelta

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Mine Site Data Hub",
    page_icon="⛏",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("MINEHUB_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("MINEHUB_API_KEY", "viewer-key")


def _headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


@st.cache_data(ttl=15)
def fetch_json(path: str) -> dict | list | None:
    try:
        r = httpx.get(f"{API_URL}{path}", headers=_headers(), timeout=5.0)
        if r.status_code >= 400:
            return None
        return r.json()
    except Exception:
        return None


def demo_live() -> dict:
    return {
        "shift_id": f"{date.today().isoformat()}-D",
        "tonnes_total": 18420.0,
        "loads": 81,
        "tonnes_by_material": {"ORE": 11240.0, "WASTE": 7180.0},
        "tonnes_by_location": {"PIT1_B1": 6240.0, "PIT1_B2": 7180.0, "PIT2_B1": 5000.0},
        "truck_loads": {f"HT{i:02d}": int(5 + (i % 4)) for i in range(1, 13)},
        "queues": {"PIT1_B1": 3, "PIT1_B2": 2, "PIT2_B1": 4, "CRUSHER": 1},
    }


def demo_pva(shift_id: str) -> dict:
    rows = [
        {"location": "PIT1_B1", "material": "ORE", "planned_tonnes": 6500, "actual_tonnes": 6240},
        {"location": "PIT1_B2", "material": "WASTE", "planned_tonnes": 7000, "actual_tonnes": 7180},
        {"location": "PIT2_B1", "material": "ORE", "planned_tonnes": 5200, "actual_tonnes": 5000},
    ]
    for r in rows:
        r["variance_t"] = r["actual_tonnes"] - r["planned_tonnes"]
        r["variance_pct"] = round(100 * r["variance_t"] / r["planned_tonnes"], 1)
    tp = sum(r["planned_tonnes"] for r in rows)
    ta = sum(r["actual_tonnes"] for r in rows)
    return {
        "shift_id": shift_id,
        "rows": rows,
        "total_planned": tp,
        "total_actual": ta,
        "compliance_pct": round(100 * ta / tp, 1),
    }


def demo_shifts() -> list[dict]:
    out = []
    for i in range(6):
        d = date.today() - timedelta(days=i // 2)
        code = "D" if i % 2 == 0 else "N"
        planned = 18000 + i * 200
        actual = planned * (0.92 + (i % 3) * 0.03)
        out.append(
            {
                "shift_id": f"{d.isoformat()}-{code}",
                "planned_tonnes": planned,
                "actual_tonnes": round(actual, 1),
                "compliance_pct": round(100 * actual / planned, 1),
            }
        )
    return out


def load_live() -> tuple[dict, bool]:
    data = fetch_json("/live/shift")
    if data and data.get("shift_id"):
        return data, True
    return demo_live(), False


def load_shifts() -> tuple[list[dict], bool]:
    data = fetch_json("/shifts?limit=12")
    if isinstance(data, list) and data:
        return data, True
    return demo_shifts(), False


def load_pva(shift_id: str) -> tuple[dict, bool]:
    data = fetch_json(f"/shifts/{shift_id}/plan-vs-actual")
    if data and data.get("rows"):
        return data, True
    return demo_pva(shift_id), False


st.markdown(
    """
<style>
  .stApp { background: linear-gradient(180deg, #0f1410 0%, #1a2218 40%, #12180f 100%); color: #e8ece4; }
  h1, h2, h3, p, label, span, div { color: #e7ecdf !important; }
  [data-testid="stMetricValue"] { color: #d4e2c0 !important; font-weight: 700; }
  [data-testid="stSidebar"] { background: #141a12; border-right: 1px solid #2a3524; }
  .block-container { padding-top: 1.2rem; }
  .hub-brand { font-family: "IBM Plex Sans", "Segoe UI", sans-serif; letter-spacing: 0.04em;
               font-size: 0.85rem; color: #9bb07a !important; text-transform: uppercase; }
  .hub-title { font-family: "IBM Plex Sans", "Segoe UI", sans-serif; font-size: 2.1rem;
               font-weight: 700; margin: 0.1rem 0 0.4rem 0; color: #f2f5ea !important; }
  .hub-sub { color: #a8b59a !important; margin-bottom: 1rem; }
  .pill { display:inline-block; padding: 0.2rem 0.65rem; border-radius: 999px;
          border: 1px solid #3d4d34; background: #1d2719; color: #c5d6ae !important;
          font-size: 0.8rem; }
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Mine Site Data Hub")
    st.caption("Plan vs actual · live fleet · plant")
    source = st.radio("Data source", ["Auto (API → demo fallback)", "Force demo"], index=0)
    refresh = st.button("Refresh now", use_container_width=True)
    if refresh:
        st.cache_data.clear()
    st.divider()
    st.caption(f"API: `{API_URL}`")
    health = fetch_json("/health")
    if health and health.get("status") == "ok":
        st.success("API connected")
    else:
        st.warning("API unreachable — demo mode")

force_demo = source.startswith("Force")
live, live_live = (demo_live(), False) if force_demo else load_live()
shifts, shifts_live = (demo_shifts(), False) if force_demo else load_shifts()

st.markdown('<div class="hub-brand">Demo Gold Mine · Operations</div>', unsafe_allow_html=True)
st.markdown('<div class="hub-title">Shift Command Board</div>', unsafe_allow_html=True)
mode = "LIVE" if live_live else "DEMO"
st.markdown(
    f'<div class="hub-sub">Current shift <span class="pill">{live.get("shift_id", "—")}</span> · '
    f'<span class="pill">{mode}</span></div>',
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tonnes moved", f"{live.get('tonnes_total', 0):,.0f} t")
c2.metric("Loads", f"{live.get('loads', 0):,}")
mat = live.get("tonnes_by_material") or {}
ore, waste = float(mat.get("ORE", 0)), float(mat.get("WASTE", 0))
strip = (waste / ore) if ore else None
c3.metric("Ore / Waste", f"{ore:,.0f} / {waste:,.0f}")
c4.metric("Strip ratio", f"{strip:.2f}" if strip else "—")

left, right = st.columns((1.2, 1))
with left:
    st.subheader("Tonnes by location")
    loc = live.get("tonnes_by_location") or {}
    if loc:
        df_loc = pd.DataFrame({"location": list(loc.keys()), "tonnes": list(loc.values())})
        fig = px.bar(
            df_loc,
            x="location",
            y="tonnes",
            color_discrete_sequence=["#8fa86a"],
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#dce6d0",
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
            yaxis_title="tonnes",
            xaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No location tonnes yet.")

with right:
    st.subheader("Queue lengths")
    queues = live.get("queues") or {}
    if queues:
        df_q = pd.DataFrame({"point": list(queues.keys()), "trucks": list(queues.values())})
        fig = px.bar(df_q, x="point", y="trucks", color_discrete_sequence=["#c4a35a"])
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#dce6d0",
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
            xaxis_title="",
            yaxis_title="trucks",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No queue data.")

st.subheader("Truck loads this shift")
loads = live.get("truck_loads") or {}
if loads:
    df_t = pd.DataFrame({"truck": list(loads.keys()), "loads": list(loads.values())}).sort_values("truck")
    fig = go.Figure(
        go.Bar(x=df_t["truck"], y=df_t["loads"], marker_color="#6e8f9e")
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#dce6d0",
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="loads",
        xaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Plan vs actual")

shift_ids = [s["shift_id"] for s in shifts] or [live.get("shift_id")]
selected = st.selectbox("Shift", shift_ids, index=0)
pva, pva_live = (demo_pva(selected), False) if force_demo else load_pva(selected)
badge = "API" if pva_live else "demo"
st.caption(f"Source: {badge}")

m1, m2, m3 = st.columns(3)
m1.metric("Planned", f"{pva.get('total_planned', 0):,.0f} t")
m2.metric("Actual", f"{pva.get('total_actual', 0):,.0f} t")
comp = pva.get("compliance_pct")
m3.metric("Compliance", f"{comp:.1f}%" if comp is not None else "—")

rows = pva.get("rows") or []
if rows:
    df = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Planned", x=df["location"] + " / " + df["material"], y=df["planned_tonnes"], marker_color="#5c6b4a"))
    fig.add_trace(go.Bar(name="Actual", x=df["location"] + " / " + df["material"], y=df["actual_tonnes"], marker_color="#b7c992"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#dce6d0",
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="tonnes",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Recent shifts")
st.dataframe(pd.DataFrame(shifts), use_container_width=True, hide_index=True)

st.caption("Mine Site Plan vs. Actual Data Hub · Streamlit surface over FastAPI / Redis live state")
