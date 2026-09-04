#!/usr/bin/env python3
"""Build every processed table the dashboard and the report depend on.

Run once after cloning:

    python scripts/build_dataset.py

Reads only from ``data/raw`` and ``data/reference``; writes only to
``data/processed``. Nothing downstream reads a raw file directly, so the
provenance of every figure in the report is a single hop from this script.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from safefactory import exposure, quality, siteindex  # noqa: E402
from safefactory.compliance import ComplianceMatrix  # noqa: E402
from safefactory.config import PROCESSED, RAW, REFERENCE  # noqa: E402
from safefactory.risk import RiskRegister, matrix_reference, scale_definitions  # noqa: E402


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_air_quality() -> pd.DataFrame:
    log("Loading hourly air-quality dataset (this reads ~1M rows)...")
    aq = exposure.load_air_quality()
    log(f"  {len(aq):,} hourly records across {aq['city_name'].nunique()} cities")

    log("Building coverage report...")
    cov = exposure.coverage_report(aq).reset_index()
    cov.to_csv(PROCESSED / "air_coverage.csv", index=False)

    log("Building Dhaka annual series (2000-2025)...")
    trend = exposure.annual_trend(aq, "Dhaka")
    trend.to_csv(PROCESSED / "air_dhaka_annual_trend.csv", index=False)

    # ----------------------------------------------------------------------
    # Data-integrity screening. Run BEFORE any trend is reported, because the
    # screen decides whether a trend may be reported at all.
    # ----------------------------------------------------------------------
    log("Screening the source dataset for integrity defects...")
    qa = quality.run_all(aq, trend)
    qa["duplicate_pairs"].to_csv(PROCESSED / "qa_duplicate_series.csv", index=False)
    qa["completeness"].to_csv(PROCESSED / "qa_completeness.csv", index=False)
    qa["segments"].to_csv(PROCESSED / "qa_dhaka_segments.csv", index=False)
    qa["backfill_by_segment"].to_csv(PROCESSED / "qa_backfill_screen.csv", index=False)
    pd.DataFrame({"independent_city": qa["independent_cities"]}).to_csv(
        PROCESSED / "qa_independent_cities.csv", index=False
    )
    log(f"  {len(qa['duplicate_pairs'])} duplicate city series found; "
        f"{qa['n_independent_cities']} of {qa['named_cities']} named cities are independent")
    for _, s in qa["backfill_by_segment"].iterrows():
        span = (
            f"{int(s['first_year'])}-{int(s['last_year'])}"
            if pd.notna(s["first_year"])
            else "n/a"
        )
        log(f"  segment {span} ({int(s['years'])} yr): "
            f"monotone={s['monotone_fraction']}, R2={s['r_squared_linear']}, "
            f"screened={s['screened']}, synthetic={s['suspected_synthetic']}")

    if qa["any_synthetic"]:
        keep = qa["trusted_segments"]
        if len(keep):
            k = keep.loc[keep["years"].idxmax()]
            trusted = trend[
                (trend["year"] >= k["first_year"]) & (trend["year"] <= k["last_year"])
            ]
            log(f"  REJECTED synthetic segment(s); trend restricted to "
                f"{int(k['first_year'])}-{int(k['last_year'])}")
            slope = exposure.trend_slope(trusted)
            slope["restricted_to"] = f"{int(k['first_year'])}-{int(k['last_year'])}"
            slope["reason"] = (
                "One or more segments failed the back-fill screen and were excluded."
            )
        else:
            log("  REJECTED: no segment both passes the screen and is long enough. "
                "No long-run trend will be reported from this dataset.")
            slope = {
                "slope_per_year": None,
                "years": 0,
                "reason": (
                    "The only long segment failed the back-fill screen; the remaining "
                    "segments are too short to support a trend. No long-run trend is "
                    "claimed from this dataset."
                ),
            }
    else:
        slope = exposure.trend_slope(trend)
    pd.DataFrame([slope]).to_csv(PROCESSED / "air_dhaka_trend_slope.csv", index=False)
    log(f"  Dhaka PM2.5 trend after screening: {slope}")

    # ----------------------------------------------------------------------
    # THE ANALYSIS WINDOW.
    #
    # Two separate problems force the same restriction, and both must be
    # applied to EVERY downstream figure, not only to the cross-city ones:
    #
    # 1. Dhaka carries a 26-year record while the other cities begin in August
    #    2022. Averaging each city over its own period would compare a 26-year
    #    mean against a 3-year mean and then rank sites on the difference.
    # 2. Dhaka's pre-2022 segment failed the back-fill screen above. Any
    #    seasonal, diurnal or shift profile computed over the full record
    #    inherits that synthetic segment and reports an exposure roughly twice
    #    the measured one.
    #
    # Both are solved by the same window: the period every city shares, which
    # also begins after the splice. The window is written into the outputs so
    # it travels with the numbers.
    # ----------------------------------------------------------------------
    log("Determining the common analysis window across cities...")
    spans = aq.groupby("city_name")["datetime"].agg(["min", "max"])
    # Ignore cities whose record stops early; they cannot support a common
    # window and are reported separately rather than silently distorting it.
    latest_end = spans["max"].max()
    full_cities = spans[spans["max"] >= latest_end - pd.Timedelta(days=30)].index
    window_start = spans.loc[full_cities, "min"].max()
    window_end = spans.loc[full_cities, "max"].min()
    log(f"  common window: {window_start.date()} to {window_end.date()} "
        f"across {len(full_cities)} of {aq['city_name'].nunique()} cities")

    common = aq[
        aq["city_name"].isin(full_cities)
        & aq["datetime"].between(window_start, window_end)
    ]

    log("Building exceedance, profile and distribution tables on the window...")
    exposure.exceedance_summary(common).to_csv(
        PROCESSED / "air_exceedance_by_year.csv", index=False)
    exposure.monthly_profile(common).to_csv(
        PROCESSED / "air_monthly_profile.csv", index=False)
    exposure.diurnal_profile(common).to_csv(
        PROCESSED / "air_diurnal_profile.csv", index=False)
    exposure.shift_exposure(common).to_csv(
        PROCESSED / "air_shift_exposure.csv", index=False)
    exposure.aqi_distribution(common).reset_index().to_csv(
        PROCESSED / "air_aqi_distribution.csv", index=False)
    exposure.work_adjustment_calendar(common, "Dhaka").to_csv(
        PROCESSED / "air_dhaka_work_adjustment.csv", index=False)

    city = (
        common.groupby("city_name")
        .agg(
            lat=("lat", "first"),
            lon=("lon", "first"),
            hours=("datetime", "size"),
            mean_pm2_5=("pm2_5", "mean"),
            mean_pm10=("pm10", "mean"),
            mean_aqi=("aqi", "mean"),
            p95_pm2_5=("pm2_5", lambda s: s.quantile(0.95)),
        )
        .round(2)
        .reset_index()
    )
    pct = (
        exposure.exceedance_summary(common)
        .groupby("city_name")["pct_days_over_who_pm25"]
        .mean()
        .round(1)
        .reset_index()
    )
    city = city.merge(pct, on="city_name", how="left")
    city["window_start"] = str(window_start.date())
    city["window_end"] = str(window_end.date())
    city.to_csv(PROCESSED / "city_air_summary.csv", index=False)
    log(f"  wrote city_air_summary.csv ({len(city)} cities, common window)")

    # The full-period, per-city view is kept as well, clearly separated, so a
    # reader can see both and can never confuse one for the other.
    (
        aq.groupby("city_name")
        .agg(
            hours=("datetime", "size"),
            first=("datetime", "min"),
            last=("datetime", "max"),
            mean_pm2_5_own_period=("pm2_5", "mean"),
            mean_aqi_own_period=("aqi", "mean"),
        )
        .round({"hours": 0, "mean_pm2_5_own_period": 2, "mean_aqi_own_period": 2})
        .reset_index()
        .to_csv(PROCESSED / "city_air_own_period.csv", index=False)
    )
    return city


def build_site_index(city_air: pd.DataFrame) -> None:
    log("Loading facility geo-database...")
    fac = siteindex.load_facilities()
    log(f"  {len(fac):,} geocoded facilities; "
        f"{int(fac['workers'].notna().sum()):,} with a worker count")
    fac.to_csv(PROCESSED / "facilities_clean.csv", index=False)

    sites = pd.read_csv(REFERENCE / "sites.csv")
    cities = siteindex.load_cities()

    log("Computing the Composite Site HSE Risk Index...")
    idx = siteindex.compute_index(sites, fac, city_air, cities, radius_km=10.0)
    idx.to_csv(PROCESSED / "site_risk_index.csv", index=False)
    log(f"  top site: {idx.iloc[0]['site_name']} (CSHRI {idx.iloc[0]['cshri']})")

    log("Running weight sensitivity analysis...")
    siteindex.sensitivity_analysis(sites, fac, city_air, cities).to_csv(
        PROCESSED / "site_index_weight_sensitivity.csv", index=False
    )
    log("Running radius sensitivity analysis...")
    siteindex.radius_sensitivity(sites, fac, city_air, cities).to_csv(
        PROCESSED / "site_index_radius_sensitivity.csv", index=False
    )

    for sid in ("S01", "S02"):
        s = sites[sites["site_id"] == sid].iloc[0]
        siteindex.neighbour_profile(s["lat"], s["lon"], fac, radius_km=10.0).to_csv(
            PROCESSED / f"neighbours_{sid}.csv", index=False
        )
    log("  wrote neighbour profiles for the two NZDP factory sites")


def build_risk_and_compliance() -> None:
    log("Scoring the HIRA register...")
    reg = RiskRegister.from_csv()
    reg.df.to_csv(PROCESSED / "hira_scored.csv", index=False)
    reg.summary().reset_index(names="band").to_csv(PROCESSED / "hira_band_summary.csv", index=False)
    reg.state_comparison().reset_index(names="band").to_csv(
        PROCESSED / "hira_state_comparison.csv", index=False
    )
    reg.roadmap().to_csv(PROCESSED / "hira_roadmap.csv", index=False)
    reg.ppe_reliance().to_csv(PROCESSED / "hira_ppe_reliance.csv", index=False)
    reg.by_area().reset_index().to_csv(PROCESSED / "hira_by_area.csv", index=False)
    reg.by_category().reset_index().to_csv(PROCESSED / "hira_by_category.csv", index=False)
    reg.legal_coverage().reset_index().to_csv(PROCESSED / "hira_legal_coverage.csv", index=False)
    matrix_reference().to_csv(PROCESSED / "risk_matrix_reference.csv", index=False)
    lik, sev = scale_definitions()
    lik.to_csv(PROCESSED / "likelihood_scale.csv", index=False)
    sev.to_csv(PROCESSED / "severity_scale.csv", index=False)
    log(f"  {len(reg.df)} hazards scored; "
        f"{len(reg.open_high_risks())} sit at High or Critical today; "
        f"{len(reg.intolerable())} would remain so once the full control plan is in place")

    log("Loading the compliance matrix...")
    cm = ComplianceMatrix.from_csv()
    cm.legal_register().reset_index().to_csv(PROCESSED / "legal_register.csv", index=False)
    cm.audit_plan().to_csv(PROCESSED / "audit_plan.csv", index=False)
    log(f"  {len(cm.df)} requirements mapped across "
        f"{cm.df['iso_clause_group'].nunique()} ISO 45001 clause groups")


def main() -> None:
    log(f"SafeFactory BD — building processed datasets into {PROCESSED}")
    if not (RAW / "bd_air_quality_hourly.csv.gz").exists():
        raise SystemExit(
            "Missing data/raw/bd_air_quality_hourly.csv.gz. "
            "See README section 'Getting the data'."
        )
    city_air = build_air_quality()
    build_site_index(city_air)
    build_risk_and_compliance()
    outputs = sorted(p.name for p in PROCESSED.glob("*.csv"))
    log(f"Done. {len(outputs)} processed tables written:")
    for o in outputs:
        print(f"    {o}")


if __name__ == "__main__":
    main()
