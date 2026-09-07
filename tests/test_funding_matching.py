"""Tests for Phase 19: Funding Matching (Wave 2 — Funding Intelligence).

Validates deterministic, rule-by-rule matching of studies against verified
Saudi funding programs seeded in Phase 18.
"""
import pytest

from app.services.funding_matching import (
    evaluate_single_program_match,
    _normalize_sector,
    _normalize_stage,
    STATUS_MATCH,
    STATUS_POSSIBLE_MATCH,
    STATUS_NEEDS_INFO,
    STATUS_NOT_MATCHED,
)


# ── Helper: mock a minimal FundingProgram ORM object ────────────────────────

class _FakeRule:
    def __init__(self, rule_key, source_url="https://sdb.gov.sa", source_authority="OFFICIAL_PROVIDER", rule_version="1.0.0"):
        self.rule_key = rule_key
        self.source_url = source_url
        self.source_authority = source_authority
        self.rule_version = rule_version


class _FakeProgram:
    def __init__(self, **kw):
        self.id = kw.get("id", 1)
        self.slug = kw.get("slug", "test-prog")
        self.provider = kw.get("provider", "SDB")
        self.provider_ar = kw.get("provider_ar", "بنك التنمية")
        self.program_name_ar = kw.get("program_name_ar", "مسار تمويل")
        self.program_name_en = kw.get("program_name_en", "Test Program")
        self.program_type = kw.get("program_type", "DIRECT_LOAN")
        self.target_business_stage = kw.get("target_business_stage", "ALL")
        self.target_sectors = kw.get("target_sectors", ["all"])
        self.financing_min = kw.get("financing_min", 100000.0)
        self.financing_max = kw.get("financing_max", 4000000.0)
        self.term_months = kw.get("term_months", 96)
        self.grace_period_months = kw.get("grace_period_months", 24)
        self.official_source_url = kw.get("official_source_url", "https://www.sdb.gov.sa")
        self.source_owner = kw.get("source_owner", "SDB")
        self.rule_version = kw.get("rule_version", "1.0.0")
        self.last_verified_at = None
        self.verification_status = "VERIFIED_CURRENT"
        self.owner_contribution_rule = kw.get("owner_contribution_rule")
        self.collateral_rule = kw.get("collateral_rule")
        self.revenue_rule = kw.get("revenue_rule")
        self.business_age_rule = kw.get("business_age_rule")
        self.rules = kw.get("rules", [])


# ── Normalization Tests ─────────────────────────────────────────────────────

class TestNormalization:

    def test_normalize_sector_synonyms(self):
        assert _normalize_sector("tech") == "technology"
        assert _normalize_sector("IT") == "technology"
        assert _normalize_sector("restaurant") == "food_beverage"
        assert _normalize_sector("logistics") == "logistics"

    def test_normalize_sector_empty(self):
        assert _normalize_sector(None) == ""
        assert _normalize_sector("") == ""

    def test_normalize_stage_startup_variants(self):
        assert _normalize_stage("idea") == "STARTUP"
        assert _normalize_stage("MVP") == "STARTUP"
        assert _normalize_stage("seed") == "STARTUP"
        assert _normalize_stage(None) == "STARTUP"

    def test_normalize_stage_existing(self):
        assert _normalize_stage("existing") == "EXISTING"
        assert _normalize_stage("OPERATING") == "EXISTING"

    def test_normalize_stage_expansion(self):
        assert _normalize_stage("expansion") == "EXPANSION"
        assert _normalize_stage("GROWTH") == "EXPANSION"


# ── Sector Rule Tests ───────────────────────────────────────────────────────

class TestSectorRule:

    def test_all_sectors_pass(self):
        prog = _FakeProgram(target_sectors=["all"])
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="technology",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        sector_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "sector"][0]
        assert sector_eval["result"] == "PASS"

    def test_sector_mismatch_fails(self):
        prog = _FakeProgram(target_sectors=["agriculture", "poultry"])
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="technology",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        sector_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "sector"][0]
        assert sector_eval["result"] == "FAIL"
        assert "sector" in result["failed_rules"]

    def test_missing_sector_unknown(self):
        prog = _FakeProgram(target_sectors=["retail", "services"])
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        sector_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "sector"][0]
        assert sector_eval["result"] == "UNKNOWN"


# ── Business Stage Rule Tests ───────────────────────────────────────────────

class TestBusinessStage:

    def test_stage_all_passes(self):
        prog = _FakeProgram(target_business_stage="ALL")
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=1_000_000,
            owner_contribution=300_000, funding_gap=700_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        stage_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "business_stage"][0]
        assert stage_eval["result"] == "PASS"

    def test_stage_existing_fails_for_startup(self):
        prog = _FakeProgram(target_business_stage="EXISTING")
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=1_000_000,
            owner_contribution=300_000, funding_gap=700_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        stage_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "business_stage"][0]
        assert stage_eval["result"] == "FAIL"


# ── Financing Amount Rule Tests ─────────────────────────────────────────────

class TestFinancingAmount:

    def test_within_range_passes(self):
        prog = _FakeProgram(financing_min=100_000, financing_max=4_000_000)
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        fin_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "financing_limit"][0]
        assert fin_eval["result"] == "PASS"

    def test_exceeds_max_fails(self):
        prog = _FakeProgram(financing_min=100_000, financing_max=500_000)
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        fin_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "financing_limit"][0]
        assert fin_eval["result"] == "FAIL"
        assert "financing_limit" in result["failed_rules"]

    def test_below_min_fails(self):
        prog = _FakeProgram(financing_min=5_000_000, financing_max=50_000_000)
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        fin_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "financing_limit"][0]
        assert fin_eval["result"] == "FAIL"


# ── Owner Contribution Rule Tests ───────────────────────────────────────────

class TestOwnerContribution:

    def test_sufficient_equity_passes(self):
        prog = _FakeProgram(
            owner_contribution_rule={"min_percentage": 0.20, "required": True},
            rules=[_FakeRule("owner_contribution")],
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        oc_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "owner_contribution"][0]
        assert oc_eval["result"] == "PASS"

    def test_insufficient_equity_fails(self):
        prog = _FakeProgram(
            owner_contribution_rule={"min_percentage": 0.20, "required": True},
            rules=[_FakeRule("owner_contribution")],
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=300_000,  # 10% < 20%
            funding_gap=2_700_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        oc_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "owner_contribution"][0]
        assert oc_eval["result"] == "FAIL"
        assert "owner_contribution" in result["failed_rules"]


# ── Collateral Rule Tests ───────────────────────────────────────────────────

class TestCollateral:

    def test_no_collateral_required_passes(self):
        prog = _FakeProgram(collateral_rule={"required": False})
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        col_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "collateral"][0]
        assert col_eval["result"] == "PASS"

    def test_guarantee_program_passes_without_collateral(self):
        prog = _FakeProgram(
            program_type="GUARANTEE",
            collateral_rule={"required": True},
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        col_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "collateral"][0]
        assert col_eval["result"] == "PASS"

    def test_collateral_required_and_missing_fails(self):
        prog = _FakeProgram(
            collateral_rule={"required": True, "coverage_ratio": 1.0},
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="services",
            study_stage="startup", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        col_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "collateral"][0]
        assert col_eval["result"] == "FAIL"


# ── Overall Status Classification ───────────────────────────────────────────

class TestOverallStatus:

    def _make_full_match_program(self):
        return _FakeProgram(
            target_sectors=["all"],
            target_business_stage="ALL",
            financing_min=100_000,
            financing_max=5_000_000,
            owner_contribution_rule={"min_percentage": 0.20},
            collateral_rule={"required": False},
            revenue_rule=None,
        )

    def test_full_match(self):
        prog = self._make_full_match_program()
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=3_000_000,
        )
        assert result["overall_match_status"] == STATUS_MATCH
        assert len(result["failed_rules"]) == 0

    def test_not_matched_with_failure(self):
        prog = _FakeProgram(
            target_sectors=["agriculture"],
            financing_max=5_000_000,
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="technology",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        assert result["overall_match_status"] == STATUS_NOT_MATCHED
        assert "sector" in result["failed_rules"]

    def test_needs_info_on_missing_core_data(self):
        prog = _FakeProgram(
            target_sectors=["all"],
            owner_contribution_rule={"min_percentage": 0.20},
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=0,  # no cost
            owner_contribution=None, funding_gap=0,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        assert result["overall_match_status"] == STATUS_NEEDS_INFO

    def test_possible_match_with_unknown_rules(self):
        prog = _FakeProgram(
            target_sectors=["all"],
            target_business_stage="ALL",
            financing_min=100_000,
            financing_max=5_000_000,
            owner_contribution_rule={"min_percentage": 0.20},
            collateral_rule={"required": True},  # requires collateral
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None,
            available_collateral_value=500_000,  # partial
            collateral_coverage_ratio=0.22,
            safe_debt_capacity=0,
        )
        assert result["overall_match_status"] == STATUS_POSSIBLE_MATCH


# ── Provenance Verification ─────────────────────────────────────────────────

class TestProvenance:

    def test_rule_evaluations_have_source_urls(self):
        prog = _FakeProgram(
            target_sectors=["all"],
            official_source_url="https://www.sdb.gov.sa/ar-sa/services/tamayoz",
            source_owner="Social Development Bank",
            rules=[_FakeRule("sector", source_url="https://www.sdb.gov.sa/ar-sa/services/tamayoz")],
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        for ev in result["rule_evaluations"]:
            assert ev["source_url"], f"Rule {ev['rule_key']} missing source_url"
            assert ev["source_authority"], f"Rule {ev['rule_key']} missing source_authority"
            assert ev["rule_version"], f"Rule {ev['rule_key']} missing rule_version"


# ── Revenue Rule Tests ──────────────────────────────────────────────────────

class TestRevenue:

    def test_revenue_under_ceiling_passes(self):
        prog = _FakeProgram(
            target_sectors=["all"],
            revenue_rule={"max_annual_revenue": 40_000_000},
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="existing", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=12_500_000,
            available_collateral_value=0, collateral_coverage_ratio=0,
            safe_debt_capacity=0,
        )
        rev_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "revenue"][0]
        assert rev_eval["result"] == "PASS"

    def test_revenue_over_ceiling_fails(self):
        prog = _FakeProgram(
            target_sectors=["all"],
            revenue_rule={"max_annual_revenue": 10_000_000},
        )
        result = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="existing", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=25_000_000,
            available_collateral_value=0, collateral_coverage_ratio=0,
            safe_debt_capacity=0,
        )
        rev_eval = [e for e in result["rule_evaluations"] if e["rule_key"] == "revenue"][0]
        assert rev_eval["result"] == "FAIL"


# ── Dynamic Recalculation Tests ─────────────────────────────────────────────

class TestDynamicRecalculation:

    def test_changing_owner_contribution_changes_result(self):
        """Increasing equity from 10% to 25% should flip owner_contribution from FAIL to PASS."""
        prog = _FakeProgram(
            target_sectors=["all"],
            financing_max=5_000_000,
            owner_contribution_rule={"min_percentage": 0.20},
        )
        # Low equity → FAIL
        r1 = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=300_000, funding_gap=2_700_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        oc1 = [e for e in r1["rule_evaluations"] if e["rule_key"] == "owner_contribution"][0]
        assert oc1["result"] == "FAIL"

        # Higher equity → PASS
        r2 = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        oc2 = [e for e in r2["rule_evaluations"] if e["rule_key"] == "owner_contribution"][0]
        assert oc2["result"] == "PASS"

    def test_adding_collateral_changes_result(self):
        """Adding verified collateral should flip from FAIL to PASS."""
        prog = _FakeProgram(
            target_sectors=["all"],
            financing_max=5_000_000,
            collateral_rule={"required": True, "coverage_ratio": 1.0},
        )
        # No collateral → FAIL
        r1 = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None, available_collateral_value=0,
            collateral_coverage_ratio=0, safe_debt_capacity=0,
        )
        c1 = [e for e in r1["rule_evaluations"] if e["rule_key"] == "collateral"][0]
        assert c1["result"] == "FAIL"

        # With collateral → PASS
        r2 = evaluate_single_program_match(
            program=prog, study_id=1, study_sector="retail",
            study_stage="idea", project_cost=3_000_000,
            owner_contribution=750_000, funding_gap=2_250_000,
            current_annual_revenue=None,
            available_collateral_value=2_500_000,
            collateral_coverage_ratio=1.11,
            safe_debt_capacity=0,
        )
        c2 = [e for e in r2["rule_evaluations"] if e["rule_key"] == "collateral"][0]
        assert c2["result"] == "PASS"
