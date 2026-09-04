"""Ambient air-quality exposure analytics.

Built on the national hourly air-quality dataset. The purpose is not general
air-quality research: it is to answer three operational HSE questions.

1. What ambient particulate load does a site's outdoor workforce actually
   breathe, and how does it compare with the WHO guideline and the Bangladesh
   national standard?
2. When in the year and when in the day is that load worst, so that outdoor
   work can be scheduled around it?
3. How many shift-days per year would trigger a work-adjustment protocol?

Every function returns a table a plant manager can act on, not a p-value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    AQI_CATEGORIES,
    BD_NAAQS_PM25_ANNUAL,
    BD_NAAQS_PM25_DAILY,
    BD_NAAQS_PM10_DAILY,
    PROCESSED,
    RAW,
    WHO_PM25_ANNUAL,
    WHO_PM25_DAILY,
    WHO_PM10_DAILY,
)

POLLUTANTS = [
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
]


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def load_air_quality(path=None, city: str | None = None,
                     usecols: list | None = None) -> pd.DataFrame:
    """Load the hourly air-quality dataset.

    The file is large (over one million rows), so a city filter is applied
    during the read where possible rather than after.
    """
    path = path or (RAW / "bd_air_quality_hourly.csv.gz")
    # carbon_dioxide is loaded but never analysed: it is 74% missing, and the
    # completeness screen should report that rather than silently omit the column.
    cols = usecols or [
        "city_id", "city_name", "lat", "lon", "datetime",
        *POLLUTANTS, "carbon_dioxide", "aqi",
    ]
    df = pd.read_csv(path, usecols=cols)
    if city:
        df = df[df["city_name"] == city]
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df["date"] = df["datetime"].dt.date
    df["year"] = df["datetime"].dt.year
    df["month"] = df["datetime"].dt.month
    df["hour"] = df["datetime"].dt.hour
    return df


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-city record counts and date span — the honesty table.

    Any analysis of this dataset must state which cities have long records and
    which have short ones, because the source file is truncated.
    """
    g = df.groupby("city_name").agg(
        records=("datetime", "size"),
        first=("datetime", "min"),
        last=("datetime", "max"),
        lat=("lat", "first"),
        lon=("lon", "first"),
    )
    g["years_span"] = ((g["last"] - g["first"]).dt.days / 365.25).round(1)
    g["completeness_pct"] = (
        g["records"] / ((g["last"] - g["first"]).dt.total_seconds() / 3600 + 1) * 100
    ).round(1)
    return g.sort_values("records", ascending=False)


# --------------------------------------------------------------------------
# Exceedance analysis
# --------------------------------------------------------------------------
def daily_means(df: pd.DataFrame) -> pd.DataFrame:
    """Daily mean concentrations, the basis for 24-hour standard comparison."""
    d = (
        df.groupby(["city_name", "date"])
        .agg(
            pm2_5=("pm2_5", "mean"),
            pm10=("pm10", "mean"),
            aqi=("aqi", "mean"),
            hours=("datetime", "size"),
        )
        .reset_index()
    )
    # A day with fewer than 18 valid hours is not a valid 24-hour mean under
    # normal air-quality data-handling rules, so it is flagged rather than used.
    d["valid_24h"] = d["hours"] >= 18
    d["date"] = pd.to_datetime(d["date"])
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    return d


def exceedance_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Days per year above the WHO guideline and the Bangladesh standard."""
    d = daily_means(df)
    d = d[d["valid_24h"]]
    g = d.groupby(["city_name", "year"]).agg(
        valid_days=("date", "count"),
        mean_pm25=("pm2_5", "mean"),
        mean_pm10=("pm10", "mean"),
        max_pm25=("pm2_5", "max"),
        days_over_who_pm25=("pm2_5", lambda s: int((s > WHO_PM25_DAILY).sum())),
        days_over_bd_pm25=("pm2_5", lambda s: int((s > BD_NAAQS_PM25_DAILY).sum())),
        days_over_who_pm10=("pm10", lambda s: int((s > WHO_PM10_DAILY).sum())),
        days_over_bd_pm10=("pm10", lambda s: int((s > BD_NAAQS_PM10_DAILY).sum())),
    )
    g["pct_days_over_who_pm25"] = (
        g["days_over_who_pm25"] / g["valid_days"] * 100
    ).round(1)
    g["pct_days_over_bd_pm25"] = (
        g["days_over_bd_pm25"] / g["valid_days"] * 100
    ).round(1)
    g["annual_mean_vs_who"] = (g["mean_pm25"] / WHO_PM25_ANNUAL).round(1)
    g["annual_mean_vs_bd_standard"] = (g["mean_pm25"] / BD_NAAQS_PM25_ANNUAL).round(1)
    return g.round(2).reset_index()


def aqi_category(value: float) -> str:
    if pd.isna(value):
        return "No data"
    for lo, hi, label in AQI_CATEGORIES:
        if lo <= value <= hi:
            return label
    return "Beyond index"


def aqi_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Share of hours in each US EPA AQI category, by city."""
    d = df.dropna(subset=["aqi"]).copy()
    d["category"] = d["aqi"].map(aqi_category)
    order = [c[2] for c in AQI_CATEGORIES]
    out = (
        pd.crosstab(d["city_name"], d["category"], normalize="index")
        .reindex(columns=order)
        .fillna(0)
        * 100
    )
    return out.round(1)


# --------------------------------------------------------------------------
# Operational scheduling
# --------------------------------------------------------------------------
def monthly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Seasonal profile — which months outdoor work is most exposed."""
    g = df.groupby(["city_name", "month"]).agg(
        mean_pm25=("pm2_5", "mean"),
        mean_pm10=("pm10", "mean"),
        mean_aqi=("aqi", "mean"),
        p95_pm25=("pm2_5", lambda s: s.quantile(0.95)),
    )
    return g.round(1).reset_index()


def diurnal_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Hour-of-day profile — the basis for shift scheduling of outdoor tasks."""
    g = df.groupby(["city_name", "hour"]).agg(
        mean_pm25=("pm2_5", "mean"),
        mean_aqi=("aqi", "mean"),
        p95_pm25=("pm2_5", lambda s: s.quantile(0.95)),
    )
    return g.round(1).reset_index()


def shift_exposure(df: pd.DataFrame, shifts: dict | None = None) -> pd.DataFrame:
    """Mean exposure by working shift.

    Default shifts follow a typical three-shift Bangladeshi factory pattern.
    """
    shifts = shifts or {"A (06-14)": (6, 13), "B (14-22)": (14, 21), "C (22-06)": (22, 5)}
    rows = []
    for city, cd in df.groupby("city_name"):
        for name, (start, end) in shifts.items():
            if start <= end:
                mask = cd["hour"].between(start, end)
            else:  # wraps midnight
                mask = (cd["hour"] >= start) | (cd["hour"] <= end)
            sub = cd[mask]
            rows.append(
                {
                    "city_name": city,
                    "shift": name,
                    "hours_sampled": int(len(sub)),
                    "mean_pm2_5": round(sub["pm2_5"].mean(), 1),
                    "mean_pm10": round(sub["pm10"].mean(), 1),
                    "mean_aqi": round(sub["aqi"].mean(), 1),
                    "p95_pm2_5": round(sub["pm2_5"].quantile(0.95), 1),
                }
            )
    out = pd.DataFrame(rows)
    out["vs_who_daily_guideline"] = (out["mean_pm2_5"] / WHO_PM25_DAILY).round(2)
    return out


def work_adjustment_calendar(df: pd.DataFrame, city: str,
                             trigger_aqi: int = 150) -> pd.DataFrame:
    """Days per month that would trigger an outdoor-work adjustment protocol.

    This is the table that turns an air-quality dataset into an HSE control:
    it tells a plant how many shift-days a year the protocol would actually
    fire, which is what determines whether the protocol is workable.
    """
    d = df[df["city_name"] == city]
    if d.empty:
        raise KeyError(f"city {city!r} not in dataset")
    dm = daily_means(d)
    dm = dm[dm["valid_24h"]]
    dm["trigger"] = dm["aqi"] >= trigger_aqi
    g = (
        dm.groupby(["year", "month"])
        .agg(days=("date", "count"), trigger_days=("trigger", "sum"), mean_aqi=("aqi", "mean"))
        .reset_index()
    )
    g["trigger_pct"] = (g["trigger_days"] / g["days"] * 100).round(1)
    g["mean_aqi"] = g["mean_aqi"].round(0)
    return g


def annual_trend(df: pd.DataFrame, city: str) -> pd.DataFrame:
    """Long-run annual trend for a city with a multi-year record."""
    d = df[df["city_name"] == city]
    if d.empty:
        raise KeyError(f"city {city!r} not in dataset")
    dm = daily_means(d)
    dm = dm[dm["valid_24h"]]
    g = dm.groupby("year").agg(
        valid_days=("date", "count"),
        mean_pm25=("pm2_5", "mean"),
        median_pm25=("pm2_5", "median"),
        p95_pm25=("pm2_5", lambda s: s.quantile(0.95)),
        mean_aqi=("aqi", "mean"),
    )
    # Only report years with reasonable coverage.
    g["coverage_ok"] = g["valid_days"] >= 300
    return g.round(1).reset_index()


def trend_slope(annual: pd.DataFrame, value_col: str = "mean_pm25") -> dict:
    """Ordinary least-squares slope over years with adequate coverage.

    Reported with the number of years it rests on so the reader can judge it.
    """
    d = annual.copy()
    if "coverage_ok" in d.columns:
        d = d[d["coverage_ok"].astype(bool)]
    d = d.dropna(subset=[value_col])
    if len(d) < 3:
        return {"slope_per_year": None, "years": int(len(d)), "note": "insufficient years"}
    x = d["year"].to_numpy(dtype=float)
    y = d[value_col].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan
    return {
        "slope_per_year": round(float(slope), 3),
        "r_squared": round(float(r2), 3),
        "years": int(len(d)),
        "first_year": int(d["year"].min()),
        "last_year": int(d["year"].max()),
    }


def save_processed(frames: dict, outdir=None) -> list:
    outdir = outdir or PROCESSED
    written = []
    for name, frame in frames.items():
        p = outdir / f"{name}.csv"
        frame.to_csv(p, index=False)
        written.append(str(p))
    return written
