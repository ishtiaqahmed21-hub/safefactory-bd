"""Central configuration: paths, constants and reference values.

Every threshold used anywhere in the package is declared here so that a reviewer
can see, in one file, exactly which numbers the system runs on and where each
one comes from.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
REFERENCE = DATA / "reference"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

for _p in (RAW, REFERENCE, PROCESSED, REPORTS, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Risk matrix (5 x 5)
# --------------------------------------------------------------------------
LIKELIHOOD_SCALE = {
    1: ("Rare", "Not expected to occur in the life of the plant (<1 in 25 years)"),
    2: ("Unlikely", "Could occur at some time (once in 10-25 years)"),
    3: ("Possible", "Might occur at some time (once in 2-10 years)"),
    4: ("Likely", "Will probably occur in most circumstances (once a year)"),
    5: ("Almost certain", "Expected to occur in most circumstances (several times a year)"),
}

SEVERITY_SCALE = {
    1: ("Negligible", "No treatment or first aid only; no lost time; no environmental effect"),
    2: ("Minor", "Medical treatment case; up to 3 days lost; contained on-site release"),
    3: ("Moderate", "Lost-time injury; reversible health effect; reportable release"),
    4: ("Major", "Permanent disability or single serious injury; major release; regulatory action"),
    5: ("Catastrophic", "Single or multiple fatality; irreversible health effect; licence at risk"),
}

# Risk bands on the product L x S (range 1-25)
RISK_BANDS = [
    (1, 4, "Low", "Acceptable. Monitor and maintain existing controls.", 12),
    (5, 9, "Medium", "Tolerable if ALARP. Documented action plan required.", 6),
    (10, 15, "High", "Not acceptable as-is. Additional controls within 30 days.", 3),
    (16, 25, "Critical", "Unacceptable. Stop or restrict the activity until controls are in place.", 1),
]

# Escalation rule: a credible fatality scenario is never allowed to sit below
# 'High' on the basis of a low likelihood score alone.
FATALITY_ESCALATION_SEVERITY = 5
FATALITY_ESCALATION_MIN_LIKELIHOOD = 3

# Hierarchy of controls, most effective first (ISO 45001:2018 clause 8.1.2).
# The weight is used to score how much a control plan relies on genuinely
# effective controls rather than on PPE and procedure alone.
CONTROL_HIERARCHY = {
    "Elimination": 5,
    "Substitution": 4,
    "Engineering": 3,
    "Administrative": 2,
    "PPE": 1,
}

# --------------------------------------------------------------------------
# Injury performance metrics
# --------------------------------------------------------------------------
# LTIFR and severity rate are expressed per 1,000,000 hours worked (ILO
# convention). TRIR and DART are expressed per 200,000 hours (the OSHA
# convention: 100 full-time equivalent workers at 2,000 hours per year).
LTIFR_BASE = 1_000_000
SEVERITY_RATE_BASE = 1_000_000
TRIR_BASE = 200_000
DART_BASE = 200_000

# Incident classification hierarchy, least to most severe.
INCIDENT_CLASSES = [
    "Near Miss",
    "First Aid Case",
    "Medical Treatment Case",
    "Restricted Work Case",
    "Lost Time Injury",
    "Permanent Disability",
    "Fatality",
]

# Classes that count as OSHA-style recordable cases for TRIR.
RECORDABLE_CLASSES = {
    "Medical Treatment Case",
    "Restricted Work Case",
    "Lost Time Injury",
    "Permanent Disability",
    "Fatality",
}

# Classes that count as DART (days away, restricted or transferred).
DART_CLASSES = {
    "Restricted Work Case",
    "Lost Time Injury",
    "Permanent Disability",
    "Fatality",
}

# Standard charge in lost days used when a fatality or permanent total
# disability occurs, per the long-standing ANSI Z16.1 convention. Declared
# explicitly because severity rate is meaningless without stating it.
FATALITY_DAY_CHARGE = 6000

# --------------------------------------------------------------------------
# Permit to Work
# --------------------------------------------------------------------------
PERMIT_TYPES = {
    "Hot Work": {
        "max_validity_hours": 12,
        "gas_test_required": True,
        "fire_watch_minutes_after": 60,
        "standby_required": True,
    },
    "Confined Space Entry": {
        "max_validity_hours": 8,
        "gas_test_required": True,
        "fire_watch_minutes_after": 0,
        "standby_required": True,
    },
    "Work at Height": {
        "max_validity_hours": 12,
        "gas_test_required": False,
        "fire_watch_minutes_after": 0,
        "standby_required": True,
    },
    "Electrical Work": {
        "max_validity_hours": 12,
        "gas_test_required": False,
        "fire_watch_minutes_after": 0,
        "standby_required": True,
    },
    "Line Breaking": {
        "max_validity_hours": 8,
        "gas_test_required": True,
        "fire_watch_minutes_after": 0,
        "standby_required": True,
    },
    "Excavation": {
        "max_validity_hours": 24,
        "gas_test_required": True,
        "fire_watch_minutes_after": 0,
        "standby_required": False,
    },
    "General Maintenance": {
        "max_validity_hours": 24,
        "gas_test_required": False,
        "fire_watch_minutes_after": 0,
        "standby_required": False,
    },
}

# Atmospheric acceptance criteria for entry and hot work.
GAS_TEST_LIMITS = {
    "oxygen_pct": (19.5, 23.5),      # acceptable range
    "lel_pct": (0.0, 10.0),          # % of lower explosive limit
    "co_ppm": (0.0, 25.0),           # NIOSH REL TWA
    "h2s_ppm": (0.0, 10.0),
    "nh3_ppm": (0.0, 25.0),          # NIOSH REL TWA for ammonia
}

# --------------------------------------------------------------------------
# Exposure reference values (ambient and occupational)
# --------------------------------------------------------------------------
# WHO Global Air Quality Guidelines 2021.
WHO_PM25_ANNUAL = 5.0        # ug/m3
WHO_PM25_DAILY = 15.0        # ug/m3
WHO_PM10_ANNUAL = 15.0       # ug/m3
WHO_PM10_DAILY = 45.0        # ug/m3

# Bangladesh National Ambient Air Quality Standard (Schedule 2, ECR 1997 as
# amended 2005) for PM2.5 and PM10.
BD_NAAQS_PM25_ANNUAL = 15.0  # ug/m3
BD_NAAQS_PM25_DAILY = 65.0   # ug/m3
BD_NAAQS_PM10_ANNUAL = 50.0  # ug/m3
BD_NAAQS_PM10_DAILY = 150.0  # ug/m3

# US EPA AQI category breakpoints, used because the source dataset reports AQI
# on the US EPA scale.
AQI_CATEGORIES = [
    (0, 50, "Good"),
    (51, 100, "Moderate"),
    (101, 150, "Unhealthy for Sensitive Groups"),
    (151, 200, "Unhealthy"),
    (201, 300, "Very Unhealthy"),
    (301, 500, "Hazardous"),
]

# Occupational exposure limits used in the HIRA (source noted in the report).
OEL = {
    "ammonia_osha_pel_twa_ppm": 50,
    "ammonia_niosh_rel_twa_ppm": 25,
    "ammonia_niosh_stel_ppm": 35,
    "ammonia_idlh_ppm": 300,
    "ammonia_lel_vol_pct": 15,
    "noise_action_level_dba": 85,
    "oxygen_min_pct": 19.5,
}

# --------------------------------------------------------------------------
# Site Risk Index weights (see reports/ for the justification of each weight)
# --------------------------------------------------------------------------
SITE_INDEX_WEIGHTS = {
    "ambient_air": 0.30,
    "industrial_density": 0.25,
    "worker_concentration": 0.25,
    "emergency_access": 0.20,
}
