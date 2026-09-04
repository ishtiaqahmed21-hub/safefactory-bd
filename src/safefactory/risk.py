"""HIRA / JSA risk engine.

Implements a 5 x 5 likelihood-severity matrix with an explicit fatality
escalation rule, hierarchy-of-controls scoring, and portfolio analytics over a
whole risk register.

The scoring convention and every threshold are declared in ``config`` rather
than hard-coded here, so an auditor can check the rules without reading code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

from .config import (
    CONTROL_HIERARCHY,
    FATALITY_ESCALATION_MIN_LIKELIHOOD,
    FATALITY_ESCALATION_SEVERITY,
    LIKELIHOOD_SCALE,
    REFERENCE,
    RISK_BANDS,
    SEVERITY_SCALE,
)

BAND_ORDER = ["Low", "Medium", "High", "Critical"]


# --------------------------------------------------------------------------
# Core scoring
# --------------------------------------------------------------------------
def _validate(likelihood: int, severity: int) -> None:
    if likelihood not in LIKELIHOOD_SCALE:
        raise ValueError(f"likelihood must be 1-5, got {likelihood!r}")
    if severity not in SEVERITY_SCALE:
        raise ValueError(f"severity must be 1-5, got {severity!r}")


def risk_score(likelihood: int, severity: int) -> int:
    """Return the raw 5 x 5 matrix score (likelihood x severity, 1-25)."""
    _validate(int(likelihood), int(severity))
    return int(likelihood) * int(severity)


def risk_band(likelihood: int, severity: int) -> str:
    """Return the risk band, applying the fatality escalation rule.

    A credible fatality scenario (severity 5) at likelihood 3 or above is
    forced to at least ``High`` even when the arithmetic product would place it
    lower. This prevents the common HIRA failure of scoring a fatal hazard as
    tolerable purely because it is judged unlikely.
    """
    score = risk_score(likelihood, severity)
    band = next(
        name for lo, hi, name, _action, _months in RISK_BANDS if lo <= score <= hi
    )
    if (
        int(severity) >= FATALITY_ESCALATION_SEVERITY
        and int(likelihood) >= FATALITY_ESCALATION_MIN_LIKELIHOOD
        and BAND_ORDER.index(band) < BAND_ORDER.index("High")
    ):
        band = "High"
    return band


def band_action(band: str) -> str:
    """The required management response for a band."""
    return next(action for _lo, _hi, name, action, _m in RISK_BANDS if name == band)


def band_review_months(band: str) -> int:
    """Maximum review interval in months for a band."""
    return next(m for _lo, _hi, name, _a, m in RISK_BANDS if name == band)


def control_effectiveness(control_hierarchy: str) -> float:
    """Score a control plan on the hierarchy of controls (ISO 45001 cl. 8.1.2).

    Accepts a single level or a ``+``-separated combination such as
    ``"Engineering + Administrative"``. Returns the mean weight of the levels
    present, normalised to 0-1, so that a plan resting only on PPE scores 0.2
    while one built on elimination scores 1.0.
    """
    if not isinstance(control_hierarchy, str) or not control_hierarchy.strip():
        return 0.0
    # Case-insensitive lookup against the canonical keys. Title-casing the
    # input would silently turn "PPE" into "Ppe" and drop it from the plan.
    canonical = {k.casefold(): k for k in CONTROL_HIERARCHY}
    levels = [p.strip().casefold() for p in control_hierarchy.split("+")]
    weights = [CONTROL_HIERARCHY[canonical[l]] for l in levels if l in canonical]
    if not weights:
        return 0.0
    return round(sum(weights) / len(weights) / max(CONTROL_HIERARCHY.values()), 3)


# --------------------------------------------------------------------------
# Register-level operations
# --------------------------------------------------------------------------
@dataclass
class RiskRegister:
    """A HIRA register with initial and residual scoring."""

    df: pd.DataFrame = field(repr=False)

    REQUIRED = [
        "hazard_id",
        "area",
        "hazard_description",
        "likelihood_initial",
        "severity_initial",
        "likelihood_residual",
        "severity_residual",
    ]

    def __post_init__(self) -> None:
        missing = [c for c in self.REQUIRED if c not in self.df.columns]
        if missing:
            raise ValueError(f"risk register is missing required columns: {missing}")
        self.df = self._score(self.df.copy())

    # -- construction ------------------------------------------------------
    @classmethod
    def from_csv(cls, path=None) -> "RiskRegister":
        path = path or (REFERENCE / "hira_dairy_seed.csv")
        return cls(pd.read_csv(path))

    # -- scoring -----------------------------------------------------------
    @staticmethod
    def _score(df: pd.DataFrame) -> pd.DataFrame:
        df["risk_score_initial"] = [
            risk_score(l, s)
            for l, s in zip(df["likelihood_initial"], df["severity_initial"])
        ]
        df["risk_band_initial"] = [
            risk_band(l, s)
            for l, s in zip(df["likelihood_initial"], df["severity_initial"])
        ]
        df["risk_score_residual"] = [
            risk_score(l, s)
            for l, s in zip(df["likelihood_residual"], df["severity_residual"])
        ]
        df["risk_band_residual"] = [
            risk_band(l, s)
            for l, s in zip(df["likelihood_residual"], df["severity_residual"])
        ]
        df["risk_reduction"] = df["risk_score_initial"] - df["risk_score_residual"]
        df["risk_reduction_pct"] = (
            df["risk_reduction"] / df["risk_score_initial"] * 100
        ).round(1)
        if "control_hierarchy" in df.columns:
            df["control_effectiveness"] = df["control_hierarchy"].map(
                control_effectiveness
            )
        # ------------------------------------------------------------------
        # Current risk.
        #
        # The residual score assumes every additional control is fully in
        # place. That is the target state, not today's state. Crediting it
        # before the control exists is the single most common way a HIRA
        # becomes fiction. Where a ``control_status`` column is present, the
        # current risk credits the control plan only to the extent it has
        # actually been implemented: fully when Implemented, half the
        # reduction when In progress, not at all when Proposed.
        # ------------------------------------------------------------------
        if "control_status" in df.columns:
            credit = df["control_status"].map(
                {"Implemented": 1.0, "In progress": 0.5, "Proposed": 0.0}
            ).fillna(0.0)
            df["risk_score_current"] = (
                df["risk_score_initial"] - credit * df["risk_reduction"]
            ).round().astype(int)
            df["risk_band_current"] = [
                next(n for lo, hi, n, _a, _m in RISK_BANDS if lo <= s <= hi)
                for s in df["risk_score_current"]
            ]
            # Apply the same fatality escalation to the current-state band,
            # using the severity that actually applies today: the reduced
            # severity only where the control plan is already implemented.
            effective_severity = df["severity_initial"].where(
                df["control_status"] != "Implemented", df["severity_residual"]
            )
            df["risk_band_current"] = [
                "High"
                if (sev >= FATALITY_ESCALATION_SEVERITY
                    and BAND_ORDER.index(b) < BAND_ORDER.index("High"))
                else b
                for b, sev in zip(df["risk_band_current"], effective_severity)
            ]
            df["gap_to_target"] = df["risk_score_current"] - df["risk_score_residual"]

        df["required_action"] = df["risk_band_residual"].map(band_action)
        df["max_review_months"] = df["risk_band_residual"].map(band_review_months)
        return df

    # -- analytics ---------------------------------------------------------
    def summary(self) -> pd.DataFrame:
        """Count of hazards by band, before and after controls."""
        before = self.df["risk_band_initial"].value_counts()
        after = self.df["risk_band_residual"].value_counts()
        out = pd.DataFrame({"before_controls": before, "after_controls": after})
        out = out.reindex(BAND_ORDER).fillna(0).astype(int)
        out["change"] = out["after_controls"] - out["before_controls"]
        return out

    def state_comparison(self) -> pd.DataFrame:
        """Hazard counts by band in three states: inherent, today, target.

        This is the single most useful table in the register. It shows what the
        plant would face with no controls, what it faces today given what is
        actually installed, and what the programme is buying.
        """
        cols = {"risk_band_initial": "inherent"}
        if "risk_band_current" in self.df.columns:
            cols["risk_band_current"] = "current"
        cols["risk_band_residual"] = "target"
        out = pd.DataFrame(
            {label: self.df[col].value_counts() for col, label in cols.items()}
        )
        return out.reindex(BAND_ORDER).fillna(0).astype(int)

    def roadmap(self) -> pd.DataFrame:
        """Implementation priority: biggest risk reduction still unbought.

        Ranked by the risk points the outstanding control plan would remove.
        That ordering, not the raw risk score, is where the next taka of HSE
        budget does the most good.
        """
        if "gap_to_target" not in self.df.columns:
            raise ValueError("register has no control_status column")
        d = self.df[self.df["gap_to_target"] > 0].copy()
        cols = [
            c
            for c in [
                "hazard_id",
                "area",
                "hazard_description",
                "control_status",
                "additional_controls",
                "control_hierarchy",
                "risk_score_current",
                "risk_band_current",
                "risk_score_residual",
                "gap_to_target",
                "responsible",
            ]
            if c in d.columns
        ]
        return d.sort_values(
            ["gap_to_target", "risk_score_current"], ascending=False
        )[cols].reset_index(drop=True)

    def open_high_risks(self) -> pd.DataFrame:
        """Hazards sitting at High or Critical *today* — the live exposure."""
        if "risk_band_current" not in self.df.columns:
            return self.intolerable()
        return self.df[
            self.df["risk_band_current"].isin(["High", "Critical"])
        ].sort_values("risk_score_current", ascending=False)

    def by_area(self) -> pd.DataFrame:
        """Area-level risk profile, ranked by residual exposure."""
        g = self.df.groupby("area").agg(
            hazards=("hazard_id", "count"),
            mean_initial=("risk_score_initial", "mean"),
            mean_residual=("risk_score_residual", "mean"),
            max_residual=("risk_score_residual", "max"),
            total_residual=("risk_score_residual", "sum"),
            mean_reduction_pct=("risk_reduction_pct", "mean"),
        )
        return g.round(2).sort_values("total_residual", ascending=False)

    def by_category(self) -> pd.DataFrame:
        col = "hazard_category"
        if col not in self.df.columns:
            raise ValueError("register has no hazard_category column")
        g = self.df.groupby(col).agg(
            hazards=("hazard_id", "count"),
            mean_initial=("risk_score_initial", "mean"),
            mean_residual=("risk_score_residual", "mean"),
            mean_reduction_pct=("risk_reduction_pct", "mean"),
        )
        return g.round(2).sort_values("mean_residual", ascending=False)

    def intolerable(self) -> pd.DataFrame:
        """Hazards still High or Critical after the planned controls."""
        return self.df[self.df["risk_band_residual"].isin(["High", "Critical"])].sort_values(
            "risk_score_residual", ascending=False
        )

    def top_risks(self, n: int = 10, stage: str = "initial") -> pd.DataFrame:
        col = f"risk_score_{stage}"
        cols = [
            "hazard_id",
            "area",
            "hazard_description",
            "likelihood_" + stage,
            "severity_" + stage,
            col,
            f"risk_band_{stage}",
        ]
        cols = [c for c in cols if c in self.df.columns]
        return self.df.nlargest(n, col)[cols]

    def ppe_reliance(self) -> pd.DataFrame:
        """Hazards whose control plan leans on PPE or procedure alone.

        A low control-effectiveness score against a high residual risk is the
        clearest signal that a control plan has been written for the audit file
        rather than for the hazard.
        """
        if "control_effectiveness" not in self.df.columns:
            raise ValueError("register has no control_hierarchy column")
        d = self.df[
            (self.df["control_effectiveness"] <= 0.5)
            & (self.df["risk_score_residual"] >= 6)
        ]
        return d[
            [
                "hazard_id",
                "area",
                "hazard_description",
                "control_hierarchy",
                "control_effectiveness",
                "risk_score_residual",
            ]
        ].sort_values("risk_score_residual", ascending=False)

    def matrix(self, stage: str = "residual") -> pd.DataFrame:
        """A 5 x 5 count matrix for plotting (severity rows, likelihood cols)."""
        m = pd.crosstab(
            self.df[f"severity_{stage}"],
            self.df[f"likelihood_{stage}"],
        )
        return m.reindex(index=range(1, 6), columns=range(1, 6)).fillna(0).astype(int)

    def legal_coverage(self) -> pd.DataFrame:
        """Which statutory instruments the register actually cites, and how often."""
        if "legal_reference" not in self.df.columns:
            raise ValueError("register has no legal_reference column")
        rows = []
        for hid, refs in zip(self.df["hazard_id"], self.df["legal_reference"]):
            for r in str(refs).split(";"):
                r = r.strip()
                if r:
                    rows.append({"hazard_id": hid, "legal_reference": r})
        d = pd.DataFrame(rows)
        return (
            d.groupby("legal_reference")
            .size()
            .rename("hazards_citing")
            .sort_values(ascending=False)
            .to_frame()
        )


def matrix_reference() -> pd.DataFrame:
    """The published 5 x 5 matrix with band labels — the document an auditor asks for."""
    rows = []
    for s in range(1, 6):
        for l in range(1, 6):
            rows.append(
                {
                    "severity": s,
                    "severity_label": SEVERITY_SCALE[s][0],
                    "likelihood": l,
                    "likelihood_label": LIKELIHOOD_SCALE[l][0],
                    "score": risk_score(l, s),
                    "band": risk_band(l, s),
                }
            )
    return pd.DataFrame(rows)


def scale_definitions() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The likelihood and severity descriptors, for inclusion in the HIRA document."""
    lik = pd.DataFrame(
        [{"level": k, "label": v[0], "definition": v[1]} for k, v in LIKELIHOOD_SCALE.items()]
    )
    sev = pd.DataFrame(
        [{"level": k, "label": v[0], "definition": v[1]} for k, v in SEVERITY_SCALE.items()]
    )
    return lik, sev


def jsa_from_hazard(register: RiskRegister, hazard_id: str, steps: Iterable[str]) -> pd.DataFrame:
    """Expand one register line into a Job Safety Analysis skeleton.

    A HIRA answers 'what can hurt someone in this area'. A JSA answers 'what
    can hurt someone at each step of this job'. This produces the second from
    the first so the two documents cannot drift apart.
    """
    row = register.df.loc[register.df["hazard_id"] == hazard_id]
    if row.empty:
        raise KeyError(f"hazard_id {hazard_id!r} not in register")
    r = row.iloc[0]
    return pd.DataFrame(
        {
            "step_no": range(1, len(list(steps)) + 1),
            "job_step": list(steps),
            "parent_hazard_id": hazard_id,
            "area": r["area"],
            "hazard": r["hazard_description"],
            "consequence": r.get("potential_consequence", ""),
            "controls": r.get("additional_controls", ""),
            "residual_band": r["risk_band_residual"],
        }
    )
