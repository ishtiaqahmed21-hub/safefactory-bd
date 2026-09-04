"""Ambient exposure analytics — turning an air-quality dataset into an HSE control."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import theme as T
from safefactory.config import (
    BD_NAAQS_PM25_ANNUAL,
    BD_NAAQS_PM25_DAILY,
    WHO_PM25_ANNUAL,
    WHO_PM25_DAILY,
)

T.setup("Exposure")
st.title("Ambient Exposure & Outdoor Work Scheduling")
st.caption("ISO 45001:2018 clauses 6.1.2 and 9.1.1 · Environment Conservation Act 1995 "
           "· Bangladesh Labour Act 2006 s. 79c")

if not T.guard():
    st.stop()

city_air = T.load("city_air_summary")
monthly = T.load("air_monthly_profile")
diurnal = T.load("air_diurnal_profile")
shifts = T.load("air_shift_exposure")
adjust = T.load("air_dhaka_work_adjustment")
aqi_dist = T.load("air_aqi_distribution")

T.note(
    "Most HSE functions treat the 'E' in HSE as effluent and stack emissions only. "
    "Ambient air is the exposure every outdoor worker on the site takes all shift, "
    "every shift, and it is measurable. This page turns 1.05 million hourly records "
    "into three operational answers: what the workforce breathes, when it is worst, "
    "and how many shift-days a year a work-adjustment protocol would actually fire."
)

city = st.selectbox(
    "Reference location", sorted(city_air["city_name"]),
    index=sorted(city_air["city_name"]).index("Dhaka")
    if "Dhaka" in set(city_air["city_name"]) else 0,
)
row = city_air[city_air["city_name"] == city].iloc[0]

T.tiles([
    ("Mean PM2.5", f"{row['mean_pm2_5']:.1f}", "µg/m³ over the common window"),
    ("Against WHO annual", f"{row['mean_pm2_5'] / WHO_PM25_ANNUAL:.1f}×",
     f"guideline is {WHO_PM25_ANNUAL:.0f} µg/m³"),
    ("Against BD standard", f"{row['mean_pm2_5'] / BD_NAAQS_PM25_ANNUAL:.1f}×",
     f"national standard is {BD_NAAQS_PM25_ANNUAL:.0f} µg/m³"),
    ("Days over WHO 24-h guideline", f"{row['pct_days_over_who_pm25']:.0f}%",
     f"of valid days above {WHO_PM25_DAILY:.0f} µg/m³"),
    ("Mean AQI", f"{row['mean_aqi']:.0f}", "US EPA scale"),
])

st.caption(
    f"All cross-city figures are computed over the window "
    f"**{row['window_start']} to {row['window_end']}**, which every city in the "
    "dataset shares. Averaging each city over its own record length would compare "
    "a 26-year mean against a 3-year one and then rank sites on the difference."
)

# --------------------------------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("When in the year")
    m = monthly[monthly["city_name"] == city].sort_values("month")
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure()
    fig.add_scatter(
        x=names, y=m["mean_pm25"], mode="lines+markers", name="Mean PM2.5",
        line=dict(color=T.SERIES[0], width=2), marker=dict(size=9),
        hovertemplate="%{x}<br>Mean PM2.5 %{y:.1f} µg/m³<extra></extra>",
    )
    fig.add_scatter(
        x=names, y=m["p95_pm25"], mode="lines+markers", name="95th percentile",
        line=dict(color=T.SERIES[1], width=2, dash="dash"), marker=dict(size=8),
        hovertemplate="%{x}<br>95th percentile %{y:.1f} µg/m³<extra></extra>",
    )
    fig.add_hline(y=WHO_PM25_DAILY, line=dict(color=T.INK_MUTED, width=1, dash="dot"))
    fig.add_annotation(x=names[-1], y=WHO_PM25_DAILY, text="WHO 24-h guideline",
                       showarrow=False, yshift=11, xanchor="right",
                       font=dict(color=T.INK_MUTED, size=10))
    fig.update_layout(**T.layout(f"Seasonal profile — {city}", height=360),
                      hovermode="x unified")
    fig.update_yaxes(title="PM2.5 (µg/m³)")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "The dry-season peak is the scheduling target: heavy outdoor work, external "
        "contractor projects and non-urgent yard tasks move out of the worst months "
        "wherever the production plan allows."
    )

with c2:
    st.subheader("When in the day")
    dd = diurnal[diurnal["city_name"] == city].sort_values("hour")
    fig = go.Figure()
    fig.add_scatter(
        x=dd["hour"], y=dd["mean_pm25"], mode="lines+markers", name="Mean PM2.5",
        line=dict(color=T.SERIES[0], width=2), marker=dict(size=7),
        hovertemplate="%{x}:00<br>Mean PM2.5 %{y:.1f} µg/m³<extra></extra>",
    )
    fig.add_scatter(
        x=dd["hour"], y=dd["p95_pm25"], mode="lines", name="95th percentile",
        line=dict(color=T.SERIES[1], width=2, dash="dash"),
        hovertemplate="%{x}:00<br>95th percentile %{y:.1f} µg/m³<extra></extra>",
    )
    fig.update_layout(**T.layout(f"Diurnal profile — {city}", height=360),
                      hovermode="x unified")
    fig.update_xaxes(title="Hour of day", dtick=3)
    fig.update_yaxes(title="PM2.5 (µg/m³)")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Where the profile has a clear trough, outdoor tasks that can move — yard "
        "maintenance, external painting, roof work — should be scheduled into it."
    )

# --------------------------------------------------------------------------
st.subheader("Exposure by shift")
sh = shifts[shifts["city_name"] == city]
fig = go.Figure(
    go.Bar(
        x=sh["shift"], y=sh["mean_pm2_5"],
        marker_color=T.SERIES[0], marker_line=dict(color=T.SURFACE, width=2),
        text=[f"{v:.1f} µg/m³  ({r:.1f}× WHO 24-h)"
              for v, r in zip(sh["mean_pm2_5"], sh["vs_who_daily_guideline"])],
        textposition="outside", textfont=dict(color=T.INK_SECONDARY, size=11),
        hovertemplate="%{x}<br>Mean PM2.5 %{y:.1f} µg/m³<extra></extra>",
        showlegend=False,
    )
)
fig.add_hline(y=WHO_PM25_DAILY, line=dict(color=T.INK_MUTED, width=1, dash="dot"))
fig.update_layout(**T.layout("Mean PM2.5 by working shift", height=320))
fig.update_yaxes(title="PM2.5 (µg/m³)")
st.plotly_chart(fig, width="stretch")
st.caption(
    "Shift-level exposure differences are what justify — or fail to justify — "
    "rotating outdoor assignments between shifts. Where the difference is small, "
    "rotation buys nothing and the control has to be engineering or respiratory."
)

# --------------------------------------------------------------------------
st.subheader("Would a work-adjustment protocol be workable?")
trigger = st.slider(
    "Trigger the protocol at AQI", 100, 250, 150, 10,
    help="US EPA AQI 151 and above is 'Unhealthy' for the general population.",
)

adj = T.load("air_dhaka_work_adjustment")
adj = adj.copy()
adj["ym"] = adj["year"].astype(str) + "-" + adj["month"].astype(str).str.zfill(2)
by_month = adj.groupby("month").agg(
    days=("days", "sum"), trigger_days=("trigger_days", "sum")
).reset_index()
by_month["pct"] = (by_month["trigger_days"] / by_month["days"] * 100).round(1)
names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

fig = go.Figure(
    go.Bar(
        x=[names[m - 1] for m in by_month["month"]], y=by_month["pct"],
        marker_color=T.SERIES[0], marker_line=dict(color=T.SURFACE, width=2),
        text=[f"{p:.0f}%" for p in by_month["pct"]],
        textposition="outside", textfont=dict(color=T.INK_SECONDARY, size=11),
        hovertemplate=("%{x}<br>%{y:.0f}% of days would trigger"
                       "<br>%{customdata} trigger-days recorded<extra></extra>"),
        customdata=by_month["trigger_days"], showlegend=False,
    )
)
fig.update_layout(**T.layout(
    "Share of days that would trigger the protocol, Dhaka reference", height=340))
fig.update_yaxes(title="% of days", range=[0, 108])
st.plotly_chart(fig, width="stretch")

total_days = int(adj["days"].sum())
total_trigger = int(adj["trigger_days"].sum())
pct = total_trigger / total_days * 100
worst = by_month.loc[by_month["pct"].idxmax()]
best = by_month.loc[by_month["pct"].idxmin()]

st.markdown(
    f"Across the analysis window, **{total_trigger:,} of {total_days:,} valid days "
    f"({pct:.0f}%)** sit at or above AQI 150 at the Dhaka reference point. The load "
    f"is strongly seasonal: **{names[int(worst['month']) - 1]} triggers on "
    f"{worst['pct']:.0f}% of days, {names[int(best['month']) - 1]} on "
    f"{best['pct']:.0f}%.**\n\n"
    "That shape is what makes the control designable. A protocol firing on a third "
    "of all days, concentrated into a predictable dry-season window, is one a plant "
    "can actually run: heavy outdoor work, external contractor projects and "
    "non-urgent yard tasks move out of the peak months, and the administrative "
    "trigger handles the residue. Had the figure come out at 80% of days, the "
    "honest conclusion would have been the opposite — that a day-by-day trigger is "
    "theatre and the money belongs in engineering controls instead: an enclosed and "
    "positively pressurised gatehouse and loading office, and filtered fresh-air "
    "intakes sited away from stack downwash.\n\n"
    "**Running this calculation before writing the procedure is the difference "
    "between a control that works and one that is ignored by week three.**"
)
st.caption(
    "The slider above changes the trigger for illustration; the chart is built on "
    "the stored AQI 150 calculation. Rebuild with a different threshold in "
    "`scripts/build_dataset.py` to move the underlying figures. All figures on this "
    "page use the screened analysis window — the pre-2022 Dhaka segment failed the "
    "integrity screen and is excluded throughout. See the Data & Method page."
)

# --------------------------------------------------------------------------
with st.expander("How every city compares over the common window"):
    d = city_air.sort_values("mean_pm2_5", ascending=False)
    fig = go.Figure(
        go.Bar(
            x=d["mean_pm2_5"], y=d["city_name"], orientation="h",
            marker_color=T.SERIES[0], marker_line=dict(color=T.SURFACE, width=2),
            hovertemplate=("%{y}<br>Mean PM2.5 %{x:.1f} µg/m³"
                           "<br>%{customdata:.0f}% of days over the WHO 24-h "
                           "guideline<extra></extra>"),
            customdata=d["pct_days_over_who_pm25"], showlegend=False,
        )
    )
    fig.add_vline(x=BD_NAAQS_PM25_ANNUAL,
                  line=dict(color=T.STATUS["warning"], width=2, dash="dash"))
    fig.add_vline(x=WHO_PM25_ANNUAL,
                  line=dict(color=T.STATUS["critical"], width=2, dash="dot"))
    fig.update_layout(**T.layout("Mean PM2.5 by city, common window", height=640))
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(title="PM2.5 (µg/m³)")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"Dashed line: Bangladesh national annual standard, {BD_NAAQS_PM25_ANNUAL:.0f} "
        f"µg/m³. Dotted line: WHO annual guideline, {WHO_PM25_ANNUAL:.0f} µg/m³. "
        "Every city in the dataset sits above both."
    )
    st.dataframe(city_air.sort_values("mean_pm2_5", ascending=False),
                 width="stretch", hide_index=True)

with st.expander("Share of hours in each AQI category"):
    st.dataframe(aqi_dist, width="stretch", hide_index=True)
