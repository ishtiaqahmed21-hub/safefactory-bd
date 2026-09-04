"""SafeFactory BD — HSE Command Centre (landing page)."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import theme as T
from safefactory.incidents import IncidentRegister, exposure_hours, heinrich_ratio
from safefactory.risk import RiskRegister

T.setup("Command Centre")

st.title("SafeFactory BD — HSE Command Centre")
st.caption(
    "An ISO 45001-aligned health, safety and environment management system for "
    "Bangladeshi food and dairy manufacturing, built on open national data."
)

if not T.guard():
    st.stop()

# --------------------------------------------------------------------------
# Sidebar: exposure denominator
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Site parameters")
    headcount = st.number_input("Headcount", 50, 5000, 450, 10)
    hours_per_shift = st.number_input("Hours per shift", 6.0, 12.0, 8.0, 0.5)
    working_days = st.number_input("Working days in period", 100, 400, 300, 10)
    hours = exposure_hours(headcount, hours_per_shift, working_days)
    st.caption(
        f"Exposure hours: **{hours:,.0f}**\n\n"
        "This is an estimate from headcount, not a timesheet total. "
        "Every frequency rate below inherits that assumption."
    )

# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
reg = RiskRegister.from_csv()
inc_df = T.load("incidents_synthetic_demo")
inc = IncidentRegister(inc_df)
kpi = inc.kpis(hours, headcount)
hr = heinrich_ratio(inc.df)

open_high = reg.open_high_risks()

T.note(
    "<b>Demonstration data.</b> The incident register on this page is "
    "<b>synthetic</b> — generated, not observed — so the system can be "
    "demonstrated before a plant loads its own records. The hazard register, "
    "compliance matrix, air-quality analysis and site index are all built from "
    "real sources, cited on the Data & Method page.",
    kind="warn",
)

# --------------------------------------------------------------------------
# Lagging indicators
# --------------------------------------------------------------------------
st.subheader("Lagging indicators")
T.tiles([
    ("LTIFR", f"{kpi['LTIFR_per_1M_hours']:.2f}", "per 1,000,000 hours (ILO base)"),
    ("TRIR", f"{kpi['TRIR_per_200k_hours']:.2f}", "per 200,000 hours (OSHA base)"),
    ("DART rate", f"{kpi['DART_per_200k_hours']:.2f}", "per 200,000 hours"),
    ("Severity rate", f"{kpi['severity_rate_per_1M_hours']:.0f}", "days lost per 1M hours"),
    ("Lost-time injuries", f"{kpi['lost_time_injuries']}", f"{kpi['days_lost']:.0f} days lost"),
    ("Fatalities", f"{kpi['fatalities']}", "period to date"),
])

st.subheader("Leading indicators")
T.tiles([
    ("Near misses reported", f"{kpi['near_misses']}", "the earliest signal available"),
    ("Near miss : recordable", f"{hr['near_miss_per_recordable']:.1f} : 1",
     "below about 10:1 suggests under-reporting"),
    ("Hazards at High/Critical today", f"{len(open_high)}",
     f"of {len(reg.df)} assessed"),
    ("Controls still unbought", f"{len(reg.roadmap())}",
     "hazards whose control plan is not yet in place"),
])

# --------------------------------------------------------------------------
# Risk state
# --------------------------------------------------------------------------
left, right = st.columns([1.15, 1])

with left:
    st.subheader("Where the risk sits")
    sc = reg.state_comparison()
    fig = go.Figure()
    for i, state in enumerate(["inherent", "current", "target"]):
        fig.add_bar(
            name=state.title(),
            x=sc.index.tolist(),
            y=sc[state].tolist(),
            marker_color=T.SERIES[i],
            marker_line=dict(color=T.SURFACE, width=2),
            text=sc[state].tolist(),
            textposition="outside",
            textfont=dict(color=T.INK_SECONDARY, size=11),
            hovertemplate="%{x} · " + state + ": %{y} hazards<extra></extra>",
        )
    fig.update_layout(**T.layout("Hazards by risk band", height=360),
                      barmode="group", bargap=0.28, bargroupgap=0.08)
    fig.update_yaxes(title="Hazards")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "**Inherent** is the risk with no controls at all. **Current** credits only "
        "the controls actually installed. **Target** is what the full control plan "
        "would deliver. The distance between current and target is the programme."
    )

with right:
    st.subheader("Reporting pyramid")
    pyramid = [
        ("Near miss", hr["near_miss"], T.SERIES[0]),
        ("First aid", hr["first_aid"], T.SERIES[1]),
        ("Recordable", hr["recordable"], T.SERIES[2]),
        ("Lost time or worse", hr["lost_time_or_worse"], T.STATUS["critical"]),
    ]
    fig = go.Figure()
    for label, value, color in pyramid:
        fig.add_bar(
            x=[value], y=[label], orientation="h", marker_color=color,
            marker_line=dict(color=T.SURFACE, width=2), showlegend=False,
            text=[f"{int(value)}"], textposition="outside",
            textfont=dict(color=T.INK_SECONDARY, size=11),
            hovertemplate=f"{label}: %{{x}} events<extra></extra>",
        )
    fig.update_layout(**T.layout("Event mix by severity", height=360))
    fig.update_yaxes(categoryorder="array",
                     categoryarray=[p[0] for p in reversed(pyramid)])
    fig.update_xaxes(title="Events")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "A plant reporting few near misses per recordable is almost certainly "
        "under-reporting rather than unusually safe. This ratio is a measure of "
        "the reporting system, not of the hazard."
    )

# --------------------------------------------------------------------------
# What needs doing
# --------------------------------------------------------------------------
st.subheader("Top of the queue")
road = reg.roadmap().head(8)
st.dataframe(
    road[["hazard_id", "area", "hazard_description", "control_status",
          "risk_score_current", "risk_band_current", "risk_score_residual",
          "gap_to_target", "responsible"]].rename(columns={
        "hazard_id": "ID", "area": "Area", "hazard_description": "Hazard",
        "control_status": "Control status", "risk_score_current": "Risk now",
        "risk_band_current": "Band now", "risk_score_residual": "Risk after",
        "gap_to_target": "Points removed", "responsible": "Owner",
    }),
    width="stretch", hide_index=True,
)
st.caption(
    "Ranked by the risk points the outstanding control plan would remove — not by "
    "raw risk score. That ordering is where the next unit of HSE budget does the "
    "most good."
)

st.divider()
st.caption(
    "Built by Ishtiaq Ahmed · Industrial & Production Engineering, Islamic "
    "University of Technology · Source and method: see the Data & Method page."
)
