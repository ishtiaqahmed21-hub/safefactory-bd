#!/usr/bin/env python3
"""Generate a SYNTHETIC demonstration incident register.

This file exists so the dashboard has something to display before a real plant
loads its own data. Every row is generated, not observed.

It is deliberately NOT presented as real plant data anywhere in this project,
and the output file carries the word ``synthetic`` in its name and in a header
column so it cannot be mistaken for a genuine record. The generator is seeded,
so the demo is reproducible.

The event mix is shaped by the hazard profile in the HIRA register rather than
drawn uniformly, so the resulting Pareto and area rankings are at least
internally consistent with the risk assessment.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from safefactory.config import PROCESSED  # noqa: E402

RNG = np.random.default_rng(20260904)

# Area, its share of events, and the causes credible in that area.
AREA_PROFILE = {
    "Powder Blending & Packing": (0.18, ["Manual handling", "Caught in machinery",
                                        "Slip trip fall", "Dust exposure"]),
    "Noodle & Snack Frying Line": (0.16, ["Contact with hot surface", "Hot oil splash",
                                          "Slip trip fall", "Caught in machinery"]),
    "Warehouse & Yard": (0.20, ["Struck by forklift", "Falling load", "Manual handling",
                                "Slip trip fall"]),
    "Boiler House": (0.06, ["Contact with hot surface", "Steam release", "Slip trip fall"]),
    "Refrigeration Plant": (0.05, ["Chemical exposure", "Cold burn", "Slip trip fall"]),
    "CIP & Chemical Store": (0.09, ["Chemical splash", "Slip trip fall", "Manual handling"]),
    "Biscuit & Wafer Baking": (0.10, ["Contact with hot surface", "Caught in machinery",
                                      "Slip trip fall"]),
    "Maintenance Workshop": (0.10, ["Hand tool injury", "Eye injury from grinding",
                                    "Electric shock", "Fall from height"]),
    "Whole Site": (0.06, ["Slip trip fall", "Road/traffic", "Manual handling"]),
}

# A healthy reporting culture is dominated by near misses. This mix is what a
# plant with a working reporting system looks like, and the dashboard's
# reporting-health check is calibrated against it.
CLASS_MIX = {
    "Near Miss": 0.78,
    "First Aid Case": 0.135,
    "Medical Treatment Case": 0.05,
    "Restricted Work Case": 0.020,
    "Lost Time Injury": 0.015,
}

ACTION_STATUS = ["Verified effective", "Closed - pending verification", "In progress", "Overdue"]
ACTION_WEIGHTS = [0.55, 0.20, 0.17, 0.08]


def make(n: int = 340, start: str = "2025-01-01", end: str = "2026-08-31") -> pd.DataFrame:
    areas = list(AREA_PROFILE)
    p = np.array([AREA_PROFILE[a][0] for a in areas], dtype=float)
    p = p / p.sum()

    dates = pd.to_datetime(
        RNG.integers(
            pd.Timestamp(start).value // 10**9,
            pd.Timestamp(end).value // 10**9,
            n,
        ),
        unit="s",
    ).normalize()

    chosen_areas = RNG.choice(areas, size=n, p=p)
    causes = [RNG.choice(AREA_PROFILE[a][1]) for a in chosen_areas]
    classes = RNG.choice(list(CLASS_MIX), size=n, p=list(CLASS_MIX.values()))

    days_lost = []
    for c in classes:
        if c == "Lost Time Injury":
            days_lost.append(int(RNG.gamma(shape=2.0, scale=6.0)) + 1)
        elif c == "Restricted Work Case":
            days_lost.append(0)
        else:
            days_lost.append(0)

    df = pd.DataFrame(
        {
            "incident_id": [f"INC-{i:04d}" for i in range(1, n + 1)],
            "date": dates,
            "area": chosen_areas,
            "classification": classes,
            "immediate_cause": causes,
            "days_lost": days_lost,
            "shift": RNG.choice(["A (06-14)", "B (14-22)", "C (22-06)"], n, p=[0.4, 0.38, 0.22]),
            "reported_by_role": RNG.choice(
                ["Operator", "Supervisor", "Maintenance", "Contractor", "HSE"],
                n, p=[0.46, 0.22, 0.16, 0.10, 0.06]
            ),
            "action_status": RNG.choice(ACTION_STATUS, n, p=ACTION_WEIGHTS),
            "data_origin": "SYNTHETIC - generated for demonstration, not observed",
        }
    ).sort_values("date").reset_index(drop=True)

    df["action_owner"] = RNG.choice(
        ["Manager - Production", "Manager - Maintenance", "Warehouse Manager",
         "HSE Executive", "Manager - Utilities"], len(df)
    )
    df["action_due"] = df["date"] + pd.to_timedelta(RNG.integers(7, 60, len(df)), unit="D")
    df["corrective_action"] = "See investigation record " + df["incident_id"]
    return df


def main() -> None:
    df = make()
    out = PROCESSED / "incidents_synthetic_demo.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} SYNTHETIC demonstration incidents to {out}")
    print(df["classification"].value_counts().to_string())


if __name__ == "__main__":
    main()
