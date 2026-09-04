"""Incident register, performance metrics and structured investigation."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import theme as T
from safefactory.incidents import (
    IncidentRegister,
    bowtie,
    exposure_hours,
    five_why,
)

T.setup("Incidents")
st.title("Incidents, Investigation & Performance")
st.caption("ISO 45001:2018 clauses 9.1.1 and 10.2 · Bangladesh Labour Act 2006 s. 80 · "
           "Bangladesh Labour Rules 2015 r. 73 and Schedule IV(2)")

if not T.guard():
    st.stop()

T.note(
    "<b>The incident data on this page is synthetic</b> — generated to demonstrate "
    "the system, not observed at any plant. The metric definitions, classification "
    "rules and investigation tools are real and are what a live register would use.",
    kind="warn",
)

with st.sidebar:
    st.header("Exposure denominator")
    headcount = st.number_input("Headcount", 50, 5000, 450, 10)
    hours_per_shift = st.number_input("Hours per shift", 6.0, 12.0, 8.0, 0.5)
    working_days = st.number_input("Working days in period", 100, 400, 300, 10)
    hours = exposure_hours(headcount, hours_per_shift, working_days)
    st.caption(f"Exposure hours: **{hours:,.0f}** (estimated, not from timesheets)")

inc = IncidentRegister(T.load("incidents_synthetic_demo"))
kpi = inc.kpis(hours, headcount)

tab_perf, tab_analysis, tab_investigate = st.tabs(
    ["Performance", "Where events come from", "Investigate an event"]
)

# --------------------------------------------------------------------------
with tab_perf:
    T.tiles([
        ("LTIFR", f"{kpi['LTIFR_per_1M_hours']:.2f}", "lost-time injuries per 1M hours"),
        ("TRIR", f"{kpi['TRIR_per_200k_hours']:.2f}", "recordables per 200k hours"),
        ("DART", f"{kpi['DART_per_200k_hours']:.2f}", "days away/restricted per 200k hours"),
        ("Severity rate", f"{kpi['severity_rate_per_1M_hours']:.0f}", "days lost per 1M hours"),
        ("Days lost per LTI", f"{kpi['average_days_lost_per_LTI']:.1f}", "typical case severity"),
    ])

    st.markdown(
        "**The two bases are not interchangeable.** LTIFR and severity rate are "
        "expressed per 1,000,000 hours on the ILO convention. TRIR and DART are "
        "expressed per 200,000 hours on the OSHA convention — 100 full-time workers "
        "at 2,000 hours a year. Quoting one number against the other's benchmark is "
        "the most common error in factory HSE reporting, so every figure above names "
        "its own base."
    )

    monthly_hours = hours / max(inc.df["month"].nunique(), 1)
    trend = inc.monthly_trend(monthly_hours)

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_scatter(
            x=trend["month"], y=trend["LTIFR"], mode="lines+markers", name="LTIFR",
            line=dict(color=T.SERIES[0], width=2), marker=dict(size=8),
            hovertemplate="%{x}<br>LTIFR %{y:.2f}<extra></extra>",
        )
        fig.add_scatter(
            x=trend["month"], y=trend["rolling_12m_LTIFR"], mode="lines",
            name="Rolling 12-month LTIFR",
            line=dict(color=T.SERIES[1], width=2, dash="dash"),
            hovertemplate="%{x}<br>Rolling LTIFR %{y:.2f}<extra></extra>",
        )
        fig.update_layout(**T.layout("Lost-time injury frequency", height=330),
                          hovermode="x unified")
        fig.update_yaxes(title="per 1,000,000 hours")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "A single month of a small plant's LTIFR is mostly noise — one injury "
            "moves it enormously. The rolling twelve-month line is the one to manage "
            "against."
        )
    with c2:
        fig = go.Figure()
        fig.add_scatter(
            x=trend["month"], y=trend["near_misses"], mode="lines+markers",
            name="Near misses reported",
            line=dict(color=T.SERIES[2], width=2), marker=dict(size=8),
            hovertemplate="%{x}<br>%{y} near misses<extra></extra>",
        )
        fig.update_layout(**T.layout("Near-miss reporting volume", height=330),
                          hovermode="x unified")
        fig.update_yaxes(title="Reports")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Falling near-miss volume is usually a reporting-culture problem, not a "
            "safety improvement. It is the leading indicator worth defending."
        )

    if "action_status" in inc.df.columns:
        st.subheader("Corrective actions")
        oa = inc.open_actions()
        overdue = oa[oa.get("days_overdue", pd.Series(dtype=int)) > 0] if len(oa) else oa
        T.tiles([
            ("Actions not yet verified", f"{len(oa)}", "ISO 45001 clause 10.2 requires "
             "verification of effectiveness, not just closure"),
            ("Overdue", f"{len(overdue)}", "past the agreed due date"),
        ])
        st.dataframe(oa.head(50), width="stretch", hide_index=True)

# --------------------------------------------------------------------------
with tab_analysis:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("What is actually hurting people")
        p = inc.pareto("immediate_cause", top=10).reset_index()
        p.columns = ["cause", "events", "pct", "cumulative_pct"]
        fig = go.Figure(
            go.Bar(
                x=p["events"], y=p["cause"], orientation="h",
                marker_color=T.SERIES[0], marker_line=dict(color=T.SURFACE, width=2),
                text=[f"{e}  ({c:.0f}% cumulative)"
                      for e, c in zip(p["events"], p["cumulative_pct"])],
                textposition="outside", textfont=dict(color=T.INK_SECONDARY, size=10),
                hovertemplate=("%{y}<br>%{x} events<br>"
                               "%{customdata:.1f}% of all events<extra></extra>"),
                customdata=p["pct"], showlegend=False,
            )
        )
        fig.update_layout(**T.layout("Immediate cause, most frequent first", height=430))
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(title="Events")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "The running cumulative share is printed on each bar rather than drawn on "
            "a second y-axis: two scales on one chart invite the reader to compare "
            "quantities that are not comparable."
        )
    with c2:
        st.subheader("Where events happen")
        ba = inc.by_area().reset_index()
        fig = go.Figure()
        for i, (col, label) in enumerate(
            [("events", "All events"), ("recordables", "Recordable"), ("ltis", "Lost time")]
        ):
            fig.add_bar(
                name=label, x=ba[col], y=ba["area"], orientation="h",
                marker_color=T.SERIES[i], marker_line=dict(color=T.SURFACE, width=2),
                hovertemplate="%{y}<br>" + label + ": %{x}<extra></extra>",
            )
        fig.update_layout(**T.layout("Events by area and severity", height=430),
                          barmode="group", bargap=0.3)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(title="Events")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "An area high on all events but low on recordables is reporting well. "
            "The reverse — few reports, severe outcomes — is the pattern to worry about."
        )

    st.subheader("The register")
    st.dataframe(inc.df.drop(columns=["month"], errors="ignore"),
                 width="stretch", hide_index=True, height=340)

# --------------------------------------------------------------------------
with tab_investigate:
    st.subheader("Five Why")
    T.note(
        "An analysis that ends at a person — 'the operator was careless' — has "
        "stopped at the immediate cause and will not prevent recurrence. The check "
        "below names that failure explicitly, so an investigation cannot be closed "
        "out on blame."
    )
    problem = st.text_input(
        "Event", "Operator sustained scald burns while draining the fryer"
    )
    default_whys = [
        "The oil was still above 100 C when the drain valve was opened",
        "The cool-down step was skipped",
        "The changeover was running behind the production schedule",
        "Nothing physically prevents the drain valve opening while the oil is hot",
        "The interlock was never specified because the line was commissioned without a pre-start safety review",
    ]
    whys = []
    for i in range(5):
        whys.append(st.text_input(f"Why {i + 1}", default_whys[i], key=f"why{i}"))
    whys = [w for w in whys if w.strip()]

    if whys:
        d = five_why(problem, whys)
        st.dataframe(d, width="stretch", hide_index=True)
        if d.attrs["terminates_in_blame"]:
            st.error(
                "**This analysis terminates in individual blame.** Keep asking why: "
                "what in the system allowed, required or rewarded that behaviour?"
            )
        else:
            st.success(
                "**The analysis reaches a systemic cause.** A control placed here "
                "protects everyone doing this task, not just the person involved."
            )
        if not d.attrs["adequate_depth"]:
            st.warning(f"Only {d.attrs['depth']} levels. Five is the working minimum.")

    st.divider()
    st.subheader("Bow-tie: ammonia loss of containment")
    T.note(
        "A bow-tie is worth drawing for one reason: it makes an <i>unbarriered line</i> "
        "visible. A threat with no preventive barrier, or a consequence with no "
        "mitigative barrier, is where the next serious event comes from."
    )
    b = bowtie(
        hazard="Anhydrous ammonia inventory in the refrigeration circuit",
        top_event="Loss of containment",
        threats=["Compressor seal failure", "Flange or gasket failure",
                 "Corrosion under insulation", "Overpressure", "Impact from vehicle"],
        consequences=["Toxic inhalation injury", "Chemical or cold burns",
                      "Flammable atmosphere and explosion", "Off-site community exposure"],
        preventive={
            "Compressor seal failure": ["Planned seal replacement", "Vibration monitoring"],
            "Flange or gasket failure": ["Torque procedure", "Joint integrity register"],
            "Corrosion under insulation": [],
            "Overpressure": ["Certified relief valves", "High-pressure cut-out"],
            "Impact from vehicle": ["Bollards around the plant room"],
        },
        mitigative={
            "Toxic inhalation injury": ["Fixed gas detection at 25 ppm",
                                        "Emergency ventilation interlock", "SCBA at the door"],
            "Chemical or cold burns": ["Deluge shower and eye wash", "Chemical-resistant PPE"],
            "Flammable atmosphere and explosion": [],
            "Off-site community exposure": ["Exclusion zoning", "Community warning arrangement"],
        },
    )
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.metric("Preventive barriers", b["n_preventive"])
    c2.metric("Mitigative barriers", b["n_mitigative"])
    c3.metric("Unbarriered lines", len(b["gaps"]))

    st.dataframe(pd.DataFrame(b["gaps"]), width="stretch", hide_index=True)
    st.error(
        "**Corrosion under insulation has no preventive barrier, and a flammable "
        "atmosphere has no mitigative barrier.** Ammonia is flammable between 15% and "
        "28% by volume in air, and corrosion under insulation is the failure mode "
        "least likely to be found by a visual walk-round. These two lines are the "
        "action, and they are visible in seconds because the model was drawn."
    )
