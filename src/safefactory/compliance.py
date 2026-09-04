"""ISO 45001:2018 x Bangladesh statutory compliance matrix and audit scoring.

The matrix is the deliverable a factory HSE function is actually judged on: it
maps every ISO clause to the Bangladeshi instrument that makes it a legal duty,
names the evidence, and scores where the site stands.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .config import REFERENCE

# Conformity scoring. The weights are deliberately steep: a critical
# non-conformance cannot be averaged away by a long list of conformities.
CONFORMITY_SCORES = {
    "Conforms": 1.0,
    "Minor NC": 0.6,
    "Major NC": 0.2,
    "Not Conform": 0.0,
    "Not Started": 0.0,
    "Not Applicable": None,
}

CRITICALITY_WEIGHT = {"Critical": 3.0, "High": 2.0, "Medium": 1.0, "Low": 0.5}

ISO_CLAUSE_TITLES = {
    "4": "Context of the organization",
    "5": "Leadership and worker participation",
    "6": "Planning",
    "7": "Support",
    "8": "Operation",
    "9": "Performance evaluation",
    "10": "Improvement",
}


@dataclass
class ComplianceMatrix:
    """The compliance register, with scoring and gap reporting."""

    df: pd.DataFrame = field(repr=False)
    REQUIRED = [
        "req_id",
        "iso45001_clause",
        "bd_legal_reference",
        "requirement",
        "evidence_required",
        "criticality",
    ]

    def __post_init__(self) -> None:
        missing = [c for c in self.REQUIRED if c not in self.df.columns]
        if missing:
            raise ValueError(f"compliance matrix is missing required columns: {missing}")
        self.df = self.df.copy()
        if "status" not in self.df.columns:
            self.df["status"] = "Not Started"
        self.df["iso_clause_group"] = (
            self.df["iso45001_clause"].astype(str).str.split(".").str[0]
        )
        self.df["iso_clause_title"] = self.df["iso_clause_group"].map(ISO_CLAUSE_TITLES)

    @classmethod
    def from_csv(cls, path=None) -> "ComplianceMatrix":
        path = path or (REFERENCE / "compliance_matrix.csv")
        return cls(pd.read_csv(path))

    # -- assessment --------------------------------------------------------
    def set_status(self, req_id: str, status: str, note: str = "") -> None:
        if status not in CONFORMITY_SCORES:
            raise ValueError(
                f"unknown status {status!r}. Allowed: {sorted(CONFORMITY_SCORES)}"
            )
        if req_id not in set(self.df["req_id"]):
            raise KeyError(f"req_id {req_id!r} not in matrix")
        self.df.loc[self.df["req_id"] == req_id, "status"] = status
        if note:
            self.df.loc[self.df["req_id"] == req_id, "assessor_note"] = note

    def apply_statuses(self, statuses: dict[str, str]) -> None:
        for req_id, status in statuses.items():
            self.set_status(req_id, status)

    def scored(self) -> pd.DataFrame:
        d = self.df.copy()
        d["score"] = d["status"].map(CONFORMITY_SCORES)
        d["weight"] = d["criticality"].map(CRITICALITY_WEIGHT).fillna(1.0)
        d["weighted_score"] = d["score"] * d["weight"]
        return d

    def conformity_index(self) -> dict:
        """Weighted conformity index, 0-100, excluding Not Applicable items."""
        d = self.scored()
        d = d[d["score"].notna()]
        if d.empty:
            return {"conformity_index": None, "assessed": 0}
        idx = d["weighted_score"].sum() / d["weight"].sum() * 100
        return {
            "conformity_index": round(idx, 1),
            "assessed": int(len(d)),
            "conforms": int((d["status"] == "Conforms").sum()),
            "minor_nc": int((d["status"] == "Minor NC").sum()),
            "major_nc": int((d["status"] == "Major NC").sum()),
            "not_conform": int((d["status"] == "Not Conform").sum()),
            "not_started": int((d["status"] == "Not Started").sum()),
            "critical_gaps": int(
                (
                    (d["criticality"] == "Critical")
                    & (d["status"].isin(["Major NC", "Not Conform", "Not Started"]))
                ).sum()
            ),
        }

    def by_clause(self) -> pd.DataFrame:
        d = self.scored()
        d = d[d["score"].notna()]
        g = d.groupby(["iso_clause_group", "iso_clause_title"]).apply(
            lambda x: pd.Series(
                {
                    "requirements": len(x),
                    "conformity_pct": round(
                        x["weighted_score"].sum() / x["weight"].sum() * 100, 1
                    ),
                    "critical_gaps": int(
                        (
                            (x["criticality"] == "Critical")
                            & (x["status"].isin(["Major NC", "Not Conform", "Not Started"]))
                        ).sum()
                    ),
                }
            ),
            include_groups=False,
        )
        return g.reset_index().sort_values("iso_clause_group")

    def gaps(self, min_criticality: str = "High") -> pd.DataFrame:
        """Open non-conformances at or above a criticality, worst first."""
        order = ["Low", "Medium", "High", "Critical"]
        floor = order.index(min_criticality)
        d = self.df[
            self.df["status"].isin(["Major NC", "Not Conform", "Not Started", "Minor NC"])
        ].copy()
        d["crit_rank"] = d["criticality"].map({c: i for i, c in enumerate(order)})
        d = d[d["crit_rank"] >= floor]
        cols = [
            "req_id",
            "domain",
            "iso45001_clause",
            "bd_legal_reference",
            "requirement",
            "evidence_required",
            "criticality",
            "status",
        ]
        cols = [c for c in cols if c in d.columns]
        return d.sort_values(["crit_rank", "req_id"], ascending=[False, True])[cols]

    def legal_register(self) -> pd.DataFrame:
        """The statutory register required by ISO 45001 clause 6.1.3."""
        rows = []
        for _, r in self.df.iterrows():
            for ref in str(r["bd_legal_reference"]).split(";"):
                ref = ref.strip()
                if ref:
                    rows.append(
                        {
                            "legal_reference": ref,
                            "req_id": r["req_id"],
                            "requirement": r["requirement"],
                            "status": r["status"],
                            "criticality": r["criticality"],
                        }
                    )
        d = pd.DataFrame(rows)
        return (
            d.groupby("legal_reference")
            .agg(
                requirements=("req_id", "count"),
                critical=("criticality", lambda s: (s == "Critical").sum()),
                open_items=("status", lambda s: (s != "Conforms").sum()),
            )
            .sort_values(["critical", "requirements"], ascending=False)
        )

    def audit_plan(self) -> pd.DataFrame:
        """A frequency-driven audit programme (ISO 45001 clause 9.2)."""
        cols = [
            c
            for c in ["req_id", "domain", "requirement", "verification_method", "frequency", "criticality"]
            if c in self.df.columns
        ]
        d = self.df[cols].copy()
        order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        d["_o"] = d["criticality"].map(order)
        return d.sort_values(["_o", "req_id"]).drop(columns="_o")
