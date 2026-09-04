"""HIRA risk register: the 5x5 matrix, the register itself, and control quality."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import theme as T
from safefactory.risk import RiskRegister, matrix_reference, scale_definitions

T.setup("Risk Register")
st.title("Hazard Identification & Risk Assessment")
st.caption("ISO 45001:2018 clause 6.1.2 · Bangladesh Labour Act 2006 ss. 61–62 · "
           "Bangladesh Labour Rules 2015 r. 68")

if not T.guard():
    st.stop()

reg = RiskRegister.from_csv()

stage = st.radio(
    "Risk state",
    ["current", "initial", "residual"],
    horizontal=True,
    format_func=lambda s: {
        "current": "Current (credits only installed controls)",
        "initial": "Inherent (no controls)",
        "residual": "Target (full control plan in place)",
    }[s],
)
band_col = "risk_band_current" if stage == "current" else f"risk_band_{stage}"
score_col = "risk_score_current" if stage == "current" else f"risk_score_{stage}"

counts = reg.df[band_col].value_counts()
T.tiles([
    ("Hazards assessed", f"{len(reg.df)}", f"across {reg.df['area'].nunique()} areas"),
    ("Critical", f"{counts.get('Critical', 0)}", "stop or restrict the activity"),
    ("High", f"{counts.get('High', 0)}", "additional controls within 30 days"),
    ("Medium", f"{counts.get('Medium', 0)}", "tolerable if ALARP"),
    ("Low", f"{counts.get('Low', 0)}", "monitor and maintain"),
])

# --------------------------------------------------------------------------
# The matrix
# --------------------------------------------------------------------------
left, right = st.columns([1, 1])

with left:
    st.subheader("Risk matrix")
    if stage == "current":
        st.caption(
            "The current state has no separate likelihood and severity pair, so the "
            "matrix is drawn for the inherent assessment. Switch state above to "
            "plot the target."
        )
        plot_stage = "initial"
    else:
        plot_stage = stage
    m = reg.matrix(plot_stage)
    ref = matrix_reference()
    band_grid = ref.pivot(index="severity", columns="likelihood", values="band")

    # The cell colour encodes the BAND (a state), so it comes from the reserved
    # status palette, not from a sequential ramp. The count is written into the
    # cell, so meaning never rests on colour alone.
    band_num = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
    z = band_grid.map(band_num.get).values
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[f"{i}" for i in range(1, 6)],
            y=[f"{i}" for i in range(1, 6)],
            colorscale=[
                [0.00, T.BAND_COLOR["Low"]], [0.24, T.BAND_COLOR["Low"]],
                [0.25, T.BAND_COLOR["Medium"]], [0.49, T.BAND_COLOR["Medium"]],
                [0.50, T.BAND_COLOR["High"]], [0.74, T.BAND_COLOR["High"]],
                [0.75, T.BAND_COLOR["Critical"]], [1.00, T.BAND_COLOR["Critical"]],
            ],
            showscale=False,
            xgap=2, ygap=2,
            hovertemplate=(
                "Likelihood %{x} × Severity %{y}<br>%{customdata} hazards<extra></extra>"
            ),
            customdata=m.values,
        )
    )
    for si, s in enumerate(range(1, 6)):
        for li, l in enumerate(range(1, 6)):
            n = int(m.loc[s, l])
            fig.add_annotation(
                x=str(l), y=str(s), text=str(n) if n else "·",
                showarrow=False,
                font=dict(color="#ffffff" if n else "rgba(255,255,255,0.55)",
                          size=15 if n else 12, family=T.FONT),
            )
    fig.update_layout(**T.layout(f"Hazard count by cell ({plot_stage})", height=520))
    fig.update_xaxes(title="Likelihood  1 rare → 5 almost certain", side="bottom")
    fig.update_yaxes(title="Severity  1 negligible → 5 catastrophic")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Cell colour is the risk band — green Low, amber Medium, orange High, "
        "red Critical — and the number in each cell is the hazard count, so the "
        "reading never depends on colour alone."
    )

with right:
    st.subheader("Residual risk by area")
    ba = reg.by_area().reset_index()
    fig = go.Figure(
        go.Bar(
            x=ba["total_residual"], y=ba["area"], orientation="h",
            marker_color=T.SERIES[0], marker_line=dict(color=T.SURFACE, width=2),
            text=ba["hazards"].map(lambda n: f"{n} hazards"),
            textposition="outside", textfont=dict(color=T.INK_SECONDARY, size=10),
            hovertemplate=("%{y}<br>Total residual risk: %{x}"
                           "<br>Mean residual: %{customdata:.1f}<extra></extra>"),
            customdata=ba["mean_residual"],
        )
    )
    fig.update_layout(**T.layout("Total residual risk points, target state", height=520))
    fig.update_yaxes(categoryorder="total ascending", tickfont=dict(size=10))
    # Leave headroom so the outside bar labels sit inside the plot area.
    fig.update_xaxes(title="Sum of residual risk scores",
                     range=[0, ba["total_residual"].max() * 1.35])
    fig.update_traces(cliponaxis=False)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Summed rather than averaged, so an area with many moderate hazards is not "
        "hidden behind an area with one severe one."
    )

# --------------------------------------------------------------------------
# Control quality
# --------------------------------------------------------------------------
st.subheader("Control quality — how far up the hierarchy each plan reaches")
ce = reg.df[["hazard_id", "area", "control_hierarchy", "control_effectiveness",
             "risk_score_residual"]].copy()
fig = go.Figure(
    go.Scatter(
        x=ce["control_effectiveness"], y=ce["risk_score_residual"],
        mode="markers", marker=dict(size=11, color=T.SERIES[0],
                                    line=dict(color=T.SURFACE, width=2)),
        text=ce["hazard_id"],
        hovertemplate=("%{text}<br>Control effectiveness: %{x:.2f}"
                       "<br>Residual risk: %{y}<extra></extra>"),
        showlegend=False,
    )
)
fig.add_vline(x=0.5, line=dict(color=T.STATUS["warning"], width=2, dash="dash"))
fig.add_annotation(x=0.5, y=ce["risk_score_residual"].max(),
                   text="  PPE / procedure reliance →", showarrow=False,
                   xanchor="right", font=dict(color=T.INK_MUTED, size=11))
fig.update_layout(**T.layout(
    "Residual risk against control-plan effectiveness", height=340))
fig.update_xaxes(title="Control effectiveness  (1.0 = elimination, 0.2 = PPE only)",
                 range=[0, 1.05])
fig.update_yaxes(title="Residual risk score")
st.plotly_chart(fig, width="stretch")
st.caption(
    "Points to the left of the dashed line rest mainly on procedure and personal "
    "protective equipment, which fail whenever a person does. A high residual risk "
    "sitting on a low-effectiveness plan is the clearest signal that a control was "
    "written for the audit file rather than for the hazard."
)

ppe = reg.ppe_reliance()
if len(ppe):
    T.note(
        f"<b>{len(ppe)} hazard(s)</b> combine a residual score of 6 or more with a "
        "control plan that leans on administrative measures or PPE. These are the "
        "first candidates for an engineering solution.", kind="warn")
    st.dataframe(ppe, width="stretch", hide_index=True)
else:
    T.note("No hazard combines meaningful residual risk with a PPE-only control plan.")

# --------------------------------------------------------------------------
# Register
# --------------------------------------------------------------------------
st.subheader("The register")
areas = st.multiselect("Filter by area", sorted(reg.df["area"].unique()))
bands = st.multiselect("Filter by band", T.BAND_ORDER)
d = reg.df
if areas:
    d = d[d["area"].isin(areas)]
if bands:
    d = d[d[band_col].isin(bands)]

st.dataframe(
    d[["hazard_id", "area", "activity", "hazard_category", "hazard_description",
       "potential_consequence", "existing_controls", "likelihood_initial",
       "severity_initial", score_col, band_col, "additional_controls",
       "control_hierarchy", "control_status", "legal_reference",
       "iso45001_clause", "responsible"]],
    width="stretch", hide_index=True, height=420,
)
st.download_button(
    "Download the register as CSV",
    d.to_csv(index=False).encode(),
    "hira_register.csv",
    "text/csv",
)

with st.expander("Scoring rules — the definitions an auditor will ask for"):
    lik, sev = scale_definitions()
    c1, c2 = st.columns(2)
    c1.markdown("**Likelihood**")
    c1.dataframe(lik, width="stretch", hide_index=True)
    c2.markdown("**Severity**")
    c2.dataframe(sev, width="stretch", hide_index=True)
    st.markdown(
        "**Bands.** Score is likelihood × severity, 1–25. "
        "1–4 Low · 5–9 Medium · 10–15 High · 16–25 Critical.\n\n"
        "**Fatality escalation.** A credible fatality scenario (severity 5) at "
        "likelihood 3 or above is never allowed to sit below High, whatever the "
        "arithmetic gives. This blocks the common failure of scoring a fatal "
        "hazard as tolerable because it is judged unlikely."
    )

with st.expander("Statutory coverage of the register"):
    st.dataframe(reg.legal_coverage().reset_index(), width="stretch",
                 hide_index=True)
