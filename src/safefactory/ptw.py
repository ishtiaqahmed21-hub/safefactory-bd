"""Permit to Work and Lockout-Tagout.

The value of a PTW system is not the form. It is that an expired permit, a
missing gas test, an absent standby person or an unclosed fire watch can be
detected without reading every sheet in the file. That detection is what this
module does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from .config import GAS_TEST_LIMITS, PERMIT_TYPES


# --------------------------------------------------------------------------
# Gas testing
# --------------------------------------------------------------------------
def evaluate_gas_test(readings: dict) -> dict:
    """Check a gas test against the acceptance criteria in ``config``.

    Returns a pass/fail verdict plus the specific readings that failed, so the
    permit issuer is told which parameter blocks the job rather than simply
    'failed'.
    """
    failures = []
    checked = {}
    for param, (lo, hi) in GAS_TEST_LIMITS.items():
        if param not in readings or readings[param] is None:
            continue
        val = float(readings[param])
        ok = lo <= val <= hi
        checked[param] = {"value": val, "limit": (lo, hi), "pass": ok}
        if not ok:
            failures.append(
                f"{param} = {val} (acceptable {lo}-{hi})"
            )
    if not checked:
        return {"pass": False, "reason": "no readings supplied", "detail": {}, "failures": []}
    return {
        "pass": len(failures) == 0,
        "reason": "within limits" if not failures else "; ".join(failures),
        "detail": checked,
        "failures": failures,
    }


# --------------------------------------------------------------------------
# Permits
# --------------------------------------------------------------------------
@dataclass
class Permit:
    permit_id: str
    permit_type: str
    area: str
    description: str
    issued_by: str
    accepted_by: str
    start: datetime
    end: datetime
    isolations: list = field(default_factory=list)
    gas_test: dict | None = None
    standby_person: str | None = None
    fire_watch_completed: bool | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None

    def __post_init__(self) -> None:
        if self.permit_type not in PERMIT_TYPES:
            raise ValueError(
                f"unknown permit type {self.permit_type!r}. "
                f"Allowed: {sorted(PERMIT_TYPES)}"
            )
        self.start = pd.Timestamp(self.start).to_pydatetime()
        self.end = pd.Timestamp(self.end).to_pydatetime()
        if self.end <= self.start:
            raise ValueError("permit end must be after start")

    # -- rules -------------------------------------------------------------
    @property
    def rules(self) -> dict:
        return PERMIT_TYPES[self.permit_type]

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    def validate(self, now: datetime | None = None) -> dict:
        """Return every rule this permit breaks, with the rule named."""
        now = now or datetime.now()
        issues = []

        if self.duration_hours > self.rules["max_validity_hours"]:
            issues.append(
                f"validity {self.duration_hours:.1f} h exceeds the "
                f"{self.rules['max_validity_hours']} h maximum for {self.permit_type}"
            )
        if self.rules["gas_test_required"]:
            if not self.gas_test:
                issues.append("gas test required for this permit type but none recorded")
            else:
                verdict = evaluate_gas_test(self.gas_test)
                if not verdict["pass"]:
                    issues.append(f"gas test not acceptable: {verdict['reason']}")
        if self.rules["standby_required"] and not self.standby_person:
            issues.append("standby person required for this permit type but none named")
        if self.issued_by and self.accepted_by and self.issued_by == self.accepted_by:
            issues.append(
                "issuer and acceptor are the same person — no independent check"
            )
        if self.permit_type in {"Confined Space Entry", "Line Breaking", "Electrical Work"} and not self.isolations:
            issues.append("no energy isolations recorded for a permit type that requires LOTO")
        if self.closed_at is None and now > self.end:
            issues.append(
                f"permit expired {(now - self.end).total_seconds()/3600:.1f} h ago and is not closed out"
            )
        if (
            self.rules["fire_watch_minutes_after"] > 0
            and self.closed_at is not None
            and not self.fire_watch_completed
        ):
            issues.append(
                f"closed without confirming the {self.rules['fire_watch_minutes_after']}-minute fire watch"
            )
        if (
            self.rules["fire_watch_minutes_after"] > 0
            and self.closed_at is not None
            and self.closed_at < self.end + timedelta(minutes=self.rules["fire_watch_minutes_after"])
            and self.fire_watch_completed
        ):
            issues.append(
                "fire watch recorded as complete but the permit was closed before the required watch period elapsed"
            )

        return {
            "permit_id": self.permit_id,
            "permit_type": self.permit_type,
            "valid": len(issues) == 0,
            "issues": issues,
            "status": self.status(now),
        }

    def status(self, now: datetime | None = None) -> str:
        now = now or datetime.now()
        if self.closed_at is not None:
            return "Closed"
        if now < self.start:
            return "Issued - not started"
        if now > self.end:
            return "EXPIRED - not closed"
        return "Active"


@dataclass
class PermitRegister:
    permits: list[Permit] = field(default_factory=list)

    def add(self, permit: Permit) -> None:
        if any(p.permit_id == permit.permit_id for p in self.permits):
            raise ValueError(f"duplicate permit_id {permit.permit_id!r}")
        self.permits.append(permit)

    def to_frame(self, now: datetime | None = None) -> pd.DataFrame:
        rows = []
        for p in self.permits:
            v = p.validate(now)
            rows.append(
                {
                    "permit_id": p.permit_id,
                    "permit_type": p.permit_type,
                    "area": p.area,
                    "description": p.description,
                    "issued_by": p.issued_by,
                    "accepted_by": p.accepted_by,
                    "start": p.start,
                    "end": p.end,
                    "duration_h": round(p.duration_hours, 1),
                    "standby_person": p.standby_person,
                    "n_isolations": len(p.isolations),
                    "status": v["status"],
                    "compliant": v["valid"],
                    "issues": "; ".join(v["issues"]),
                    "n_issues": len(v["issues"]),
                }
            )
        return pd.DataFrame(rows)

    def audit(self, now: datetime | None = None) -> dict:
        """Permit-system health, the number a Safety Committee should see monthly."""
        df = self.to_frame(now)
        if df.empty:
            return {"permits": 0, "compliance_rate_pct": None}
        return {
            "permits": int(len(df)),
            "compliant": int(df["compliant"].sum()),
            "non_compliant": int((~df["compliant"]).sum()),
            "compliance_rate_pct": round(df["compliant"].mean() * 100, 1),
            "expired_not_closed": int((df["status"] == "EXPIRED - not closed").sum()),
            "active": int((df["status"] == "Active").sum()),
            "total_findings": int(df["n_issues"].sum()),
            "by_type": df.groupby("permit_type")["compliant"].agg(["count", "sum"]).to_dict("index"),
        }


# --------------------------------------------------------------------------
# Lockout-Tagout
# --------------------------------------------------------------------------
ENERGY_TYPES = [
    "Electrical",
    "Mechanical",
    "Hydraulic",
    "Pneumatic",
    "Thermal",
    "Chemical",
    "Gravity",
    "Stored (spring / capacitor / pressure)",
]


@dataclass
class LOTOPoint:
    """One isolation point on an equipment-specific isolation sheet."""

    point_id: str
    equipment: str
    energy_type: str
    isolation_device: str
    isolation_method: str
    verification_method: str
    locked: bool = False
    tagged: bool = False
    verified_zero_energy: bool = False
    applied_by: str | None = None

    def __post_init__(self) -> None:
        if self.energy_type not in ENERGY_TYPES:
            raise ValueError(
                f"unknown energy type {self.energy_type!r}. Allowed: {ENERGY_TYPES}"
            )

    def check(self) -> dict:
        issues = []
        if not self.locked:
            issues.append("no lock applied")
        if not self.tagged:
            issues.append("no danger tag applied")
        if not self.verified_zero_energy:
            issues.append("zero-energy state not verified by try-out")
        if not self.applied_by:
            issues.append("no named person applied the isolation")
        return {"point_id": self.point_id, "safe": not issues, "issues": issues}


@dataclass
class LOTOProcedure:
    """The equipment-specific isolation procedure required before maintenance."""

    equipment: str
    prepared_by: str
    points: list[LOTOPoint] = field(default_factory=list)

    def add(self, point: LOTOPoint) -> None:
        self.points.append(point)

    def energy_types_covered(self) -> set:
        return {p.energy_type for p in self.points}

    def validate(self) -> dict:
        """Confirm the isolation is complete before work is allowed to start."""
        point_checks = [p.check() for p in self.points]
        unsafe = [c for c in point_checks if not c["safe"]]
        issues = []
        if not self.points:
            issues.append("no isolation points defined for this equipment")
        for c in unsafe:
            issues.append(f"{c['point_id']}: " + "; ".join(c["issues"]))
        # A single-point electrical lockout on plant that also holds stored
        # pressure or gravity energy is the classic fatal gap.
        covered = self.energy_types_covered()
        if covered == {"Electrical"} and len(self.points) == 1:
            issues.append(
                "only electrical energy isolated — confirm there is no stored "
                "pressure, gravity, thermal or chemical energy on this equipment"
            )
        return {
            "equipment": self.equipment,
            "points": len(self.points),
            "energy_types": sorted(covered),
            "safe_to_work": len(issues) == 0,
            "issues": issues,
        }

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "point_id": p.point_id,
                    "equipment": p.equipment,
                    "energy_type": p.energy_type,
                    "isolation_device": p.isolation_device,
                    "isolation_method": p.isolation_method,
                    "verification_method": p.verification_method,
                    "locked": p.locked,
                    "tagged": p.tagged,
                    "verified_zero_energy": p.verified_zero_energy,
                    "applied_by": p.applied_by,
                    "safe": p.check()["safe"],
                }
                for p in self.points
            ]
        )
