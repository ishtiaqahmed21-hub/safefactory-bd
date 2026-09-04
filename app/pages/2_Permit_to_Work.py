"""Permit to Work and Lockout-Tagout: issue, validate, audit."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import theme as T
from safefactory.config import PERMIT_TYPES
from safefactory.ptw import (
    ENERGY_TYPES,
    LOTOPoint,
    LOTOProcedure,
    Permit,
    PermitRegister,
    evaluate_gas_test,
)

T.setup("Permit to Work")
st.title("Permit to Work & Lockout–Tagout")
st.caption("ISO 45001:2018 clauses 8.1.2 and 8.1.4 · Bangladesh Labour Act 2006 "
           "ss. 62 and 78A · Fire Prevention and Extinction Act 2003 ss. 4 & 8")

T.note(
    "The value of a permit system is not the form. It is that an expired permit, a "
    "missing gas test, an absent standby person or an unclosed fire watch can be "
    "found <i>without reading every sheet in the file</i>. That detection is what "
    "this page does."
)

tab_audit, tab_issue, tab_loto = st.tabs(
    ["Live permit audit", "Issue a permit", "LOTO isolation sheet"]
)

# --------------------------------------------------------------------------
# A worked register that demonstrates each failure mode
# --------------------------------------------------------------------------
NOW = datetime(2026, 9, 4, 11, 0)


def demo_register() -> PermitRegister:
    r = PermitRegister()
    r.add(Permit(
        "PTW-2026-041", "Hot Work", "Warehouse & Yard",
        "Weld a damaged racking upright in bay 12",
        "A. Rahman (Maintenance Manager)", "K. Islam (Welder)",
        NOW - timedelta(hours=2), NOW + timedelta(hours=4),
        isolations=["Local power isolated"],
        gas_test={"oxygen_pct": 20.9, "lel_pct": 0.0, "co_ppm": 2.0},
        standby_person="M. Hasan (fire watch)",
    ))
    r.add(Permit(
        "PTW-2026-042", "Confined Space Entry", "Process Tanks & Silos",
        "Internal inspection of milk silo 2",
        "S. Ahmed (HSE Executive)", "R. Karim (Fitter)",
        NOW - timedelta(hours=3), NOW + timedelta(hours=3),
        isolations=[],  # <- the fatal gap
        gas_test={"oxygen_pct": 20.6, "lel_pct": 0.0, "co_ppm": 3.0},
        standby_person="T. Ali (attendant)",
    ))
    r.add(Permit(
        "PTW-2026-043", "Work at Height", "Refrigeration Plant",
        "Replace lighting above the ammonia compressor deck",
        "A. Rahman (Maintenance Manager)", "A. Rahman (Maintenance Manager)",
        NOW - timedelta(hours=6), NOW - timedelta(hours=1),
        isolations=["Lighting circuit locked off"],
        standby_person=None,  # <- two gaps: self-issued and no standby
    ))
    r.add(Permit(
        "PTW-2026-044", "Line Breaking", "Refrigeration Plant",
        "Break the NH3 suction line at the compressor flange",
        "S. Ahmed (HSE Executive)", "R. Karim (Fitter)",
        NOW - timedelta(days=1, hours=2), NOW - timedelta(days=1),
        isolations=["Pump-down complete", "Double block and bleed", "N2 purge verified"],
        gas_test={"oxygen_pct": 20.8, "nh3_ppm": 8.0, "lel_pct": 0.0},
        standby_person="M. Hasan",
    ))  # <- expired, never closed out
    r.add(Permit(
        "PTW-2026-045", "Hot Work", "Maintenance Workshop",
        "Grind and dress a conveyor shaft",
        "A. Rahman (Maintenance Manager)", "F. Nahar (Fitter)",
        NOW - timedelta(hours=8), NOW - timedelta(hours=3),
        isolations=["Workshop bench isolated"],
        gas_test={"oxygen_pct": 20.9, "lel_pct": 0.0},
        standby_person="J. Uddin",
        closed_at=NOW - timedelta(hours=2, minutes=55),
        fire_watch_completed=False,  # <- closed without the 60-minute fire watch
    ))
    r.add(Permit(
        "PTW-2026-046", "Electrical Work", "Substation & MCC Rooms",
        "Thermographic survey and terminal tightening, MCC-3",
        "S. Ahmed (HSE Executive)", "B. Chowdhury (Electrician)",
        NOW - timedelta(hours=1), NOW + timedelta(hours=5),
        isolations=["MCC-3 incomer racked out and locked", "Proved dead at terminals"],
        standby_person="N. Sultana",
    ))
    return r


with tab_audit:
    reg = demo_register()
    df = reg.to_frame(now=NOW)
    audit = reg.audit(now=NOW)

    T.tiles([
        ("Permits in period", f"{audit['permits']}", "hot work, entry, height, electrical"),
        ("Compliant", f"{audit['compliant']}", f"{audit['compliance_rate_pct']:.0f}% of permits"),
        ("Expired, not closed", f"{audit['expired_not_closed']}", "still open past validity"),
        ("Total findings", f"{audit['total_findings']}", "rule breaches detected"),
    ])

    if audit["non_compliant"]:
        T.note(
            f"<b>{audit['non_compliant']} of {audit['permits']} permits breach at least "
            "one rule.</b> Each finding below names the rule broken, not merely that "
            "the permit 'failed' — so the issuer knows what to fix.", kind="crit")

    show = df[["permit_id", "permit_type", "area", "description", "status",
               "compliant", "n_issues", "issues"]].rename(columns={
        "permit_id": "Permit", "permit_type": "Type", "area": "Area",
        "description": "Work", "status": "Status", "compliant": "OK",
        "n_issues": "Findings", "issues": "What is wrong",
    })
    st.dataframe(show, width="stretch", hide_index=True, height=300)

    st.subheader("Findings by permit")
    fig = go.Figure(
        go.Bar(
            x=df["n_issues"], y=df["permit_id"], orientation="h",
            marker_color=[T.STATUS["good"] if c else T.STATUS["critical"]
                          for c in df["compliant"]],
            marker_line=dict(color=T.SURFACE, width=2),
            text=[("compliant" if c else f"{n} finding{'s' if n != 1 else ''}")
                  for c, n in zip(df["compliant"], df["n_issues"])],
            textposition="outside", textfont=dict(color=T.INK_SECONDARY, size=11),
            hovertemplate="%{y}<br>%{x} finding(s)<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(**T.layout("Rule breaches per permit", height=300))
    fig.update_xaxes(title="Findings", dtick=1)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Green bars are compliant permits and red bars are non-compliant; the text "
        "label on every bar states which, so the status never rests on colour alone."
    )

    with st.expander("The rules each permit type is checked against"):
        st.dataframe(
            pd.DataFrame(PERMIT_TYPES).T.reset_index().rename(columns={
                "index": "Permit type",
                "max_validity_hours": "Max validity (h)",
                "gas_test_required": "Gas test required",
                "fire_watch_minutes_after": "Fire watch after (min)",
                "standby_required": "Standby required",
            }),
            width="stretch", hide_index=True,
        )
        st.markdown(
            "Two further rules apply to every type: the issuer and the acceptor "
            "must be different people, and a permit for confined space entry, line "
            "breaking or electrical work must record at least one energy isolation."
        )

# --------------------------------------------------------------------------
with tab_issue:
    st.subheader("Issue and validate a permit")
    c1, c2 = st.columns(2)
    with c1:
        ptype = st.selectbox("Permit type", list(PERMIT_TYPES))
        area = st.text_input("Area", "Refrigeration Plant")
        desc = st.text_input("Description of work", "Replace compressor shaft seal")
        issuer = st.text_input("Issued by", "S. Ahmed (HSE Executive)")
        acceptor = st.text_input("Accepted by", "R. Karim (Fitter)")
        standby = st.text_input("Standby person", "M. Hasan")
    with c2:
        dur = st.slider("Duration (hours)", 1, 30, 6)
        isolations = st.text_area(
            "Energy isolations (one per line)",
            "Compressor breaker racked out and locked\nSuction and discharge valves closed and locked",
        )
        st.markdown("**Gas test**")
        o2 = st.number_input("Oxygen (%)", 0.0, 30.0, 20.9, 0.1)
        lel = st.number_input("LEL (%)", 0.0, 100.0, 0.0, 1.0)
        nh3 = st.number_input("Ammonia (ppm)", 0.0, 500.0, 0.0, 1.0)
        co = st.number_input("Carbon monoxide (ppm)", 0.0, 500.0, 0.0, 1.0)

    start = NOW
    permit = Permit(
        "PTW-DRAFT", ptype, area, desc, issuer, acceptor,
        start, start + timedelta(hours=dur),
        isolations=[i for i in isolations.splitlines() if i.strip()],
        gas_test={"oxygen_pct": o2, "lel_pct": lel, "nh3_ppm": nh3, "co_ppm": co},
        standby_person=standby or None,
    )
    v = permit.validate(now=start + timedelta(minutes=30))

    if v["valid"]:
        st.success("**Permit may be issued.** Every applicable rule is satisfied.")
    else:
        st.error("**Permit must not be issued.** Findings:")
        for i in v["issues"]:
            st.markdown(f"- {i}")

    gas = evaluate_gas_test(permit.gas_test)
    st.markdown("**Atmospheric test against the acceptance criteria**")
    rows = []
    for param, detail in gas["detail"].items():
        rows.append({
            "Parameter": param,
            "Reading": detail["value"],
            "Acceptable range": f"{detail['limit'][0]} – {detail['limit'][1]}",
            "Result": "Pass" if detail["pass"] else "FAIL",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(
        "Ammonia limits follow the NIOSH recommended exposure limit of 25 ppm as an "
        "8-hour average, against an IDLH of 300 ppm. Oxygen must sit between 19.5% "
        "and 23.5%: enrichment above 23.5% is a fire hazard, not a safe atmosphere."
    )

# --------------------------------------------------------------------------
with tab_loto:
    st.subheader("Equipment-specific isolation sheet")
    T.note(
        "A single-point electrical lockout on plant that also holds stored pressure, "
        "gravity or thermal energy is the classic fatal gap. The check below refuses "
        "to sign off an isolation that covers electrical energy alone."
    )

    equip = st.selectbox(
        "Equipment",
        ["Ammonia compressor 1", "Powder blender 1", "Continuous fryer line 2",
         "Milk silo 2 agitator"],
    )

    PRESETS = {
        "Ammonia compressor 1": [
            ("Electrical", "Compressor MCC breaker", "Rack out and lock", "Prove dead at terminals"),
            ("Chemical", "NH3 suction and discharge valves", "Close, chain and lock", "Pump down, gauge at 0 bar"),
            ("Stored (spring / capacitor / pressure)", "Oil separator", "Vent to safe location", "Gauge reads zero"),
            ("Mechanical", "Drive coupling", "Remove coupling guard pin", "Attempt to rotate by hand"),
        ],
        "Powder blender 1": [
            ("Electrical", "Blender drive breaker", "Lock off", "Prove dead, attempt start"),
            ("Gravity", "Feed hopper slide gate", "Pin and lock closed", "Visual check, no residual load"),
            ("Pneumatic", "Rotary valve air supply", "Isolate and bleed", "Gauge at zero"),
        ],
        "Continuous fryer line 2": [
            ("Electrical", "Fryer heater contactor", "Lock off", "Prove dead"),
            ("Thermal", "Oil bath", "Cool-down period", "Verified below 50 C by probe"),
            ("Chemical", "Gas supply to burner", "Close and lock manual valve", "Burner will not light"),
            ("Mechanical", "Conveyor drive", "Lock off", "Attempt start"),
        ],
        "Milk silo 2 agitator": [
            ("Electrical", "Agitator motor breaker", "Lock off", "Prove dead, attempt start"),
            ("Chemical", "CIP caustic supply line", "Close and lock, blank flange", "Line drained and flushed"),
            ("Gravity", "Product inlet valve", "Close and lock", "Visual check through hatch"),
        ],
    }

    st.markdown("**Isolation points** — tick each control only when it is physically done.")
    proc = LOTOProcedure(equipment=equip, prepared_by="Maintenance Engineering")
    for i, (energy, device, method, verify) in enumerate(PRESETS[equip], start=1):
        c = st.columns([2.1, 2.4, 2.4, 1, 1, 1.2])
        c[0].markdown(f"**{energy}**")
        c[1].caption(device)
        c[2].caption(f"{method} → {verify}")
        locked = c[3].checkbox("Lock", True, key=f"l{i}{equip}")
        tagged = c[4].checkbox("Tag", True, key=f"t{i}{equip}")
        verified = c[5].checkbox("Try-out", i != 2, key=f"v{i}{equip}")
        proc.add(LOTOPoint(f"LP-{i}", equip, energy, device, method, verify,
                           locked, tagged, verified, "R. Karim"))

    v = proc.validate()
    if v["safe_to_work"]:
        st.success(
            f"**Safe to work.** {v['points']} isolation points applied, locked, "
            f"tagged and proved dead across: {', '.join(v['energy_types'])}."
        )
    else:
        st.error("**Not safe to work.** The isolation is incomplete:")
        for i in v["issues"]:
            st.markdown(f"- {i}")

    st.dataframe(proc.to_frame(), width="stretch", hide_index=True)

    with st.expander("The energy types every isolation must be checked against"):
        st.markdown("\n".join(f"- {e}" for e in ENERGY_TYPES))
        st.markdown(
            "**Try-out** means attempting to start the equipment through its normal "
            "controls after isolation, then returning the control to off. A lock "
            "without a try-out is an assumption, not an isolation."
        )
