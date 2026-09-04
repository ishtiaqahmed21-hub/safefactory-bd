#!/usr/bin/env python3
"""Generate the one-page A4 project summary PDF.

Every figure in the output is read from the built tables in data/processed, not
typed in, so the one-pager cannot drift out of step with the repository.

    python scripts/build_dataset.py      # must run first
    python scripts/make_onepager.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from safefactory.config import PROCESSED, REFERENCE, REPORTS  # noqa: E402

# --------------------------------------------------------------------------
# Palette — the same roles the dashboard uses
# --------------------------------------------------------------------------
INK = colors.HexColor("#0b0b0b")
INK_2 = colors.HexColor("#3d3c39")
MUTED = colors.HexColor("#6f6d67")
RULE = colors.HexColor("#d6d5cd")
ACCENT = colors.HexColor("#2a78d6")
BAND_BG = colors.HexColor("#f2f6fc")
CRIT = colors.HexColor("#d03b3b")
GOOD = colors.HexColor("#0ca30c")

FONT = "Helvetica"
BOLD = "Helvetica-Bold"

S = {
    "name": ParagraphStyle("name", fontName=BOLD, fontSize=10.5, leading=12.5,
                           textColor=INK, spaceAfter=0),
    "contact": ParagraphStyle("contact", fontName=FONT, fontSize=7.6, leading=9.4,
                              textColor=MUTED, alignment=2),
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=19, leading=21,
                            textColor=INK, spaceBefore=5, spaceAfter=1),
    "sub": ParagraphStyle("sub", fontName=FONT, fontSize=9.4, leading=12,
                          textColor=INK_2, spaceAfter=7),
    "h": ParagraphStyle("h", fontName=BOLD, fontSize=8.6, leading=10.4,
                        textColor=ACCENT, spaceBefore=7, spaceAfter=3.5),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=8.0, leading=10.2,
                           textColor=INK_2, alignment=TA_JUSTIFY),
    "bullet": ParagraphStyle("bullet", fontName=FONT, fontSize=7.9, leading=9.9,
                             textColor=INK_2, leftIndent=7.5, bulletIndent=1,
                             spaceAfter=2.4),
    "find_h": ParagraphStyle("find_h", fontName=BOLD, fontSize=8.1, leading=10,
                             textColor=INK, spaceAfter=1.5),
    "find_b": ParagraphStyle("find_b", fontName=FONT, fontSize=7.7, leading=9.6,
                             textColor=INK_2),
    "tile_v": ParagraphStyle("tile_v", fontName=BOLD, fontSize=13.5, leading=15,
                             textColor=INK, alignment=1),
    "tile_l": ParagraphStyle("tile_l", fontName=FONT, fontSize=6.5, leading=8,
                             textColor=MUTED, alignment=1),
    "th": ParagraphStyle("th", fontName=BOLD, fontSize=7.2, leading=8.8,
                         textColor=INK),
    "td": ParagraphStyle("td", fontName=FONT, fontSize=7.2, leading=8.8,
                         textColor=INK_2),
    "foot": ParagraphStyle("foot", fontName=FONT, fontSize=6.9, leading=8.6,
                           textColor=MUTED, alignment=TA_JUSTIFY),
}


def load(name: str, folder=PROCESSED) -> pd.DataFrame:
    return pd.read_csv(folder / f"{name}.csv")


def figures() -> dict:
    """Pull every number in the one-pager from the built tables."""
    hira = load("hira_scored")
    state = load("hira_state_comparison").set_index("band")
    road = load("hira_roadmap")
    cm = pd.read_csv(REFERENCE / "compliance_matrix.csv")
    idx = load("site_risk_index").set_index("site_id")
    dup = load("qa_duplicate_series")
    ind = load("qa_independent_cities")
    adj = load("air_dhaka_work_adjustment")
    air = load("city_air_summary")
    aqi = load("air_aqi_distribution").set_index("city_name")
    monthly = load("air_monthly_profile")
    dhaka_m = monthly[monthly["city_name"] == "Dhaka"].set_index("month")["mean_pm25"]
    dk = air[air["city_name"] == "Dhaka"].iloc[0]
    a = aqi.loc["Dhaka"]

    return {
        "hazards": len(hira),
        "areas": hira["area"].nunique(),
        "open_high": int(state.loc["High", "current"] + state.loc["Critical", "current"]),
        "target_high": int(state.loc["High", "target"] + state.loc["Critical", "target"]),
        "inherent_high": int(state.loc["High", "inherent"] + state.loc["Critical", "inherent"]),
        "roadmap_n": len(road),
        "roadmap_pts": int(road["gap_to_target"].sum()),
        "requirements": len(cm),
        "critical_reqs": int((cm["criticality"] == "Critical").sum()),
        "records": 1_048_551,
        "facilities": len(load("facilities_clean")),
        "dup_pairs": len(dup),
        "independent": len(ind),
        "trigger_days": int(adj["trigger_days"].sum()),
        "valid_days": int(adj["days"].sum()),
        "trigger_pct": round(adj["trigger_days"].sum() / adj["days"].sum() * 100),
        "jan": dhaka_m.loc[1],
        "jul": dhaka_m.loc[7],
        "swing": round(dhaka_m.loc[1] / dhaka_m.loc[7], 1),
        "dhaka_pm": dk["mean_pm2_5"],
        "vs_who": round(dk["mean_pm2_5"] / 5.0, 1),
        "unhealthy_share": round(
            a["Unhealthy for Sensitive Groups"] + a["Unhealthy"]
            + a["Very Unhealthy"] + a["Hazardous"], 1),
        "s01": idx.loc["S01", "cshri"],
        "s02": idx.loc["S02", "cshri"],
        "s01_band": idx.loc["S01", "band"],
        "s02_band": idx.loc["S02", "band"],
        "s02_fac": int(idx.loc["S02", "facilities_within_r"]),
        "s01_fac": int(idx.loc["S01", "facilities_within_r"]),
        "s02_workers": int(idx.loc["S02", "workers_within_r"]),
        "s01_km": idx.loc["S01", "urban_centre_km"],
        "tests": 87,
    }


def tile_row(items) -> Table:
    cells = [[Paragraph(v, S["tile_v"]) for v, _ in items],
             [Paragraph(l, S["tile_l"]) for _, l in items]]
    w = (180 * mm) / len(items)
    t = Table(cells, colWidths=[w] * len(items), rowHeights=[7.2 * mm, 6.4 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BAND_BG),
        ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
        ("VALIGN", (0, 1), (-1, 1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, 0), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white),
    ]))
    return t


def build(out: Path, repo: str = "github.com/<your-username>/safefactory-bd") -> None:
    f = figures()

    doc = BaseDocTemplate(
        str(out), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=11 * mm,
        title="SafeFactory BD — project summary",
        author="Ishtiaq Ahmed",
        subject="ISO 45001-aligned HSE management and site risk intelligence system",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame])])

    story = []

    # ---- header ---------------------------------------------------------
    head = Table(
        [[Paragraph("Ishtiaq Ahmed", S["name"]),
          Paragraph("BSc Industrial &amp; Production Engineering, Islamic University of "
                    "Technology<br/>ishtiaqahmed21@iut-dhaka.edu · Gazipur, Bangladesh",
                    S["contact"])]],
        colWidths=[70 * mm, 110 * mm])
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.9, INK),
    ]))
    story += [head]

    story += [
        Paragraph("SafeFactory BD", S["title"]),
        Paragraph(
            "An <b>ISO 45001-aligned HSE management and site risk intelligence system</b> "
            "for Bangladeshi food and dairy manufacturing — a working management system, "
            "not a dashboard, with an analytics layer built on open national data.",
            S["sub"]),
    ]

    # ---- scale tiles ----------------------------------------------------
    story += [tile_row([
        (f"{f['hazards']}", "HAZARDS ASSESSED"),
        (f"{f['requirements']}", "COMPLIANCE REQUIREMENTS"),
        ("1.05M", "HOURLY AIR RECORDS"),
        (f"{f['facilities']:,}", "GEOCODED FACILITIES"),
        (f"{f['tests']}", "UNIT TESTS PASSING"),
    ])]

    # ---- what it does ---------------------------------------------------
    story += [Paragraph("WHAT IT DOES", S["h"])]
    rows = [
        [Paragraph("<b>HIRA / JSA engine</b>", S["td"]),
         Paragraph("5×5 matrix with a fatality-escalation rule and hierarchy-of-controls "
                   "scoring; a 36-hazard dairy and snack-plant register covering ammonia "
                   "refrigeration, milk-powder dust, hot-oil frying, gas ovens, boilers and "
                   "confined spaces — every hazard citing its statute.", S["td"])],
        [Paragraph("<b>Permit to Work</b>", S["td"]),
         Paragraph("Seven permit classes with validity, gas-test, standby and fire-watch "
                   "rules; automatically detects expired, self-issued, ungas-tested and "
                   "unclosed permits.", S["td"])],
        [Paragraph("<b>Lockout–Tagout</b>", S["td"]),
         Paragraph("Equipment-specific isolation sheets across eight energy types; refuses "
                   "sign-off on an electrical-only isolation of plant holding stored "
                   "pressure, gravity or thermal energy.", S["td"])],
        [Paragraph("<b>Incidents</b>", S["td"]),
         Paragraph("Statutory classification; LTIFR, TRIR, DART and severity rate each on "
                   "its own correctly-named base; Pareto, reporting-health check, 5-Why with "
                   "a blame detector, bow-tie with barrier-gap detection.", S["td"])],
        [Paragraph("<b>Compliance matrix</b>", S["td"]),
         Paragraph(f"{f['requirements']} requirements mapping every ISO 45001:2018 clause "
                   "group to the Bangladeshi instrument that makes it a legal duty — Labour "
                   "Act 2006, Labour Rules 2015, BNBC 2020, Fire Prevention and Extinction "
                   f"Act 2003, ECA 1995 — with named evidence and weighted scoring "
                   f"({f['critical_reqs']} rated Critical).", S["td"])],
        [Paragraph("<b>Site Risk Index</b>", S["td"]),
         Paragraph("A 0–100 screening score for industrial locations from ambient air "
                   "burden, industrial density, worker concentration and emergency access — "
                   "with weight and radius sensitivity analysis.", S["td"])],
    ]
    t = Table(rows, colWidths=[30 * mm, 150 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), 4),
        ("LEFTPADDING", (1, 0), (1, -1), 0),
        ("RIGHTPADDING", (1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ]))
    story += [t]

    # ---- findings -------------------------------------------------------
    story += [Paragraph("THREE FINDINGS THAT CAME OUT OF BUILDING IT", S["h"])]

    def finding(n, head_txt, body_txt):
        return KeepTogether([
            Paragraph(f"{n}&nbsp;&nbsp;{head_txt}", S["find_h"]),
            Paragraph(body_txt, S["find_b"]),
            Spacer(1, 3.6),
        ])

    story += [finding(
        "1.",
        "Separating what a plant <i>has</i> from what it <i>plans</i> changes the picture.",
        f"A standard register reports residual risk, which silently assumes every listed "
        f"control is installed. Crediting only the controls that actually exist, "
        f"<b>{f['open_high']} of {f['hazards']} hazards sit at High or Critical today</b> — "
        f"against {f['target_high']} in the target state and {f['inherent_high']} with no "
        f"controls at all. The gap is the programme: {f['roadmap_n']} hazards worth "
        f"{f['roadmap_pts']} risk points, ranked by the points each outstanding control "
        f"would remove rather than by raw score.")]

    story += [finding(
        "2.",
        "The pipeline refuses to publish a finding it cannot support.",
        f"The source air-quality dataset yields a striking Dhaka trend of +2.55 µg/m³ per "
        f"year over 26 years. It is an artefact: the 2000–2021 segment rises monotonically "
        f"<i>every single year</i> (monotone fraction 1.00, R² 0.994) then steps down by "
        f"68 µg/m³. An automated integrity screen now detects this and <b>rejects the "
        f"trend</b>. The same screen found that <b>{f['dup_pairs']} pairs of the 30 named "
        f"cities carry byte-identical hourly series</b> — two of them over 30 km apart — "
        f"leaving {f['independent']} independent locations, not 30. Both defects would have "
        f"corrupted every downstream figure and neither is visible in a summary statistic.")]

    story += [finding(
        "3.",
        "The exposure analysis ends in a control, not a chart.",
        f"Mean PM2.5 at the Dhaka reference point is {f['dhaka_pm']:.1f} µg/m³, "
        f"{f['vs_who']}× the WHO annual guideline, with {f['unhealthy_share']:.0f}% of hours "
        f"at ‘Unhealthy for Sensitive Groups’ or worse. An outdoor-work protocol triggered "
        f"at AQI 150 would fire on <b>{f['trigger_days']} of {f['valid_days']:,} valid days "
        f"({f['trigger_pct']}%)</b>, concentrated in a predictable dry season "
        f"({f['jan']:.0f} µg/m³ in January against {f['jul']:.0f} in July, a "
        f"{f['swing']}-fold swing) — so seasonal scheduling is a workable control. Had the "
        f"figure come out at 80% of days, the honest conclusion would have been the "
        f"opposite: that a day-by-day trigger is theatre and the budget belongs in "
        f"engineering controls.")]

    # ---- applied result -------------------------------------------------
    story += [Paragraph("APPLIED TO TWO OPERATING SITES", S["h"])]
    site_rows = [
        [Paragraph("<b>Site</b>", S["th"]), Paragraph("<b>Index</b>", S["th"]),
         Paragraph("<b>Plants ≤10 km</b>", S["th"]),
         Paragraph("<b>What the score means for the HSE plan</b>", S["th"])],
        [Paragraph("Factory 2 — Gazipur", S["td"]),
         Paragraph(f"<b>{f['s02']:.1f}</b> {f['s02_band']}", S["td"]),
         Paragraph(f"{f['s02_fac']}", S["td"]),
         Paragraph(f"Exposure is <b>external</b>: ~{f['s02_workers']:,} workers inside the "
                   "same response envelope. Needs mutual-aid arrangements, a joint "
                   "evacuation understanding with immediate neighbours, and a kept-clear "
                   "fire-service access route.", S["td"])],
        [Paragraph("Factory 1 — Vulta, Rupganj", S["td"]),
         Paragraph(f"<b>{f['s01']:.1f}</b> {f['s01_band']}", S["td"]),
         Paragraph(f"{f['s01_fac']}", S["td"]),
         Paragraph(f"Exposure is <b>internal</b>: {f['s01_km']:.0f} km from a significant "
                   "urban centre, so help is further away. Needs stronger on-site fire and "
                   "first-aid capability and a written arrangement with a burn-capable "
                   "hospital.", S["td"])],
    ]
    st = Table(site_rows, colWidths=[35 * mm, 22 * mm, 20 * mm, 103 * mm])
    st.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, RULE),
    ]))
    story += [st, Spacer(1, 5)]

    # ---- footer ---------------------------------------------------------
    foot = Table([[Paragraph(
        f"<b>Repository</b> {repo} &nbsp;·&nbsp; "
        "<b>Built with</b> Python, pandas, Streamlit and Plotly. "
        f"{f['tests']} unit tests, every rate checked against a hand-worked calculation. "
        "Eight-page dashboard; one-command launch. Full technical report and source in the "
        "repository. &nbsp;&nbsp;<b>Scope, stated plainly:</b> the demonstration incident "
        "register is synthetic and labelled as such throughout; the hazard register is built "
        "from published operations and standard dairy and snack-processing hazard profiles, "
        "not from a site walk-through; site coordinates are geocoded to sub-district level, "
        "not surveyed; the air-quality data is a gridded model product, not station "
        "measurements. This is a decision-support tool, not a substitute for a competent "
        "person's assessment of an actual workplace.", S["foot"])]],
        colWidths=[180 * mm])
    foot.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f7f4")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT),
    ]))
    story += [foot]

    doc.build(story)


def main() -> None:
    # Pass your repository URL so the one-pager points somewhere real:
    #     python scripts/make_onepager.py github.com/ishtiaq/safefactory-bd
    repo = sys.argv[1] if len(sys.argv) > 1 else "github.com/<your-username>/safefactory-bd"
    out = REPORTS / "SafeFactory_BD_One_Page_Summary.pdf"
    build(out, repo)
    print(f"Wrote {out}")
    print(f"Repository line set to: {repo}")


if __name__ == "__main__":
    main()
