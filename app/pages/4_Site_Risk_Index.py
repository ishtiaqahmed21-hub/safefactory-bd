"""Composite Site HSE Risk Index — the location-screening layer."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import theme as T
from safefactory.config import SITE_INDEX_WEIGHTS

T.setup("Site Risk Index")
st.title("Composite Site HSE Risk Index")
st.caption("A screening score for industrial locations, built only from open data "
           "that can be refreshed")

if not T.guard():
    st.stop()

idx = T.load("site_risk_index")
weights = T.load("site_index_weight_sensitivity")
radii = T.load("site_index_radius_sensitivity")

T.note(
    "This index ranks locations <b>relative to each other</b>. It is a screening "
    "tool for site selection, emergency planning and mutual-aid scoping — not an "
    "absolute measure of harm, and never a substitute for a site survey. Its "
    "weights are declared, and the sensitivity tab tests whether the ranking "
    "survives changing them."
)

tab_rank, tab_components, tab_sens, tab_neighbours = st.tabs(
    ["Ranking", "What drives each score", "Does the ranking hold?", "Who is next door"]
)

# --------------------------------------------------------------------------
with tab_rank:
    top = idx.iloc[0]
    nz = idx[idx["site_name"].str.startswith("NZDP")]
    T.tiles([
        ("Sites screened", f"{len(idx)}", "two operating sites plus comparators"),
        ("Highest score", f"{top['cshri']:.1f}", f"{top['site_name']} · {top['band']}"),
        ("Highest NZDP site", f"{nz['cshri'].max():.1f}",
         f"{nz.loc[nz['cshri'].idxmax(), 'site_name']}"),
    ])

    fig = go.Figure(
        go.Bar(
            x=idx["cshri"], y=idx["site_name"], orientation="h",
            marker_color=[T.INDEX_BAND_COLOR[b] for b in idx["band"]],
            marker_line=dict(color=T.SURFACE, width=2),
            text=[f"{v:.1f}  {b}" for v, b in zip(idx["cshri"], idx["band"])],
            textposition="outside", textfont=dict(color=T.INK_SECONDARY, size=11),
            hovertemplate=("%{y}<br>Index %{x:.1f}<br>"
                           "Dominant driver: %{customdata}<extra></extra>"),
            customdata=idx["dominant_component"], showlegend=False,
        )
    )
    fig.update_layout(**T.layout("Composite Site HSE Risk Index (0–100)", height=460))
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(title="Index", range=[0, 108])
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Bar colour is the band and the band name is printed on every bar, so the "
        "reading never depends on colour alone. Bands: Low under 25 · Moderate 25–50 "
        "· Elevated 50–75 · High 75 and above."
    )

    st.dataframe(
        idx[["site_name", "district", "cshri", "band", "dominant_component",
             "facilities_within_r", "workers_within_r", "nearest_monitor_city",
             "monitor_distance_km", "monitor_representative", "mean_pm2_5",
             "urban_centre_km", "guidance"]].rename(columns={
            "site_name": "Site", "district": "District", "cshri": "Index",
            "band": "Band", "dominant_component": "Dominant driver",
            "facilities_within_r": "Plants within 10 km",
            "workers_within_r": "Workers within 10 km",
            "nearest_monitor_city": "Nearest air monitor",
            "monitor_distance_km": "Monitor distance (km)",
            "monitor_representative": "Monitor representative",
            "mean_pm2_5": "Mean PM2.5 (µg/m³)",
            "urban_centre_km": "To urban centre (km)", "guidance": "Guidance",
        }),
        width="stretch", hide_index=True,
    )
    st.caption(
        "**Monitor representative** is false where the nearest air-quality grid point "
        "is more than 30 km away. Those sites are not characterised by that monitor, "
        "and the table says so rather than hiding it."
    )

# --------------------------------------------------------------------------
with tab_components:
    st.subheader("Component contribution to each site's score")
    comps = [
        ("score_ambient_air", "Ambient air burden", SITE_INDEX_WEIGHTS["ambient_air"]),
        ("score_industrial_density", "Industrial density", SITE_INDEX_WEIGHTS["industrial_density"]),
        ("score_worker_concentration", "Worker concentration", SITE_INDEX_WEIGHTS["worker_concentration"]),
        ("score_emergency_access", "Emergency access", SITE_INDEX_WEIGHTS["emergency_access"]),
    ]
    d = idx.sort_values("cshri")
    fig = go.Figure()
    for i, (col, label, w) in enumerate(comps):
        fig.add_bar(
            name=f"{label} ({w:.0%})",
            x=d[col] * w, y=d["site_name"], orientation="h",
            marker_color=T.SERIES[i], marker_line=dict(color=T.SURFACE, width=2),
            hovertemplate=("%{y}<br>" + label +
                           ": %{customdata:.0f} raw → %{x:.1f} weighted<extra></extra>"),
            customdata=d[col],
        )
    fig.update_layout(**T.layout("Weighted contribution to the index", height=480),
                      barmode="stack", bargap=0.3)
    fig.update_xaxes(title="Weighted index points")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Segments are ordered identically on every bar, and each is labelled in the "
        "legend with the weight it carries, so a reader can reconstruct any score by "
        "hand."
    )

    st.markdown("""
**What each component measures, and why it is in the index**

| Component | Weight | What it measures | Why it belongs |
|---|---|---|---|
| Ambient air burden | 30% | Mean PM2.5 at the nearest monitored grid point over the common window | Chronic exposure of yard, loading and security staff, and the load drawn into every air intake on site. Measured, not assumed. |
| Industrial density | 25% | Registered industrial facilities within 10 km | A fire, release or explosion next door becomes your emergency. Also proxies congestion on the approach route. |
| Worker concentration | 25% | Reported workers at those facilities | Population inside the same response envelope; determines how fast the district's emergency capacity saturates. |
| Emergency access | 20% | Distance to the nearest significant urban centre | A transparent proxy for fire-service and trauma-care response time. |

**The honest weakness.** The emergency-access component does not know where fire
stations actually are. It uses distance to an urban centre as a stand-in. Replace
it with the Fire Service and Civil Defence station list and this component becomes
a real drive-time estimate rather than a proxy — that is the single highest-value
improvement available to this index.
""")

# --------------------------------------------------------------------------
with tab_sens:
    st.subheader("Does the ranking survive a different set of weights?")
    T.note(
        "A composite index whose ranking flips the moment the weights move is not "
        "telling you much. Five weighting schemes are run: the declared baseline, "
        "equal weights, and one scheme per component dominating at 55%."
    )
    w = weights.copy()
    st.dataframe(w, width="stretch", hide_index=True)
    stable = int(w["stable"].sum())
    if stable == len(w):
        st.success(
            f"**Every one of the {len(w)} sites moves by no more than one rank position "
            "across all five weighting schemes.** The ranking is robust to the weights."
        )
    else:
        st.warning(
            f"**{len(w) - stable} of {len(w)} sites move by more than one rank position** "
            "when the weights change. Those sites' positions should be quoted with "
            "that caveat attached."
        )

    st.subheader("And a different neighbourhood radius?")
    fig = go.Figure()
    for i, site in enumerate(idx["site_name"].head(6)):
        s = radii[radii["site_name"] == site]
        fig.add_scatter(
            x=s["radius_km"], y=s["cshri"], mode="lines+markers", name=site,
            line=dict(color=T.SERIES[i % len(T.SERIES)], width=2),
            marker=dict(size=9, line=dict(color=T.SURFACE, width=2)),
            hovertemplate="%{fullData.name}<br>%{x} km radius → index %{y:.1f}<extra></extra>",
        )
    fig.update_layout(**T.layout("Index against neighbourhood radius", height=380),
                      hovermode="x unified")
    fig.update_xaxes(title="Radius (km)", dtick=5)
    fig.update_yaxes(title="Index")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "The six highest-scoring sites are shown; beyond six series a legend stops "
        "being readable, so the rest are in the table on the Ranking tab."
    )

# --------------------------------------------------------------------------
with tab_neighbours:
    st.subheader("The plants inside the response envelope")
    T.note(
        "This is what turns a density score into an action: the named list of sites a "
        "mutual-aid agreement, a joint evacuation plan and a shared emergency-access "
        "route should cover."
    )
    which = st.radio(
        "Site", ["S01", "S02"], horizontal=True,
        format_func=lambda s: {
            "S01": "NZDP Factory 1 — Vulta, Rupganj, Narayanganj",
            "S02": "NZDP Factory 2 — Jangalipara, Gazipur",
        }[s],
    )
    nb = T.load(f"neighbours_{which}")
    st.caption(f"{len(nb)} nearest facilities within 10 km, closest first.")
    st.dataframe(nb, width="stretch", hide_index=True, height=420)

    st.warning(
        "**Coordinate precision.** Both NZDP site coordinates are geocoded from the "
        "published postal address to sub-district level, not surveyed. They are good "
        "enough to screen a neighbourhood at a 10 km radius; they are not good enough "
        "for a dispersion model or an evacuation plan. Replace them with a surveyed "
        "coordinate before any operational use."
    )
