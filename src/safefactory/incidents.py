"""Incident register, statutory classification and injury performance metrics.

Every rate function states its own base and returns a value that can be checked
by hand. The formulas follow the ILO convention for LTIFR and severity rate
(per 1,000,000 hours) and the OSHA convention for TRIR and DART (per 200,000
hours, i.e. 100 full-time equivalent workers). Mixing the two bases is the most
common error in factory HSE reporting, so the base is named in every result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import (
    DART_BASE,
    DART_CLASSES,
    FATALITY_DAY_CHARGE,
    INCIDENT_CLASSES,
    LTIFR_BASE,
    RECORDABLE_CLASSES,
    SEVERITY_RATE_BASE,
    TRIR_BASE,
)

# --------------------------------------------------------------------------
# Rate calculations
# --------------------------------------------------------------------------
def _guard_hours(hours_worked: float) -> float:
    if hours_worked is None or hours_worked <= 0:
        raise ValueError("hours_worked must be a positive number")
    return float(hours_worked)


def ltifr(lost_time_injuries: int, hours_worked: float) -> float:
    """Lost Time Injury Frequency Rate per 1,000,000 hours worked (ILO base)."""
    return round(lost_time_injuries * LTIFR_BASE / _guard_hours(hours_worked), 2)


def trir(recordable_cases: int, hours_worked: float) -> float:
    """Total Recordable Incident Rate per 200,000 hours worked (OSHA base)."""
    return round(recordable_cases * TRIR_BASE / _guard_hours(hours_worked), 2)


def dart_rate(dart_cases: int, hours_worked: float) -> float:
    """Days Away, Restricted or Transferred rate per 200,000 hours (OSHA base)."""
    return round(dart_cases * DART_BASE / _guard_hours(hours_worked), 2)


def severity_rate(days_lost: float, hours_worked: float) -> float:
    """Severity rate: days lost per 1,000,000 hours worked (ILO base)."""
    return round(days_lost * SEVERITY_RATE_BASE / _guard_hours(hours_worked), 1)


def incidence_rate(cases: int, average_workers: int) -> float:
    """Incidence rate per 1,000 workers employed (ILO base)."""
    if average_workers is None or average_workers <= 0:
        raise ValueError("average_workers must be a positive number")
    return round(cases * 1000 / average_workers, 2)


def average_days_lost(days_lost: float, lost_time_injuries: int) -> float:
    """Mean days lost per lost-time injury — the severity of the typical case."""
    if lost_time_injuries == 0:
        return 0.0
    return round(days_lost / lost_time_injuries, 1)


def exposure_hours(
    headcount: int, hours_per_shift: float = 8.0, working_days: int = 300
) -> float:
    """Estimate exposure hours from headcount, shift length and working days.

    Returns ``headcount x hours_per_shift x working_days``. Use a timesheet
    total whenever one exists: a frequency rate computed on an assumed
    denominator is not an audit-grade number, and the dashboard labels any
    figure derived this way as an estimate.
    """
    if headcount <= 0 or hours_per_shift <= 0 or working_days <= 0:
        raise ValueError("headcount, hours_per_shift and working_days must be positive")
    return float(headcount) * float(hours_per_shift) * float(working_days)


def safe_days(last_lti_date, as_of=None) -> int:
    """Days since the last lost-time injury."""
    last = pd.Timestamp(last_lti_date)
    now = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()
    return int((now - last).days)


def heinrich_ratio(df: pd.DataFrame) -> pd.Series:
    """Observed ratio of near misses to first aid to recordable to lost time.

    Not a prediction — a reporting-health check. A plant recording few near
    misses per lost-time injury is almost certainly under-reporting rather than
    unusually safe.
    """
    counts = df["classification"].value_counts()
    nm = counts.get("Near Miss", 0)
    fa = counts.get("First Aid Case", 0)
    rec = sum(counts.get(c, 0) for c in RECORDABLE_CLASSES)
    lti = counts.get("Lost Time Injury", 0) + counts.get("Permanent Disability", 0) + counts.get("Fatality", 0)
    return pd.Series(
        {
            "near_miss": nm,
            "first_aid": fa,
            "recordable": rec,
            "lost_time_or_worse": lti,
            "near_miss_per_recordable": round(nm / rec, 1) if rec else np.nan,
            "near_miss_per_lti": round(nm / lti, 1) if lti else np.nan,
        }
    )


# --------------------------------------------------------------------------
# Register
# --------------------------------------------------------------------------
@dataclass
class IncidentRegister:
    """An incident register with statutory classification and KPI roll-up."""

    df: pd.DataFrame = field(repr=False)
    REQUIRED = ["incident_id", "date", "area", "classification", "days_lost"]

    def __post_init__(self) -> None:
        missing = [c for c in self.REQUIRED if c not in self.df.columns]
        if missing:
            raise ValueError(f"incident register is missing required columns: {missing}")
        bad = set(self.df["classification"]) - set(INCIDENT_CLASSES)
        if bad:
            raise ValueError(
                f"unknown incident classification(s): {sorted(bad)}. "
                f"Allowed: {INCIDENT_CLASSES}"
            )
        self.df = self.df.copy()
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df["days_lost"] = self.df["days_lost"].fillna(0).astype(float)
        # Apply the standard fatality day charge so severity rate is comparable
        # across sites and years.
        fatal = self.df["classification"] == "Fatality"
        self.df.loc[fatal & (self.df["days_lost"] < FATALITY_DAY_CHARGE), "days_lost"] = (
            FATALITY_DAY_CHARGE
        )
        self.df["is_recordable"] = self.df["classification"].isin(RECORDABLE_CLASSES)
        self.df["is_dart"] = self.df["classification"].isin(DART_CLASSES)
        self.df["is_lti"] = self.df["classification"].isin(
            {"Lost Time Injury", "Permanent Disability", "Fatality"}
        )
        self.df["month"] = self.df["date"].dt.to_period("M").astype(str)

    @classmethod
    def from_csv(cls, path) -> "IncidentRegister":
        return cls(pd.read_csv(path))

    # -- KPIs --------------------------------------------------------------
    def kpis(self, hours_worked: float, average_workers: int | None = None) -> dict:
        d = self.df
        n_lti = int(d["is_lti"].sum())
        n_rec = int(d["is_recordable"].sum())
        n_dart = int(d["is_dart"].sum())
        days = float(d["days_lost"].sum())
        out = {
            "period_start": str(d["date"].min().date()),
            "period_end": str(d["date"].max().date()),
            "hours_worked": hours_worked,
            "total_events": int(len(d)),
            "near_misses": int((d["classification"] == "Near Miss").sum()),
            "first_aid_cases": int((d["classification"] == "First Aid Case").sum()),
            "recordable_cases": n_rec,
            "dart_cases": n_dart,
            "lost_time_injuries": n_lti,
            "fatalities": int((d["classification"] == "Fatality").sum()),
            "days_lost": days,
            "LTIFR_per_1M_hours": ltifr(n_lti, hours_worked),
            "TRIR_per_200k_hours": trir(n_rec, hours_worked),
            "DART_per_200k_hours": dart_rate(n_dart, hours_worked),
            "severity_rate_per_1M_hours": severity_rate(days, hours_worked),
            "average_days_lost_per_LTI": average_days_lost(days, n_lti),
        }
        if average_workers:
            out["incidence_rate_per_1000_workers"] = incidence_rate(n_rec, average_workers)
        return out

    def monthly_trend(self, monthly_hours: float) -> pd.DataFrame:
        """Rolling monthly KPI trend — the chart a management review runs on."""
        g = self.df.groupby("month").agg(
            events=("incident_id", "count"),
            near_misses=("classification", lambda s: (s == "Near Miss").sum()),
            recordables=("is_recordable", "sum"),
            ltis=("is_lti", "sum"),
            days_lost=("days_lost", "sum"),
        )
        g["LTIFR"] = (g["ltis"] * LTIFR_BASE / monthly_hours).round(2)
        g["TRIR"] = (g["recordables"] * TRIR_BASE / monthly_hours).round(2)
        g["severity_rate"] = (g["days_lost"] * SEVERITY_RATE_BASE / monthly_hours).round(1)
        g["rolling_12m_LTIFR"] = (
            g["ltis"].rolling(12, min_periods=1).sum()
            * LTIFR_BASE
            / (monthly_hours * g["ltis"].rolling(12, min_periods=1).count())
        ).round(2)
        return g.reset_index()

    def pareto(self, by: str = "immediate_cause", top: int = 10) -> pd.DataFrame:
        """Pareto of incident drivers — where the next control pound should go."""
        if by not in self.df.columns:
            raise ValueError(f"column {by!r} not in register")
        g = self.df[by].value_counts().head(top).rename("events").to_frame()
        g["pct"] = (g["events"] / len(self.df) * 100).round(1)
        g["cumulative_pct"] = g["pct"].cumsum().round(1)
        return g

    def by_area(self) -> pd.DataFrame:
        g = self.df.groupby("area").agg(
            events=("incident_id", "count"),
            recordables=("is_recordable", "sum"),
            ltis=("is_lti", "sum"),
            days_lost=("days_lost", "sum"),
        )
        return g.sort_values(["ltis", "recordables", "events"], ascending=False)

    def open_actions(self) -> pd.DataFrame:
        """Corrective actions not yet verified as effective (ISO 45001 cl. 10.2)."""
        if "action_status" not in self.df.columns:
            raise ValueError("register has no action_status column")
        d = self.df[self.df["action_status"].str.lower() != "verified effective"]
        cols = [
            c
            for c in [
                "incident_id",
                "date",
                "area",
                "classification",
                "corrective_action",
                "action_owner",
                "action_due",
                "action_status",
            ]
            if c in d.columns
        ]
        d = d[cols].copy()
        if "action_due" in d.columns:
            d["action_due"] = pd.to_datetime(d["action_due"])
            d["days_overdue"] = (pd.Timestamp.today().normalize() - d["action_due"]).dt.days
            d["days_overdue"] = d["days_overdue"].clip(lower=0)
        return d.sort_values("date")


# --------------------------------------------------------------------------
# Investigation helpers
# --------------------------------------------------------------------------
def five_why(problem: str, whys: list[str]) -> pd.DataFrame:
    """Structure a 5-Why analysis and flag the common failure mode.

    An analysis that terminates in an individual ('operator was careless') has
    stopped at the immediate cause. The check below names that explicitly so an
    investigator cannot close out on blame.
    """
    rows = [{"level": 0, "statement": problem, "type": "Problem"}]
    for i, w in enumerate(whys, start=1):
        rows.append({"level": i, "statement": w, "type": f"Why {i}"})
    d = pd.DataFrame(rows)
    blame_terms = (
        "careless",
        "negligent",
        "did not follow",
        "failed to follow",
        "human error",
        "complacent",
        "forgot",
    )
    last = str(rows[-1]["statement"]).lower()
    d.attrs["terminates_in_blame"] = any(t in last for t in blame_terms)
    d.attrs["depth"] = len(whys)
    d.attrs["adequate_depth"] = len(whys) >= 5
    return d


def bowtie(hazard: str, top_event: str, threats: list[str], consequences: list[str],
           preventive: dict[str, list[str]], mitigative: dict[str, list[str]]) -> dict:
    """Assemble a bow-tie model and count barriers on each side.

    A bow-tie with threats but no preventive barrier on a threat line, or
    consequences with no mitigative barrier, is where the next serious incident
    comes from. The returned ``gaps`` list names exactly those lines.
    """
    gaps = []
    for t in threats:
        if not preventive.get(t):
            gaps.append({"side": "preventive", "line": t, "issue": "no barrier identified"})
    for c in consequences:
        if not mitigative.get(c):
            gaps.append({"side": "mitigative", "line": c, "issue": "no barrier identified"})
    return {
        "hazard": hazard,
        "top_event": top_event,
        "threats": threats,
        "consequences": consequences,
        "preventive_barriers": preventive,
        "mitigative_barriers": mitigative,
        "n_preventive": sum(len(v) for v in preventive.values()),
        "n_mitigative": sum(len(v) for v in mitigative.values()),
        "gaps": gaps,
    }
