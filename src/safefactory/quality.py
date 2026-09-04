"""Automated data-integrity checks on the source air-quality dataset.

Written after two defects were found by hand in the published national hourly
air-quality file. Both would have silently corrupted every downstream figure,
and neither is visible in a summary statistic. They are now detected
automatically so that any refreshed copy of the dataset is screened before it
is used:

**Duplicate series.** Two named cities can carry a byte-identical hourly
record. The file is a gridded product, so city points falling in the same model
cell share one series. Treating them as independent locations inflates the
apparent sample and lets one grid cell vote twice in any cross-city ranking.

**Synthetic back-fill.** A series can rise monotonically year on year with
almost no interannual variability, then step discontinuously to a different
level. Real ambient particulate records do not behave that way: they carry
strong, irregular year-to-year variation driven by monsoon timing and
meteorology. A near-perfect monotone ramp is the signature of interpolated or
modelled back-fill, and any trend fitted through it measures the interpolation,
not the air.

Each check returns evidence, not just a verdict, so a reader can judge the call
for themselves.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# Duplicate series
# --------------------------------------------------------------------------
def find_duplicate_series(df: pd.DataFrame, value_col: str = "pm2_5",
                          min_overlap: int = 500) -> pd.DataFrame:
    """Find city pairs whose hourly values are identical over their overlap.

    Returns one row per duplicated pair with the overlap length and the exact
    match fraction, plus the distance implied by the two coordinate points.
    """
    from .siteindex import haversine_km

    wide = df.pivot_table(
        index="datetime", columns="city_name", values=value_col, aggfunc="first"
    )
    coords = df.groupby("city_name")[["lat", "lon"]].first()
    cities = list(wide.columns)
    rows = []
    for i, a in enumerate(cities):
        for b in cities[i + 1:]:
            pair = wide[[a, b]].dropna()
            if len(pair) < min_overlap:
                continue
            match = float((pair[a] == pair[b]).mean())
            if match >= 0.999:
                d = float(
                    haversine_km(
                        coords.loc[a, "lat"], coords.loc[a, "lon"],
                        coords.loc[b, "lat"], coords.loc[b, "lon"],
                    )
                )
                rows.append(
                    {
                        "city_a": a,
                        "city_b": b,
                        "overlap_hours": int(len(pair)),
                        "identical_fraction": round(match, 4),
                        "separation_km": round(d, 2),
                    }
                )
    return pd.DataFrame(rows)


def independent_cities(df: pd.DataFrame, duplicates: pd.DataFrame) -> list:
    """The list of cities after collapsing each duplicate group to one member."""
    drop = set()
    for _, r in duplicates.iterrows():
        if r["city_a"] not in drop:
            drop.add(r["city_b"])
    return sorted(set(df["city_name"]) - drop)


# --------------------------------------------------------------------------
# Synthetic back-fill
# --------------------------------------------------------------------------
def monotonicity_report(annual: pd.DataFrame, value_col: str = "mean_pm25",
                        year_col: str = "year") -> dict:
    """Test an annual series for the signature of interpolated back-fill.

    Three symptoms are measured:

    * ``monotone_fraction`` — the share of consecutive year-pairs moving in the
      same direction. A real record sits near 0.5; a ramp sits at 1.0.
    * ``r_squared_linear`` — how completely a straight line explains the series.
      Values above roughly 0.98 across many years are not physically plausible
      for ambient particulate matter.
    * ``max_step`` — the largest single year-on-year change, which locates the
      splice between a synthetic segment and a measured one.
    """
    d = annual.dropna(subset=[value_col]).sort_values(year_col)
    if len(d) < 5:
        return {
            "years": int(len(d)),
            "first_year": int(d[year_col].min()) if len(d) else None,
            "last_year": int(d[year_col].max()) if len(d) else None,
            "monotone_fraction": None,
            "r_squared_linear": None,
            "max_step": None,
            "max_step_between": None,
            "suspected_synthetic": False,
            "screened": False,
            "verdict": (
                "Too few years to screen for back-fill, and too few to support "
                "a trend claim either way."
            ),
        }
    y = d[value_col].to_numpy(dtype=float)
    x = d[year_col].to_numpy(dtype=float)
    diffs = np.diff(y)
    monotone_fraction = float(max((diffs > 0).mean(), (diffs < 0).mean()))
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan
    step_i = int(np.argmax(np.abs(diffs)))
    suspect = monotone_fraction >= 0.95 and r2 >= 0.95
    return {
        "years": int(len(d)),
        "first_year": int(x[0]),
        "last_year": int(x[-1]),
        "monotone_fraction": round(monotone_fraction, 3),
        "r_squared_linear": round(float(r2), 3),
        "max_step": round(float(diffs[step_i]), 1),
        "max_step_between": f"{int(x[step_i])}-{int(x[step_i + 1])}",
        "suspected_synthetic": bool(suspect),
        "screened": True,
        "verdict": (
            "Series shows the signature of interpolated or modelled back-fill: "
            "near-monotone year-on-year change with almost no interannual "
            "variability. Do not fit a trend through this segment."
            if suspect
            else "No back-fill signature detected."
        ),
    }


def segment_by_step(annual: pd.DataFrame, value_col: str = "mean_pm25",
                    year_col: str = "year", threshold: float = 25.0) -> pd.DataFrame:
    """Split an annual series at large discontinuities and describe each segment.

    Used to separate a synthetic segment from a measured one so the measured
    part can still be analysed.
    """
    d = annual.dropna(subset=[value_col]).sort_values(year_col).reset_index(drop=True)
    diffs = d[value_col].diff().abs()
    seg = (diffs > threshold).cumsum()
    d["segment"] = seg
    g = d.groupby("segment").agg(
        first_year=(year_col, "min"),
        last_year=(year_col, "max"),
        years=(year_col, "count"),
        mean=(value_col, "mean"),
        std=(value_col, "std"),
    )
    g["coefficient_of_variation"] = (g["std"] / g["mean"]).round(3)
    return g.round(2).reset_index()


# --------------------------------------------------------------------------
# Completeness
# --------------------------------------------------------------------------
def completeness_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column missingness and physically impossible values."""
    rows = []
    impossible = {
        "pm2_5": (0, None),
        "pm10": (0, None),
        "carbon_monoxide": (0, None),
        "nitrogen_dioxide": (0, None),
        "sulphur_dioxide": (0, None),
        "ozone": (0, None),
        "aqi": (0, 500),
    }
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = df[col]
        lo_hi = impossible.get(col)
        n_bad = 0
        if lo_hi:
            lo, hi = lo_hi
            if lo is not None:
                n_bad += int((s < lo).sum())
            if hi is not None:
                n_bad += int((s > hi).sum())
        rows.append(
            {
                "column": col,
                "missing": int(s.isna().sum()),
                "missing_pct": round(float(s.isna().mean() * 100), 3),
                "out_of_physical_range": n_bad,
                "min": round(float(s.min()), 2) if s.notna().any() else None,
                "max": round(float(s.max()), 2) if s.notna().any() else None,
            }
        )
    return pd.DataFrame(rows)


def backfill_screen(annual: pd.DataFrame, value_col: str = "mean_pm25",
                    year_col: str = "year", threshold: float = 25.0) -> pd.DataFrame:
    """Screen each continuous segment of an annual series for back-fill.

    Screening the whole series at once is the wrong test and will miss the
    defect: a synthetic ramp followed by a real, noisier segment produces a
    poor overall linear fit, which reads as 'no problem'. The series must be
    split at its discontinuities first, then each segment tested on its own.
    """
    d = annual.dropna(subset=[value_col]).sort_values(year_col).reset_index(drop=True)
    d["segment"] = (d[value_col].diff().abs() > threshold).cumsum()
    rows = []
    for seg, part in d.groupby("segment"):
        rep = monotonicity_report(part, value_col=value_col, year_col=year_col)
        rep["segment"] = int(seg)
        rows.append(rep)
    out = pd.DataFrame(rows)
    front = ["segment", "first_year", "last_year", "years"]
    cols = [c for c in front if c in out.columns] + [
        c for c in out.columns if c not in front
    ]
    return out[cols]


def run_all(df: pd.DataFrame, annual: pd.DataFrame) -> dict:
    """Run every check and return a single report object."""
    dups = find_duplicate_series(df)
    screen = backfill_screen(annual)
    suspect = screen[screen["suspected_synthetic"].fillna(False).astype(bool)]
    # A segment is usable for a trend only if it was actually screened AND
    # passed. Segments too short to screen are not 'clean' — they are unknown,
    # and they are excluded from any trend claim.
    trusted = screen[
        screen["screened"].fillna(False).astype(bool)
        & ~screen["suspected_synthetic"].fillna(True).astype(bool)
    ]
    return {
        "records": int(len(df)),
        "named_cities": int(df["city_name"].nunique()),
        "duplicate_pairs": dups,
        "independent_cities": independent_cities(df, dups),
        "n_independent_cities": len(independent_cities(df, dups)),
        "completeness": completeness_report(df),
        "backfill_by_segment": screen,
        "suspect_segments": suspect,
        "trusted_segments": trusted,
        "any_synthetic": bool(len(suspect) > 0),
        "segments": segment_by_step(annual),
    }
