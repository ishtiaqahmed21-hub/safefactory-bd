"""Unit tests.

Every rate test is checked against a value worked out by hand in the docstring,
so a reviewer can confirm the arithmetic without trusting the code.

Run with:  python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from safefactory import compliance, exposure, incidents, ptw, quality, risk, siteindex


# ==========================================================================
# Risk engine
# ==========================================================================
class TestRiskScoring:
    def test_score_is_the_product(self):
        assert risk.risk_score(4, 5) == 20
        assert risk.risk_score(1, 1) == 1
        assert risk.risk_score(3, 3) == 9

    def test_bands_at_the_boundaries(self):
        assert risk.risk_band(1, 4) == "Low"        # 4  -> top of Low
        assert risk.risk_band(1, 5) == "Medium"     # 5  -> bottom of Medium...
        assert risk.risk_band(3, 3) == "Medium"     # 9  -> top of Medium
        assert risk.risk_band(2, 5) == "High"       # 10 -> bottom of High
        assert risk.risk_band(3, 5) == "High"       # 15 -> top of High
        assert risk.risk_band(4, 4) == "Critical"   # 16 -> bottom of Critical
        assert risk.risk_band(5, 5) == "Critical"   # 25 -> top of scale

    def test_fatality_escalation_floor_and_ceiling(self):
        """The escalation rule lifts a credible fatality scenario to at least
        High. At L=3, S=5 the product is already 15 (High), so the rule is not
        what puts it there. At L=1, S=5 the product is 5 (Medium) and the rule
        does NOT fire, because likelihood is below the escalation floor of 3 —
        a fatality judged genuinely rare is allowed to sit in Medium."""
        assert risk.risk_band(3, 5) == "High"
        assert risk.risk_band(1, 5) == "Medium"
        assert risk.risk_band(2, 5) == "High"

    def test_invalid_inputs_are_rejected(self):
        with pytest.raises(ValueError):
            risk.risk_score(0, 3)
        with pytest.raises(ValueError):
            risk.risk_score(3, 6)

    def test_control_effectiveness_scale(self):
        assert risk.control_effectiveness("Elimination") == 1.0
        assert risk.control_effectiveness("PPE") == 0.2
        # Engineering (3) + Administrative (2) -> mean 2.5 / 5 = 0.5
        assert risk.control_effectiveness("Engineering + Administrative") == 0.5
        assert risk.control_effectiveness("") == 0.0
        assert risk.control_effectiveness(None) == 0.0

    def test_matrix_reference_covers_all_25_cells(self):
        m = risk.matrix_reference()
        assert len(m) == 25
        assert set(m["band"]) <= {"Low", "Medium", "High", "Critical"}


class TestRiskRegister:
    @pytest.fixture
    def reg(self):
        return risk.RiskRegister.from_csv()

    def test_seed_register_loads_and_scores(self, reg):
        assert len(reg.df) >= 30
        assert reg.df["risk_score_initial"].between(1, 25).all()
        assert reg.df["risk_score_residual"].between(1, 25).all()

    def test_controls_never_increase_risk(self, reg):
        assert (reg.df["risk_score_residual"] <= reg.df["risk_score_initial"]).all()

    def test_current_risk_sits_between_inherent_and_target(self, reg):
        d = reg.df
        assert (d["risk_score_current"] <= d["risk_score_initial"]).all()
        assert (d["risk_score_current"] >= d["risk_score_residual"]).all()

    def test_proposed_controls_get_no_credit(self, reg):
        d = reg.df[reg.df["control_status"] == "Proposed"]
        assert (d["risk_score_current"] == d["risk_score_initial"]).all()

    def test_implemented_controls_get_full_credit(self, reg):
        d = reg.df[reg.df["control_status"] == "Implemented"]
        assert (d["risk_score_current"] == d["risk_score_residual"]).all()

    def test_missing_column_is_rejected(self):
        with pytest.raises(ValueError):
            risk.RiskRegister(pd.DataFrame({"hazard_id": ["X"]}))

    def test_every_hazard_cites_a_legal_reference(self, reg):
        assert reg.df["legal_reference"].notna().all()
        assert (reg.df["legal_reference"].str.len() > 5).all()

    def test_roadmap_is_ordered_by_unbought_reduction(self, reg):
        r = reg.roadmap()
        assert (r["gap_to_target"].diff().dropna() <= 0).all()


# ==========================================================================
# Incident metrics — every expected value is worked by hand
# ==========================================================================
class TestInjuryRates:
    def test_ltifr(self):
        """3 LTIs in 500,000 hours -> 3 x 1,000,000 / 500,000 = 6.00"""
        assert incidents.ltifr(3, 500_000) == 6.00

    def test_trir(self):
        """5 recordables in 500,000 hours -> 5 x 200,000 / 500,000 = 2.00"""
        assert incidents.trir(5, 500_000) == 2.00

    def test_dart(self):
        """2 DART cases in 400,000 hours -> 2 x 200,000 / 400,000 = 1.00"""
        assert incidents.dart_rate(2, 400_000) == 1.00

    def test_severity_rate(self):
        """120 days lost in 600,000 hours -> 120 x 1,000,000 / 600,000 = 200.0"""
        assert incidents.severity_rate(120, 600_000) == 200.0

    def test_incidence_rate(self):
        """8 cases among 400 workers -> 8 x 1000 / 400 = 20.00"""
        assert incidents.incidence_rate(8, 400) == 20.00

    def test_average_days_lost(self):
        assert incidents.average_days_lost(45, 3) == 15.0
        assert incidents.average_days_lost(45, 0) == 0.0

    def test_zero_hours_is_rejected(self):
        with pytest.raises(ValueError):
            incidents.ltifr(1, 0)
        with pytest.raises(ValueError):
            incidents.trir(1, -100)

    def test_exposure_hours(self):
        """250 workers x 8 h x 300 days = 600,000 hours"""
        assert incidents.exposure_hours(250, 8, 300) == 600_000

    def test_the_two_bases_are_not_interchangeable(self):
        """The same event count on the same hours must give different numbers
        under the ILO and OSHA bases; a system that returns the same value for
        both has silently mixed them."""
        assert incidents.ltifr(4, 1_000_000) != incidents.trir(4, 1_000_000)


class TestIncidentRegister:
    @pytest.fixture
    def sample(self):
        return pd.DataFrame(
            {
                "incident_id": [f"I{i:03d}" for i in range(1, 9)],
                "date": pd.date_range("2025-01-05", periods=8, freq="45D"),
                "area": ["Frying"] * 4 + ["Warehouse"] * 4,
                "classification": [
                    "Near Miss", "Near Miss", "First Aid Case", "Medical Treatment Case",
                    "Lost Time Injury", "Lost Time Injury", "Restricted Work Case", "Near Miss",
                ],
                "days_lost": [0, 0, 0, 0, 12, 8, 0, 0],
                "immediate_cause": ["Slip"] * 3 + ["Contact with hot surface"] * 2
                + ["Struck by"] * 3,
            }
        )

    def test_classification_counts(self, sample):
        r = incidents.IncidentRegister(sample)
        k = r.kpis(hours_worked=500_000)
        assert k["near_misses"] == 3
        assert k["lost_time_injuries"] == 2
        # Medical Treatment + Lost Time x2 + Restricted Work = 4 recordables
        assert k["recordable_cases"] == 4
        # Restricted Work + 2 Lost Time = 3 DART cases
        assert k["dart_cases"] == 3

    def test_kpis_match_hand_calculation(self, sample):
        r = incidents.IncidentRegister(sample)
        k = r.kpis(hours_worked=500_000)
        assert k["LTIFR_per_1M_hours"] == 4.00     # 2 x 1e6 / 5e5
        assert k["TRIR_per_200k_hours"] == 1.60    # 4 x 2e5 / 5e5
        assert k["DART_per_200k_hours"] == 1.20    # 3 x 2e5 / 5e5
        assert k["severity_rate_per_1M_hours"] == 40.0   # 20 x 1e6 / 5e5
        assert k["average_days_lost_per_LTI"] == 10.0    # 20 / 2

    def test_fatality_gets_the_standard_day_charge(self):
        d = pd.DataFrame(
            {
                "incident_id": ["I1"],
                "date": ["2025-06-01"],
                "area": ["Boiler House"],
                "classification": ["Fatality"],
                "days_lost": [0],
            }
        )
        r = incidents.IncidentRegister(d)
        assert r.df["days_lost"].iloc[0] == 6000

    def test_unknown_classification_is_rejected(self):
        d = pd.DataFrame(
            {
                "incident_id": ["I1"],
                "date": ["2025-06-01"],
                "area": ["X"],
                "classification": ["Slightly Hurt"],
                "days_lost": [0],
            }
        )
        with pytest.raises(ValueError):
            incidents.IncidentRegister(d)

    def test_pareto_cumulative_reaches_100_when_all_shown(self, sample):
        r = incidents.IncidentRegister(sample)
        p = r.pareto(top=99)
        assert p["cumulative_pct"].iloc[-1] == pytest.approx(100.0, abs=0.2)


class TestInvestigation:
    def test_five_why_flags_a_blame_ending(self):
        d = incidents.five_why(
            "Operator burned by hot oil",
            ["Oil was still hot", "Cool-down was skipped", "Line was behind schedule",
             "No cool-down interlock", "Operator was careless"],
        )
        assert d.attrs["terminates_in_blame"] is True

    def test_five_why_accepts_a_systemic_ending(self):
        d = incidents.five_why(
            "Operator burned by hot oil",
            ["Oil was still hot", "Cool-down was skipped", "Schedule pressure",
             "No interlock prevents early draining",
             "Management of change did not require an interlock at commissioning"],
        )
        assert d.attrs["terminates_in_blame"] is False
        assert d.attrs["adequate_depth"] is True

    def test_bowtie_reports_unbarriered_lines(self):
        b = incidents.bowtie(
            hazard="Anhydrous ammonia inventory",
            top_event="Loss of containment",
            threats=["Seal failure", "Corrosion", "Overpressure"],
            consequences=["Toxic exposure", "Flammable atmosphere"],
            preventive={"Seal failure": ["Planned seal replacement"], "Corrosion": []},
            mitigative={"Toxic exposure": ["Gas detection", "SCBA"], "Flammable atmosphere": []},
        )
        gaps = {(g["side"], g["line"]) for g in b["gaps"]}
        assert ("preventive", "Corrosion") in gaps
        assert ("preventive", "Overpressure") in gaps
        assert ("mitigative", "Flammable atmosphere") in gaps


# ==========================================================================
# Permit to Work
# ==========================================================================
class TestGasTest:
    def test_acceptable_atmosphere_passes(self):
        v = ptw.evaluate_gas_test({"oxygen_pct": 20.9, "lel_pct": 0, "co_ppm": 2})
        assert v["pass"] is True

    def test_low_oxygen_fails_and_names_the_parameter(self):
        v = ptw.evaluate_gas_test({"oxygen_pct": 18.0, "lel_pct": 0})
        assert v["pass"] is False
        assert "oxygen_pct" in v["reason"]

    def test_enriched_oxygen_also_fails(self):
        """Above 23.5% is a fire hazard, not a safe atmosphere."""
        assert ptw.evaluate_gas_test({"oxygen_pct": 24.5})["pass"] is False

    def test_ammonia_above_the_rel_fails(self):
        assert ptw.evaluate_gas_test({"oxygen_pct": 20.9, "nh3_ppm": 40})["pass"] is False

    def test_no_readings_is_a_failure_not_a_pass(self):
        assert ptw.evaluate_gas_test({})["pass"] is False


class TestPermits:
    def _base(self, **kw):
        start = datetime(2026, 3, 1, 8, 0)
        args = dict(
            permit_id="PTW-001",
            permit_type="Hot Work",
            area="Warehouse",
            description="Weld a rack upright",
            issued_by="A. Rahman",
            accepted_by="K. Islam",
            start=start,
            end=start + timedelta(hours=6),
            gas_test={"oxygen_pct": 20.9, "lel_pct": 0},
            standby_person="M. Hasan",
        )
        args.update(kw)
        return ptw.Permit(**args)

    def test_a_complete_hot_work_permit_is_valid(self):
        assert self._base().validate(now=datetime(2026, 3, 1, 10, 0))["valid"] is True

    def test_over_length_permit_is_rejected(self):
        p = self._base(end=datetime(2026, 3, 2, 8, 0))  # 24 h vs 12 h limit
        v = p.validate(now=datetime(2026, 3, 1, 10, 0))
        assert v["valid"] is False
        assert any("exceeds" in i for i in v["issues"])

    def test_missing_gas_test_is_rejected(self):
        v = self._base(gas_test=None).validate(now=datetime(2026, 3, 1, 10, 0))
        assert any("gas test required" in i for i in v["issues"])

    def test_missing_standby_is_rejected(self):
        v = self._base(standby_person=None).validate(now=datetime(2026, 3, 1, 10, 0))
        assert any("standby" in i for i in v["issues"])

    def test_self_issued_permit_is_rejected(self):
        v = self._base(issued_by="A. Rahman", accepted_by="A. Rahman").validate(
            now=datetime(2026, 3, 1, 10, 0)
        )
        assert any("same person" in i for i in v["issues"])

    def test_expired_and_unclosed_is_caught(self):
        v = self._base().validate(now=datetime(2026, 3, 3, 8, 0))
        assert v["status"] == "EXPIRED - not closed"
        assert any("expired" in i for i in v["issues"])

    def test_closing_hot_work_without_the_fire_watch_is_caught(self):
        p = self._base(
            closed_at=datetime(2026, 3, 1, 14, 5), fire_watch_completed=False
        )
        v = p.validate(now=datetime(2026, 3, 1, 15, 0))
        assert any("fire watch" in i for i in v["issues"])

    def test_confined_space_without_isolations_is_caught(self):
        start = datetime(2026, 3, 1, 8, 0)
        p = ptw.Permit(
            permit_id="PTW-002",
            permit_type="Confined Space Entry",
            area="Milk Silo 2",
            description="Internal clean",
            issued_by="A",
            accepted_by="B",
            start=start,
            end=start + timedelta(hours=4),
            gas_test={"oxygen_pct": 20.9, "lel_pct": 0, "co_ppm": 1},
            standby_person="C",
            isolations=[],
        )
        v = p.validate(now=start + timedelta(hours=1))
        assert any("isolation" in i for i in v["issues"])

    def test_unknown_permit_type_is_rejected(self):
        with pytest.raises(ValueError):
            self._base(permit_type="Vibes Check")

    def test_end_before_start_is_rejected(self):
        with pytest.raises(ValueError):
            self._base(end=datetime(2026, 2, 28, 8, 0))

    def test_register_audit_counts_correctly(self):
        r = ptw.PermitRegister()
        r.add(self._base(permit_id="P1"))
        r.add(self._base(permit_id="P2", standby_person=None))
        a = r.audit(now=datetime(2026, 3, 1, 10, 0))
        assert a["permits"] == 2
        assert a["compliant"] == 1
        assert a["compliance_rate_pct"] == 50.0

    def test_duplicate_permit_id_is_rejected(self):
        r = ptw.PermitRegister()
        r.add(self._base(permit_id="P1"))
        with pytest.raises(ValueError):
            r.add(self._base(permit_id="P1"))


class TestLOTO:
    def test_a_fully_applied_isolation_is_safe(self):
        proc = ptw.LOTOProcedure(equipment="Blender 1", prepared_by="Eng")
        proc.add(ptw.LOTOPoint("P1", "Blender 1", "Electrical", "MCC breaker",
                               "Rack out and lock", "Prove dead at terminals",
                               True, True, True, "R. Karim"))
        proc.add(ptw.LOTOPoint("P2", "Blender 1", "Gravity", "Hopper slide gate",
                               "Pin and lock", "Visual check", True, True, True, "R. Karim"))
        assert proc.validate()["safe_to_work"] is True

    def test_electrical_only_isolation_is_challenged(self):
        proc = ptw.LOTOProcedure(equipment="Fryer", prepared_by="Eng")
        proc.add(ptw.LOTOPoint("P1", "Fryer", "Electrical", "Breaker", "Lock",
                               "Prove dead", True, True, True, "R. Karim"))
        v = proc.validate()
        assert v["safe_to_work"] is False
        assert any("only electrical" in i for i in v["issues"])

    def test_unverified_zero_energy_blocks_work(self):
        proc = ptw.LOTOProcedure(equipment="Conveyor", prepared_by="Eng")
        proc.add(ptw.LOTOPoint("P1", "Conveyor", "Electrical", "Breaker", "Lock",
                               "Prove dead", True, True, False, "R. Karim"))
        proc.add(ptw.LOTOPoint("P2", "Conveyor", "Pneumatic", "Air isolator",
                               "Lock and bleed", "Gauge at zero", True, True, True, "R. Karim"))
        assert proc.validate()["safe_to_work"] is False

    def test_empty_procedure_is_not_safe(self):
        assert ptw.LOTOProcedure("X", "Eng").validate()["safe_to_work"] is False

    def test_unknown_energy_type_is_rejected(self):
        with pytest.raises(ValueError):
            ptw.LOTOPoint("P1", "X", "Magic", "d", "m", "v")


# ==========================================================================
# Compliance
# ==========================================================================
class TestCompliance:
    @pytest.fixture
    def cm(self):
        return compliance.ComplianceMatrix.from_csv()

    def test_matrix_loads(self, cm):
        assert len(cm.df) >= 30
        assert cm.df["bd_legal_reference"].notna().all()

    def test_untouched_matrix_scores_zero(self, cm):
        assert cm.conformity_index()["conformity_index"] == 0.0

    def test_full_conformity_scores_100(self, cm):
        cm.apply_statuses({r: "Conforms" for r in cm.df["req_id"]})
        assert cm.conformity_index()["conformity_index"] == 100.0

    def test_a_critical_gap_costs_more_than_a_low_one(self, cm):
        crit = cm.df[cm.df["criticality"] == "Critical"]["req_id"].iloc[0]
        med = cm.df[cm.df["criticality"] == "Medium"]["req_id"].iloc[0]

        a = compliance.ComplianceMatrix.from_csv()
        a.apply_statuses({r: "Conforms" for r in a.df["req_id"]})
        a.set_status(crit, "Not Conform")

        b = compliance.ComplianceMatrix.from_csv()
        b.apply_statuses({r: "Conforms" for r in b.df["req_id"]})
        b.set_status(med, "Not Conform")

        assert a.conformity_index()["conformity_index"] < b.conformity_index()["conformity_index"]

    def test_not_applicable_is_excluded_not_scored_zero(self, cm):
        cm.apply_statuses({r: "Conforms" for r in cm.df["req_id"]})
        cm.set_status(cm.df["req_id"].iloc[0], "Not Applicable")
        assert cm.conformity_index()["conformity_index"] == 100.0

    def test_unknown_status_is_rejected(self, cm):
        with pytest.raises(ValueError):
            cm.set_status(cm.df["req_id"].iloc[0], "Probably Fine")

    def test_unknown_req_id_is_rejected(self, cm):
        with pytest.raises(KeyError):
            cm.set_status("CM-999", "Conforms")

    def test_every_requirement_names_its_evidence(self, cm):
        assert cm.df["evidence_required"].notna().all()


# ==========================================================================
# Geometry and the site index
# ==========================================================================
class TestGeometry:
    def test_haversine_against_a_known_distance(self):
        """Dhaka (23.7104, 90.4074) to Chattogram (22.3384, 91.8317) is about
        211 km great-circle. Allow a few km for the choice of city centroid."""
        d = float(siteindex.haversine_km(23.7104, 90.4074, 22.3384, 91.8317))
        assert 205 < d < 216

    def test_zero_distance(self):
        assert float(siteindex.haversine_km(23.7, 90.4, 23.7, 90.4)) == pytest.approx(0.0)

    def test_vectorised_form(self):
        d = siteindex.haversine_km(23.7, 90.4, np.array([23.7, 22.3384]),
                                   np.array([90.4, 91.8317]))
        assert d.shape == (2,)
        assert d[0] == pytest.approx(0.0)

    def test_worker_range_becomes_a_midpoint(self):
        assert siteindex._parse_workers("1001-5000") == 3000.5
        assert siteindex._parse_workers("2,500") == 2500.0
        assert np.isnan(siteindex._parse_workers(None))
        assert np.isnan(siteindex._parse_workers("unknown"))


class TestSiteIndex:
    @pytest.fixture
    def inputs(self):
        fac = pd.DataFrame(
            {
                "facility_id": [f"F{i}" for i in range(6)],
                "name": [f"Plant {i}" for i in range(6)],
                "lat": [23.80, 23.81, 23.79, 22.34, 24.85, 23.80],
                "lon": [90.40, 90.41, 90.39, 91.83, 89.37, 90.40],
                "workers": [1000, 2000, 1500, 800, 300, np.nan],
            }
        )
        air = pd.DataFrame(
            {
                "city_name": ["Dhaka", "Chittagong", "Bogra"],
                "lat": [23.71, 22.34, 24.85],
                "lon": [90.41, 91.83, 89.37],
                "mean_pm2_5": [50.0, 28.0, 52.0],
                "mean_aqi": [115.0, 90.0, 122.0],
                "pct_days_over_who_pm25": [85.0, 60.0, 90.0],
            }
        )
        cities = pd.DataFrame(
            {
                "city_name": ["Dhaka", "Chittagong", "Bogra"],
                "lat": [23.71, 22.34, 24.85],
                "lon": [90.41, 91.83, 89.37],
            }
        )
        sites = pd.DataFrame(
            {
                "site_id": ["A", "B", "C"],
                "site_name": ["Dense urban", "Port", "Regional"],
                "lat": [23.80, 22.34, 24.85],
                "lon": [90.40, 91.83, 89.37],
            }
        )
        return sites, fac, air, cities

    def test_index_is_bounded_and_banded(self, inputs):
        r = siteindex.compute_index(*inputs)
        assert r["cshri"].between(0, 100).all()
        assert set(r["band"]) <= {"Low", "Moderate", "Elevated", "High"}

    def test_dense_site_outranks_sparse_site(self, inputs):
        r = siteindex.compute_index(*inputs).set_index("site_id")
        assert r.loc["A", "facilities_within_r"] > r.loc["C", "facilities_within_r"]

    def test_weights_must_sum_to_one(self, inputs):
        with pytest.raises(ValueError):
            siteindex.compute_index(*inputs, weights={"ambient_air": 0.5,
                                                      "industrial_density": 0.2,
                                                      "worker_concentration": 0.2,
                                                      "emergency_access": 0.2})

    def test_missing_site_columns_are_rejected(self, inputs):
        _sites, fac, air, cities = inputs
        with pytest.raises(ValueError):
            siteindex.compute_index(pd.DataFrame({"site_id": ["A"]}), fac, air, cities)

    def test_radius_is_monotone_in_facility_count(self, inputs):
        sites, fac, air, cities = inputs
        small = siteindex.compute_index(sites, fac, air, cities, radius_km=2)
        big = siteindex.compute_index(sites, fac, air, cities, radius_km=50)
        s = small.set_index("site_id")["facilities_within_r"]
        b = big.set_index("site_id")["facilities_within_r"]
        assert (b >= s).all()

    def test_nan_worker_counts_do_not_break_the_sum(self, inputs):
        r = siteindex.compute_index(*inputs)
        assert r["workers_within_r"].notna().all()

    def test_sensitivity_reports_rank_stability(self, inputs):
        s = siteindex.sensitivity_analysis(*inputs)
        assert "rank_range" in s.columns
        assert "stable" in s.columns


# ==========================================================================
# Data-quality screening — the checks that caught the real defects
# ==========================================================================
class TestQualityScreen:
    def test_identical_series_are_detected(self):
        t = pd.date_range("2024-01-01", periods=600, freq="h")
        vals = np.random.default_rng(0).normal(50, 10, 600)
        df = pd.concat(
            [
                pd.DataFrame({"datetime": t, "city_name": "Alpha", "pm2_5": vals,
                              "lat": 23.7, "lon": 90.4}),
                pd.DataFrame({"datetime": t, "city_name": "Beta", "pm2_5": vals,
                              "lat": 23.72, "lon": 90.42}),
            ]
        )
        d = quality.find_duplicate_series(df)
        assert len(d) == 1
        assert d.iloc[0]["identical_fraction"] == 1.0

    def test_distinct_series_are_not_flagged(self):
        t = pd.date_range("2024-01-01", periods=600, freq="h")
        rng = np.random.default_rng(1)
        df = pd.concat(
            [
                pd.DataFrame({"datetime": t, "city_name": "Alpha",
                              "pm2_5": rng.normal(50, 10, 600), "lat": 23.7, "lon": 90.4}),
                pd.DataFrame({"datetime": t, "city_name": "Beta",
                              "pm2_5": rng.normal(50, 10, 600), "lat": 24.7, "lon": 91.4}),
            ]
        )
        assert len(quality.find_duplicate_series(df)) == 0

    def test_a_synthetic_ramp_is_flagged(self):
        annual = pd.DataFrame({"year": range(2000, 2022),
                               "mean_pm25": np.linspace(40, 158, 22)})
        r = quality.monotonicity_report(annual)
        assert r["suspected_synthetic"] is True
        assert r["monotone_fraction"] == 1.0

    def test_a_realistic_noisy_series_is_not_flagged(self):
        rng = np.random.default_rng(2)
        annual = pd.DataFrame({"year": range(2000, 2022),
                               "mean_pm25": 80 + rng.normal(0, 12, 22)})
        assert quality.monotonicity_report(annual)["suspected_synthetic"] is False

    def test_short_segments_are_marked_unscreened_not_clean(self):
        annual = pd.DataFrame({"year": [2023, 2024, 2025], "mean_pm25": [50, 48, 47]})
        r = quality.monotonicity_report(annual)
        assert r["screened"] is False
        assert r["suspected_synthetic"] is False

    def test_segmentation_splits_at_the_step(self):
        annual = pd.DataFrame(
            {"year": list(range(2018, 2026)),
             "mean_pm25": [100, 110, 120, 130, 140, 50, 48, 47]}
        )
        segs = quality.segment_by_step(annual, threshold=25)
        assert len(segs) == 2

    def test_whole_series_screen_would_miss_a_spliced_ramp(self):
        """The reason ``backfill_screen`` segments first: testing the whole
        series lets a real, noisy tail hide a synthetic head."""
        annual = pd.DataFrame(
            {"year": list(range(2000, 2026)),
             "mean_pm25": list(np.linspace(40, 158, 22)) + [118, 50, 48, 47]}
        )
        assert quality.monotonicity_report(annual)["suspected_synthetic"] is False
        screen = quality.backfill_screen(annual)
        assert screen["suspected_synthetic"].fillna(False).any()

    def test_completeness_finds_impossible_values(self):
        df = pd.DataFrame({"pm2_5": [10.0, -5.0, 20.0], "aqi": [50, 600, 80]})
        c = quality.completeness_report(df).set_index("column")
        assert c.loc["pm2_5", "out_of_physical_range"] == 1
        assert c.loc["aqi", "out_of_physical_range"] == 1


# ==========================================================================
# Exposure analytics
# ==========================================================================
class TestExposure:
    @pytest.fixture
    def synthetic(self):
        t = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h")
        rng = np.random.default_rng(3)
        base = 60 + 30 * np.cos((t.dayofyear - 15) / 365 * 2 * np.pi)
        df = pd.DataFrame(
            {
                "datetime": t,
                "city_name": "Testville",
                "lat": 23.7,
                "lon": 90.4,
                "pm2_5": np.clip(base + rng.normal(0, 8, len(t)), 1, None),
                "pm10": np.clip(base * 1.35 + rng.normal(0, 10, len(t)), 1, None),
                "aqi": np.clip(base * 2.2 + rng.normal(0, 15, len(t)), 5, 500),
            }
        )
        df["date"] = df["datetime"].dt.date
        df["year"] = df["datetime"].dt.year
        df["month"] = df["datetime"].dt.month
        df["hour"] = df["datetime"].dt.hour
        return df

    def test_aqi_categories(self):
        assert exposure.aqi_category(25) == "Good"
        assert exposure.aqi_category(75) == "Moderate"
        assert exposure.aqi_category(120) == "Unhealthy for Sensitive Groups"
        assert exposure.aqi_category(175) == "Unhealthy"
        assert exposure.aqi_category(250) == "Very Unhealthy"
        assert exposure.aqi_category(400) == "Hazardous"
        assert exposure.aqi_category(np.nan) == "No data"

    def test_daily_means_flag_short_days(self, synthetic):
        d = synthetic.drop(synthetic.index[:20])  # gut the first day
        dm = exposure.daily_means(d)
        assert dm["valid_24h"].iloc[0] is np.False_ or not dm["valid_24h"].iloc[0]

    def test_exceedance_counts_never_exceed_valid_days(self, synthetic):
        e = exposure.exceedance_summary(synthetic)
        assert (e["days_over_who_pm25"] <= e["valid_days"]).all()
        assert (e["days_over_bd_pm25"] <= e["days_over_who_pm25"]).all()

    def test_shift_exposure_covers_all_24_hours(self, synthetic):
        s = exposure.shift_exposure(synthetic)
        assert s["hours_sampled"].sum() == len(synthetic)

    def test_work_adjustment_percentages_are_bounded(self, synthetic):
        w = exposure.work_adjustment_calendar(synthetic, "Testville", trigger_aqi=150)
        assert w["trigger_pct"].between(0, 100).all()

    def test_unknown_city_is_rejected(self, synthetic):
        with pytest.raises(KeyError):
            exposure.work_adjustment_calendar(synthetic, "Nowhere")

    def test_trend_slope_refuses_short_series(self):
        a = pd.DataFrame({"year": [2023, 2024], "mean_pm25": [50, 48]})
        assert exposure.trend_slope(a)["slope_per_year"] is None
