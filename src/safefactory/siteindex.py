"""Composite Site HSE Risk Index (CSHRI).

A site-selection and site-assurance score for industrial locations in
Bangladesh, built only from open data that can be refreshed.

The index answers a question a factory HSE function is regularly asked and
usually has to answer by opinion: *is this location a higher- or lower-risk
place to operate, and why?* It is a screening tool. It ranks locations
relative to each other; it is not an absolute measure of harm, and it never
replaces a site survey.

Four components, each normalised 0-100 across the candidate set and then
weighted:

======================  ======  ================================================
Component               Weight  Rationale
======================  ======  ================================================
Ambient air burden       0.30   Chronic exposure of outdoor and yard workers,
                                and the pollutant load drawn into every air
                                intake on site. Measured, not assumed.
Industrial density       0.25   Neighbouring-plant hazard. A fire, a chemical
                                release or an explosion next door becomes your
                                emergency. Also proxies road congestion on the
                                approach route.
Worker concentration     0.25   Population at risk within the same response
                                envelope. Determines how quickly the district's
                                emergency capacity is saturated by a single
                                large event.
Emergency access         0.20   Distance from the nearest significant urban
                                centre, used as a proxy for fire-service and
                                trauma-care response time.
======================  ======  ================================================

Every weight is declared in ``config.SITE_INDEX_WEIGHTS`` and is meant to be
argued with. ``sensitivity_analysis`` exists precisely so the ranking can be
tested against a different set of weights before anyone acts on it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RAW, REFERENCE, SITE_INDEX_WEIGHTS

EARTH_RADIUS_KM = 6371.0

INDEX_BANDS = [
    (0, 25, "Low", "Standard controls adequate; verify at site survey."),
    (25, 50, "Moderate", "Standard controls plus targeted mitigation of the dominant component."),
    (50, 75, "Elevated", "Enhanced emergency planning and mutual-aid arrangements required."),
    (75, 101, "High", "Site-specific justification, quantified risk assessment and community liaison required."),
]


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres. Vectorised over numpy arrays."""
    lat1, lon1, lat2, lon2 = (
        np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2)
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
def load_facilities(path=None) -> pd.DataFrame:
    """Load the industrial facility geo-database and normalise worker counts."""
    path = path or (RAW / "osh_facilities_bd.csv")
    df = pd.read_csv(path, low_memory=False)
    keep = {
        "os_id": "facility_id",
        "name": "name",
        "address": "address",
        "lat": "lat",
        "lng": "lon",
        "sector": "sector",
        "number_of_workers": "workers_raw",
        "parent_company": "parent_company",
    }
    df = df[[c for c in keep if c in df.columns]].rename(columns=keep)
    for c in ("lat", "lon"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    # Keep only coordinates that actually fall inside Bangladesh's bounding box;
    # open registries carry a small number of transposed or null-island rows.
    df = df[df["lat"].between(20.5, 26.7) & df["lon"].between(88.0, 92.7)]
    df["workers"] = df["workers_raw"].map(_parse_workers) if "workers_raw" in df else np.nan
    return df.reset_index(drop=True)


def _parse_workers(value) -> float:
    """Parse the messy worker-count field.

    Open facility registries report headcount as a number, a range
    ('1001-5000'), or free text. Ranges are reduced to their midpoint and the
    result is flagged as an estimate wherever it is used.
    """
    if pd.isna(value):
        return np.nan
    s = str(value).replace(",", "").strip()
    if not s:
        return np.nan
    nums = pd.Series(s.replace("-", " ").replace("to", " ").split())
    nums = pd.to_numeric(nums, errors="coerce").dropna()
    if nums.empty:
        return np.nan
    return float(nums.mean())


def load_city_air_summary(path=None) -> pd.DataFrame:
    """Per-city ambient burden, produced by ``scripts/build_dataset.py``."""
    from .config import PROCESSED

    path = path or (PROCESSED / "city_air_summary.csv")
    return pd.read_csv(path)


def load_cities(path=None) -> pd.DataFrame:
    path = path or (REFERENCE / "bd_cities.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    return df.rename(columns={"name": "city_name", "latitude": "lat", "longitude": "lon"})


# --------------------------------------------------------------------------
# Component computation
# --------------------------------------------------------------------------
def industrial_context(sites: pd.DataFrame, facilities: pd.DataFrame,
                       radius_km: float = 10.0) -> pd.DataFrame:
    """Count facilities and workers within ``radius_km`` of each site."""
    out = []
    fac_lat = facilities["lat"].to_numpy()
    fac_lon = facilities["lon"].to_numpy()
    fac_workers = facilities["workers"].to_numpy()
    for _, s in sites.iterrows():
        d = haversine_km(s["lat"], s["lon"], fac_lat, fac_lon)
        within = d <= radius_km
        w = fac_workers[within]
        out.append(
            {
                "site_id": s["site_id"],
                "facilities_within_r": int(within.sum()),
                "workers_within_r": float(np.nansum(w)),
                "facilities_with_worker_data": int(np.isfinite(w).sum()),
                "nearest_facility_km": float(np.nanmin(d)) if len(d) else np.nan,
            }
        )
    return pd.DataFrame(out)


def air_context(sites: pd.DataFrame, city_air: pd.DataFrame) -> pd.DataFrame:
    """Attach the ambient burden of the nearest monitored city to each site.

    The distance to that city is returned alongside the value. A site 90 km
    from its nearest monitor is not characterised by that monitor, and the
    dashboard says so rather than hiding it.
    """
    out = []
    c_lat = city_air["lat"].to_numpy()
    c_lon = city_air["lon"].to_numpy()
    for _, s in sites.iterrows():
        d = haversine_km(s["lat"], s["lon"], c_lat, c_lon)
        i = int(np.argmin(d))
        row = city_air.iloc[i]
        out.append(
            {
                "site_id": s["site_id"],
                "nearest_monitor_city": row["city_name"],
                "monitor_distance_km": round(float(d[i]), 1),
                "mean_pm2_5": float(row["mean_pm2_5"]),
                "mean_aqi": float(row["mean_aqi"]),
                "pct_days_over_who_pm25": float(row.get("pct_days_over_who_pm25", np.nan)),
                "monitor_representative": bool(d[i] <= 30),
            }
        )
    return pd.DataFrame(out)


def access_context(sites: pd.DataFrame, cities: pd.DataFrame) -> pd.DataFrame:
    """Distance to the nearest significant urban centre.

    Used as a transparent proxy for emergency-service response. It is a proxy:
    it does not know where fire stations actually are, and the report says so.
    Replace it with the FSCD station list when that becomes available.
    """
    out = []
    c_lat = cities["lat"].to_numpy()
    c_lon = cities["lon"].to_numpy()
    for _, s in sites.iterrows():
        d = haversine_km(s["lat"], s["lon"], c_lat, c_lon)
        i = int(np.argmin(d))
        out.append(
            {
                "site_id": s["site_id"],
                "nearest_urban_centre": cities.iloc[i]["city_name"],
                "urban_centre_km": round(float(d[i]), 1),
            }
        )
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# Normalisation and scoring
# --------------------------------------------------------------------------
def _minmax(series: pd.Series, invert: bool = False) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    lo, hi = s.min(), s.max()
    if not np.isfinite(lo) or not np.isfinite(hi) or hi == lo:
        return pd.Series(np.full(len(s), 50.0), index=s.index)
    scaled = (s - lo) / (hi - lo) * 100
    return (100 - scaled) if invert else scaled


def index_band(value: float) -> str:
    for lo, hi, name, _ in INDEX_BANDS:
        if lo <= value < hi:
            return name
    return "High"


def band_guidance(band: str) -> str:
    return next(g for _lo, _hi, name, g in INDEX_BANDS if name == band)


def compute_index(sites: pd.DataFrame, facilities: pd.DataFrame,
                  city_air: pd.DataFrame, cities: pd.DataFrame,
                  radius_km: float = 10.0,
                  weights: dict | None = None) -> pd.DataFrame:
    """Compute the Composite Site HSE Risk Index for a set of sites.

    ``sites`` must have ``site_id``, ``site_name``, ``lat``, ``lon``.
    Returns one row per site with each raw component, each normalised
    sub-score, the weighted index and its band.
    """
    required = {"site_id", "site_name", "lat", "lon"}
    missing = required - set(sites.columns)
    if missing:
        raise ValueError(f"sites is missing columns: {sorted(missing)}")
    weights = weights or SITE_INDEX_WEIGHTS
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError(f"weights must sum to 1.0, got {sum(weights.values())}")

    df = sites.copy()
    df = df.merge(industrial_context(sites, facilities, radius_km), on="site_id")
    df = df.merge(air_context(sites, city_air), on="site_id")
    df = df.merge(access_context(sites, cities), on="site_id")

    # Normalised sub-scores, all oriented so that higher means more risk.
    df["score_ambient_air"] = _minmax(df["mean_pm2_5"]).round(1)
    df["score_industrial_density"] = _minmax(df["facilities_within_r"]).round(1)
    df["score_worker_concentration"] = _minmax(df["workers_within_r"]).round(1)
    # Further from an urban centre implies a slower emergency response, so the
    # distance is NOT inverted: greater distance means a higher risk score.
    df["score_emergency_access"] = _minmax(df["urban_centre_km"]).round(1)

    df["cshri"] = (
        df["score_ambient_air"] * weights["ambient_air"]
        + df["score_industrial_density"] * weights["industrial_density"]
        + df["score_worker_concentration"] * weights["worker_concentration"]
        + df["score_emergency_access"] * weights["emergency_access"]
    ).round(1)
    df["band"] = df["cshri"].map(index_band)
    df["guidance"] = df["band"].map(band_guidance)
    df["dominant_component"] = df[
        [
            "score_ambient_air",
            "score_industrial_density",
            "score_worker_concentration",
            "score_emergency_access",
        ]
    ].idxmax(axis=1).str.replace("score_", "", regex=False)
    return df.sort_values("cshri", ascending=False).reset_index(drop=True)


def sensitivity_analysis(sites: pd.DataFrame, facilities: pd.DataFrame,
                         city_air: pd.DataFrame, cities: pd.DataFrame,
                         radius_km: float = 10.0) -> pd.DataFrame:
    """Re-rank the sites under alternative weightings.

    A composite index whose ranking flips as soon as the weights move is not
    telling you much. This produces the evidence either way, including an
    equal-weight case and one case per component dominating.
    """
    schemes = {
        "baseline": SITE_INDEX_WEIGHTS,
        "equal": {k: 0.25 for k in SITE_INDEX_WEIGHTS},
        "air_dominant": {
            "ambient_air": 0.55,
            "industrial_density": 0.15,
            "worker_concentration": 0.15,
            "emergency_access": 0.15,
        },
        "density_dominant": {
            "ambient_air": 0.15,
            "industrial_density": 0.55,
            "worker_concentration": 0.15,
            "emergency_access": 0.15,
        },
        "access_dominant": {
            "ambient_air": 0.15,
            "industrial_density": 0.15,
            "worker_concentration": 0.15,
            "emergency_access": 0.55,
        },
    }
    frames = []
    for name, w in schemes.items():
        r = compute_index(sites, facilities, city_air, cities, radius_km, w)
        r["scheme"] = name
        r["rank"] = r["cshri"].rank(ascending=False, method="min").astype(int)
        frames.append(r[["site_id", "site_name", "scheme", "cshri", "rank"]])
    long = pd.concat(frames)
    wide = long.pivot_table(index=["site_id", "site_name"], columns="scheme", values="rank")
    wide["rank_range"] = wide.max(axis=1) - wide.min(axis=1)
    wide["stable"] = wide["rank_range"] <= 1
    return wide.reset_index()


def radius_sensitivity(sites: pd.DataFrame, facilities: pd.DataFrame,
                       city_air: pd.DataFrame, cities: pd.DataFrame,
                       radii=(5, 10, 15, 25)) -> pd.DataFrame:
    """How the index moves as the neighbourhood radius changes."""
    frames = []
    for r in radii:
        d = compute_index(sites, facilities, city_air, cities, radius_km=r)
        d["radius_km"] = r
        frames.append(d[["site_id", "site_name", "radius_km", "facilities_within_r",
                         "workers_within_r", "cshri", "band"]])
    return pd.concat(frames).sort_values(["site_id", "radius_km"]).reset_index(drop=True)


def neighbour_profile(site_lat: float, site_lon: float, facilities: pd.DataFrame,
                      radius_km: float = 10.0, top: int = 25) -> pd.DataFrame:
    """The named neighbouring plants inside the response envelope.

    This is the table that turns the density score into an action: it is the
    list of sites a mutual-aid agreement and a joint evacuation plan should
    cover.
    """
    d = facilities.copy()
    d["distance_km"] = haversine_km(site_lat, site_lon, d["lat"].to_numpy(), d["lon"].to_numpy())
    d = d[d["distance_km"] <= radius_km]
    cols = [c for c in ["name", "address", "sector", "workers", "distance_km"] if c in d.columns]
    return d.sort_values("distance_km")[cols].head(top).round({"distance_km": 2})
