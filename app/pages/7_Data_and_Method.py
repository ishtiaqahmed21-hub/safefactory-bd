"""Data provenance, integrity screening results, and stated limitations."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import theme as T

T.setup("Data & Method")
st.title("Data, Method & What This Does Not Show")
st.caption("Every figure in this system traces to a source on this page")

if not T.guard():
    st.stop()

tab_sources, tab_qa, tab_limits = st.tabs(
    ["Sources", "Integrity screening", "Limitations"]
)

# --------------------------------------------------------------------------
with tab_sources:
    st.subheader("National HSE statistics")
    st.caption(
        "Used for benchmarking and to justify which hazards the register treats as "
        "priorities. Every row carries its source organisation and URL."
    )
    ns = T.load("national_hse_statistics", folder="reference")
    st.dataframe(ns, width="stretch", hide_index=True, height=420)

    T.note(
        "<b>Two national fatality counts exist for 2025 and they must never be summed "
        "or swapped.</b> The Safety and Rights Society reports 802 deaths in 713 "
        "accidents, compiled from 15 national and 11 local newspapers. The OSHE "
        "Foundation reports 1,190, with 84% in the informal sector. They use different "
        "methodologies and different scopes. Both under-count, because both depend on "
        "an event being reported. Any benchmark quoted from either must name which one "
        "it came from.", kind="warn")

    st.subheader("Datasets")
    st.markdown("""
| Dataset | What it is | Size | Used for |
|---|---|---|---|
| National hourly air quality | Hourly PM2.5, PM10, CO, NO₂, SO₂, O₃ and AQI by city | 1,048,551 rows, 30 named city points, 2000–2025 | Ambient exposure analysis, the air component of the site index |
| Open industrial facility registry | Geocoded apparel and textile facilities in Bangladesh with reported worker counts | 2,123 facilities, 968 with a worker count | Industrial density and worker concentration in the site index; neighbour profiles |
| City reference points | Named populated places with coordinates | 103 places | Emergency-access proxy in the site index |
| BBS Labour Force Survey 2022, and Quarterly LFS 2015-16 and 2023 | National labour statistics including the occupational safety and health module | Full report text | Context on the national workforce and the OSH module's design |
| CPD / FES post-Accord industrial safety study | Institutional analysis of DIFE, RSC, RCC and Nirapon after the Accord–Alliance period | Full report text | Regulatory capacity figures; the Safety Committee functionality finding |
""")

    st.subheader("Reference values used in the risk assessment")
    st.markdown("""
| Value | Figure | Source |
|---|---|---|
| Ammonia, OSHA permissible exposure limit (8-h TWA) | 50 ppm | OSHA Table Z-1 |
| Ammonia, NIOSH recommended exposure limit (TWA) | 25 ppm | NIOSH |
| Ammonia, NIOSH short-term exposure limit | 35 ppm | NIOSH |
| Ammonia, immediately dangerous to life or health | 300 ppm | NIOSH IDLH, revised from 500 ppm |
| Ammonia, lower explosive limit | 15% by volume in air | NIOSH |
| Oxygen, acceptable range for entry | 19.5% – 23.5% | Standard entry criterion |
| Noise action level | 85 dB(A) | Standard occupational action level |
| WHO PM2.5 guideline | 5 µg/m³ annual, 15 µg/m³ 24-hour | WHO Global Air Quality Guidelines 2021 |
| Bangladesh PM2.5 standard | 15 µg/m³ annual, 65 µg/m³ 24-hour | Environment Conservation Rules 1997, Schedule 2 as amended |
| Fatality day charge for severity rate | 6,000 days | ANSI Z16.1 convention |
""")

    st.subheader("Data-fetch manifest")
    st.caption(
        "The full manifest of Bangladeshi HSE data sources this project can pull "
        "from, including those not yet used. Sources marked `manual` require a free "
        "account and a stated research purpose."
    )
    st.dataframe(T.load("data_sources_manifest", folder="reference"),
                 width="stretch", hide_index=True, height=320)

# --------------------------------------------------------------------------
with tab_qa:
    st.subheader("Two defects found in the source air-quality dataset")
    T.note(
        "These were found by inspection and are now detected automatically, so any "
        "refreshed copy of the dataset is screened before it is used. Both would have "
        "silently corrupted every downstream figure, and neither is visible in a "
        "summary statistic.", kind="crit")

    st.markdown("### Defect 1 — duplicate series presented as separate cities")
    dup = T.load("qa_duplicate_series")
    st.dataframe(dup, width="stretch", hide_index=True)
    ind = T.load("qa_independent_cities")
    st.markdown(
        f"The file names 30 cities. **{len(dup)} pairs carry a byte-identical hourly "
        f"record**, leaving **{len(ind)} independent series**. The dataset is a "
        "gridded product: city points falling in the same model cell share one series. "
        "One pair sits 3.1 km apart, which is unsurprising — but two sit over 30 km "
        "apart, which tells you the grid is coarse. Treating all 30 as independent "
        "locations inflates the apparent sample and lets one grid cell vote three "
        "times in a cross-city ranking."
    )

    st.markdown("### Defect 2 — a synthetic segment in the long Dhaka record")
    trend = T.load("air_dhaka_annual_trend")
    screen = T.load("qa_backfill_screen")
    segs = T.load("qa_dhaka_segments")

    fig = go.Figure()
    synth = trend[trend["year"] <= 2021]
    real = trend[trend["year"] >= 2022]
    fig.add_scatter(
        x=synth["year"], y=synth["mean_pm25"], mode="lines+markers",
        name="2000–2021 — fails the screen",
        line=dict(color=T.STATUS["critical"], width=2), marker=dict(size=8),
        hovertemplate="%{x}<br>%{y:.1f} µg/m³<extra></extra>",
    )
    fig.add_scatter(
        x=real["year"], y=real["mean_pm25"], mode="lines+markers",
        name="2022–2025 — the usable segment",
        line=dict(color=T.SERIES[0], width=2), marker=dict(size=8),
        hovertemplate="%{x}<br>%{y:.1f} µg/m³<extra></extra>",
    )
    fig.update_layout(**T.layout("Dhaka annual mean PM2.5 as published", height=380),
                      hovermode="x unified")
    fig.update_yaxes(title="Annual mean PM2.5 (µg/m³)")
    fig.update_xaxes(title="Year", dtick=3)
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        "The 2000–2021 segment rises **monotonically every single year** — a "
        "monotone fraction of 1.00 and a linear R² of 0.994 — then steps down by "
        "68 µg/m³ into a segment with a coefficient of variation of 0.03. Real "
        "ambient particulate records do not behave like this: they carry strong, "
        "irregular year-to-year variation driven by monsoon timing and meteorology. "
        "A near-perfect ramp is the signature of interpolated or modelled back-fill, "
        "and a trend fitted through it measures the interpolation, not the air.\n\n"
        "**A published '+2.6 µg/m³ per year over 26 years' finding sits right there "
        "for the taking, and it would have been wrong.** The pipeline now refuses "
        "to report it."
    )
    c1, c2 = st.columns(2)
    c1.markdown("**Segment screening**")
    c1.dataframe(screen, width="stretch", hide_index=True)
    c2.markdown("**Segment statistics**")
    c2.dataframe(segs, width="stretch", hide_index=True)

    slope = T.load("air_dhaka_trend_slope")
    st.markdown("**What the pipeline concluded**")
    st.dataframe(slope, width="stretch", hide_index=True)

    st.markdown(
        "**Why the screen segments first.** Running the test on the whole 26-year "
        "series returns a monotone fraction of 0.84 and an R² of 0.27 — which reads "
        "as 'no problem'. The real, noisy tail hides the synthetic head. The series "
        "must be split at its discontinuities and each segment tested on its own. "
        "That behaviour is covered by a unit test."
    )

    st.subheader("Completeness")
    st.dataframe(T.load("qa_completeness"), width="stretch", hide_index=True)
    st.caption(
        "Carbon dioxide is missing for 74% of records and is not used anywhere in "
        "this system. Small negative values appear in the nitrogen dioxide and ozone "
        "columns, consistent with a modelled product rather than an instrument "
        "reading."
    )

    st.subheader("Coverage by city")
    st.dataframe(T.load("air_coverage"), width="stretch", hide_index=True,
                 height=360)

# --------------------------------------------------------------------------
with tab_limits:
    st.markdown("""
## What this system does not show

Stating these plainly is not a weakness in the work. An HSE professional who
cannot say where their own numbers stop being trustworthy is a liability, and
every item below is something an interviewer is entitled to ask about.

### The incident data is synthetic
The incident register is generated, seeded and reproducible. It exists so the
dashboard has something to display before a plant loads its own records. No
conclusion about any real plant's injury performance can be drawn from it. The
metric definitions, classification rules and investigation logic are real.

### The risk assessment has not been validated on site
The HIRA register is built from the published description of the company's
operations — milk powder, instant noodles, fried snacks, wafers and biscuits —
combined with the standard hazard profile of dairy and food processing. It is a
credible starting register and a demonstration of method. It is **not** a site
assessment. A real HIRA requires a walk-through with the people who do the work,
and several hazards in this register would change or disappear once the actual
plant is seen. The likelihood and severity scores are the author's judgement, not
measurements.

### Site coordinates are geocoded, not surveyed
Both factory coordinates come from the published postal address at sub-district
level. They are adequate to screen a neighbourhood at a 10 km radius. They are
**not** adequate for a dispersion model, an evacuation plan, or anything where
being 2 km out matters.

### The air-quality data is a gridded product, not station measurements
It is a model or reanalysis output interpolated onto city points, which is why
two named cities 30 km apart can return identical hourly values. It is fit for
comparing the relative ambient burden of locations and for characterising the
seasonal and diurnal shape of exposure. It is **not** a substitute for a monitor
at the site boundary, and no regulatory compliance claim should be made from it.
All cross-city figures use the window every city shares, 2022-08-05 to 2025-11-23;
the pre-2022 Dhaka segment is excluded entirely.

### The facility registry is partial and sector-skewed
The registry covers apparel and textile facilities, so it under-counts food,
pharmaceutical, chemical and engineering plants. Industrial density in the site
index is therefore a **lower bound**, and it is a better proxy in the ready-made
garment belt than elsewhere. Worker counts are reported by the facilities
themselves and are present for only 968 of 2,123 sites; ranges such as
'1001–5000' are reduced to their midpoint.

### The emergency-access component is a proxy
It measures distance to the nearest significant urban centre. It does not know
where fire stations are, what the roads are like, or how long an ambulance
actually takes. Substituting the Fire Service and Civil Defence station list is
the single highest-value improvement available to the index.

### The index weights are a judgement
They are declared in `config.py` and are meant to be argued with. The sensitivity
analysis exists so that the argument can be settled with evidence rather than
opinion: if the ranking holds across five weighting schemes, the weights are not
doing the work.

### The national fatality statistics under-count, and they disagree
Both the SRS and OSHE figures are derived from reported events — newspapers and
clinic records — so both miss what is never reported. They are the best national
picture available and they should be used as an order of magnitude, not as a
precise denominator.

### Compliance scoring is a self-assessment tool
The conformity index is only as good as the honesty of the person setting each
status. It structures and weights a judgement; it does not replace a third-party
audit, and it does not confer certification.
""")
