"""ISO 45001 x Bangladesh statutory compliance matrix, scoring and audit plan."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import theme as T
from safefactory.compliance import CONFORMITY_SCORES, ComplianceMatrix

T.setup("Compliance")
st.title("ISO 45001:2018 × Bangladesh Statutory Compliance")
st.caption("Every clause mapped to the instrument that makes it a legal duty in "
           "Bangladesh, with the evidence named")

if not T.guard():
    st.stop()

cm = ComplianceMatrix.from_csv()

T.note(
    "An ISO gap analysis that does not name the Bangladeshi legal instrument behind "
    "each clause is an academic exercise. A legal register that does not map to a "
    "management-system clause cannot be audited. This matrix is both, in one table: "
    "<b>clause → statute → evidence → verification method → frequency</b>."
)

tab_assess, tab_gaps, tab_legal, tab_plan = st.tabs(
    ["Self-assessment", "Gap report", "Legal register", "Audit programme"]
)

# --------------------------------------------------------------------------
with tab_assess:
    st.subheader("Score the site against each requirement")
    st.caption(
        "Weighting is deliberately steep: a Critical non-conformance cannot be "
        "averaged away by a long list of conformities. Critical items carry three "
        "times the weight of Medium ones."
    )

    preset = st.selectbox(
        "Start from",
        ["A typical mid-maturity Bangladeshi food plant", "Everything conforms",
         "Nothing assessed yet"],
    )

    if preset == "Everything conforms":
        cm.apply_statuses({r: "Conforms" for r in cm.df["req_id"]})
    elif preset == "A typical mid-maturity Bangladeshi food plant":
        # A plausible starting profile: statutory certificates and documented
        # policy are usually in place; the behavioural and verification-side
        # requirements are usually where the gaps sit.
        profile = {
            "CM-01": "Conforms", "CM-02": "Conforms", "CM-03": "Minor NC",
            "CM-04": "Minor NC", "CM-05": "Major NC", "CM-06": "Major NC",
            "CM-07": "Not Started", "CM-08": "Minor NC", "CM-09": "Minor NC",
            "CM-10": "Minor NC", "CM-11": "Minor NC", "CM-12": "Minor NC",
            "CM-13": "Minor NC", "CM-14": "Conforms", "CM-15": "Conforms",
            "CM-16": "Major NC", "CM-17": "Not Conform", "CM-18": "Minor NC",
            "CM-19": "Not Started", "CM-20": "Major NC", "CM-21": "Conforms",
            "CM-22": "Minor NC", "CM-23": "Conforms", "CM-24": "Major NC",
            "CM-25": "Minor NC", "CM-26": "Not Started", "CM-27": "Not Started",
            "CM-28": "Minor NC", "CM-29": "Minor NC", "CM-30": "Not Started",
            "CM-31": "Conforms", "CM-32": "Conforms", "CM-33": "Minor NC",
            "CM-34": "Minor NC", "CM-35": "Minor NC",
        }
        cm.apply_statuses({k: v for k, v in profile.items()
                           if k in set(cm.df["req_id"])})

    ci = cm.conformity_index()
    T.tiles([
        ("Conformity index", f"{ci['conformity_index']:.0f}",
         "weighted, 0–100, Not Applicable excluded"),
        ("Conforms", f"{ci['conforms']}", f"of {ci['assessed']} requirements"),
        ("Minor NC", f"{ci['minor_nc']}", "documented but incomplete"),
        ("Major NC", f"{ci['major_nc']}", "a system element is missing"),
        ("Critical gaps", f"{ci['critical_gaps']}", "critical items not conforming"),
    ])

    if ci["critical_gaps"]:
        T.note(
            f"<b>{ci['critical_gaps']} requirement(s) rated Critical are not "
            "conforming.</b> Each carries a statutory duty as well as a clause "
            "obligation, so each is an enforcement exposure and not only a "
            "certification one. They are listed on the Gap report tab.", kind="crit")

    st.subheader("Conformity by ISO 45001 clause")
    bc = cm.by_clause()
    fig = go.Figure(
        go.Bar(
            x=bc["conformity_pct"],
            y=[f"{g} · {t}" for g, t in zip(bc["iso_clause_group"], bc["iso_clause_title"])],
            orientation="h",
            marker_color=[
                T.STATUS["good"] if v >= 80 else
                T.STATUS["warning"] if v >= 60 else
                T.STATUS["serious"] if v >= 40 else T.STATUS["critical"]
                for v in bc["conformity_pct"]
            ],
            marker_line=dict(color=T.SURFACE, width=2),
            text=[f"{v:.0f}%  ({int(g)} critical gap{'s' if g != 1 else ''})"
                  for v, g in zip(bc["conformity_pct"], bc["critical_gaps"])],
            textposition="outside", textfont=dict(color=T.INK_SECONDARY, size=11),
            hovertemplate=("%{y}<br>Conformity %{x:.0f}%"
                           "<br>%{customdata} requirements<extra></extra>"),
            customdata=bc["requirements"], showlegend=False,
        )
    )
    fig.update_layout(**T.layout("Weighted conformity by clause group", height=360))
    fig.update_xaxes(title="Weighted conformity (%)", range=[0, 118])
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "The percentage and the critical-gap count are printed on every bar, so the "
        "colour is a reinforcement of the reading rather than the reading itself."
    )

    st.subheader("Adjust individual requirements")
    req = st.selectbox(
        "Requirement", cm.df["req_id"] + " — " + cm.df["requirement"].str.slice(0, 80)
    )
    rid = req.split(" — ")[0]
    new = st.selectbox("Status", list(CONFORMITY_SCORES))
    if st.button("Apply"):
        cm.set_status(rid, new)
        st.success(f"{rid} set to {new}. New index: "
                   f"{cm.conformity_index()['conformity_index']:.0f}")

    st.dataframe(
        cm.df[["req_id", "domain", "iso45001_clause", "iso45001_title",
               "bd_legal_reference", "requirement", "evidence_required",
               "criticality", "status"]],
        width="stretch", hide_index=True, height=400,
    )

# --------------------------------------------------------------------------
with tab_gaps:
    st.subheader("Open non-conformances, worst first")
    level = st.selectbox("Minimum criticality", ["Critical", "High", "Medium", "Low"],
                         index=1)
    if preset != "Nothing assessed yet":
        gaps = cm.gaps(level)
        st.caption(f"{len(gaps)} open item(s) at {level} criticality or above.")
        st.dataframe(gaps, width="stretch", hide_index=True, height=460)
        st.download_button("Download the gap report as CSV",
                           gaps.to_csv(index=False).encode(),
                           "compliance_gaps.csv", "text/csv")
    else:
        st.info("Choose a starting profile on the Self-assessment tab.")

# --------------------------------------------------------------------------
with tab_legal:
    st.subheader("Statutory register (ISO 45001 clause 6.1.3)")
    st.caption(
        "The instruments this management system is built against, and how many "
        "requirements rest on each. Maintaining this register is itself a clause "
        "requirement."
    )
    lr = cm.legal_register().reset_index()
    fig = go.Figure(
        go.Bar(
            x=lr["requirements"], y=lr["legal_reference"], orientation="h",
            marker_color=T.SERIES[0], marker_line=dict(color=T.SURFACE, width=2),
            hovertemplate=("%{y}<br>%{x} requirement(s)"
                           "<br>%{customdata} rated Critical<extra></extra>"),
            customdata=lr["critical"], showlegend=False,
        )
    )
    fig.update_layout(**T.layout("Requirements resting on each instrument", height=560))
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(title="Requirements", dtick=1)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(lr, width="stretch", hide_index=True)

    st.markdown("""
**The instruments in play**

- **Bangladesh Labour Act 2006 (BLA)** — the primary statute. Chapter V covers health
  and hygiene (ss. 51–59); Chapter VI covers safety, including fencing of machinery
  (s. 61), precautions against fire and dangerous fumes (s. 62), self-acting machines
  (s. 63), excessive weights (s. 74), training and PPE (s. 78A), health checks for
  dangerous operations (s. 79c), notice of accident (s. 80), first aid (s. 89) and the
  Safety Committee (s. 90A).
- **Bangladesh Labour Rules 2015 (BLR)** — the operative detail. Rule 58 covers
  electrical certification; rules 60 and 62 cover lifting machinery and pressure
  plant; rule 68 covers dangerous operations; rule 73 and Schedule IV(2) cover accident
  recording; rule 81 and Schedule IV(3) govern Safety Committee composition and its
  quarterly meeting.
- **Fire Prevention and Extinction Act 2003** — sections 4 and 8 govern fire licensing
  and means of escape.
- **Bangladesh National Building Code 2020 (BNBC)** — Part 3 on occupancy, Part 4 on
  fire protection, Part 6 on structure, Part 8 on building services.
- **Environment Conservation Act 1995 and Rules 1997** — Environmental Clearance
  Certificate, effluent discharge standards and stack emission standards.
""")

# --------------------------------------------------------------------------
with tab_plan:
    st.subheader("Audit programme (ISO 45001 clause 9.2)")
    st.caption(
        "Frequency is driven by criticality, not by convenience. Critical items are "
        "verified in the field or against a certificate, not by reading a policy."
    )
    st.dataframe(cm.audit_plan(), width="stretch", hide_index=True, height=560)
    st.download_button("Download the audit programme as CSV",
                       cm.audit_plan().to_csv(index=False).encode(),
                       "audit_programme.csv", "text/csv")
