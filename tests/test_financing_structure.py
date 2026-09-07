"""
Tests for Phase 20: Financing Structure (Wave 2 — Funding Intelligence Capstone).

Validates deterministic Sources & Uses synthesis, capital structure metrics,
warnings, and next actions.
"""
import os
import tempfile

if not os.environ.get("DATABASE_URL"):
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + handle.name

import pytest
from app.services.financing_structure import (
    compute_financing_structure,
    DISCLAIMER_AR,
    DISCLAIMER_EN,
    RECOMMENDED_MIN_EQUITY_RATIO,
)


class _FakeProject:
    def __init__(self, name="مشروع تجريبي", industry="technology", investment=3_000_000, stage="idea"):
        self.id = 1
        self.name = name
        self.industry = industry
        self.investment = investment
        self.stage = stage


class _FakeStudy:
    def __init__(self, id=1, project_id=1):
        self.id = id
        self.project_id = project_id


class _MockQuery:
    def __init__(self, items):
        self._items = items

    def options(self, *a, **kw):
        return self

    def filter(self, *a, **kw):
        return self

    def order_by(self, *a, **kw):
        return self

    def all(self):
        return self._items


class _MockSession:
    def __init__(self, programs=None):
        self.programs = programs or []

    def query(self, model):
        return _MockQuery(self.programs)


class TestFinancingStructure:

    def test_sources_and_uses_reconciliation(self):
        """Test that Sources & Uses properly balance and reconcile against project requirement."""
        db = _MockSession([])
        project = _FakeProject(investment=3_000_000)
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=750_000,
            capex_assumption=3_000_000,
            existing_facilities=0,
        )

        assert res["total_project_requirement"] == 3_000_000.0
        assert res["owner_equity"] == 750_000.0
        assert res["equity_percentage"] == 0.25
        assert res["residual_gap"] == 2_250_000.0

        # Sum of sources amounts must match total project requirement
        sources_total = sum(s["amount"] for s in res["sources"])
        assert sources_total == 3_000_000.0

        # Uses amount must equal total project requirement
        uses_total = sum(u["amount"] for u in res["uses"])
        assert uses_total == 3_000_000.0

    def test_low_owner_equity_warning(self):
        """When equity is below 20%, an internal screening warning should be triggered."""
        db = _MockSession([])
        project = _FakeProject(investment=3_000_000)
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=300_000,  # 10% < 20%
            capex_assumption=3_000_000,
        )

        warning_codes = [w["code"] for w in res["warnings"]]
        assert "INTERNAL_SCREENING_LOW_EQUITY" in warning_codes
        assert "RESIDUAL_GAP_EXISTS" in warning_codes

        low_eq = [w for w in res["warnings"] if w["code"] == "INTERNAL_SCREENING_LOW_EQUITY"][0]
        assert "INTERNAL_SCREENING_ASSUMPTION" in low_eq["message_ar"] or "فرضية فحص داخلي" in low_eq["message_ar"]

    def test_exceeds_safe_debt_capacity_warning(self):
        """When debt exceeds assessed safe debt capacity, an alert should be raised."""
        db = _MockSession([])
        project = _FakeProject(investment=5_000_000)
        study = _FakeStudy()

        # Financial period with limited EBITDA yielding modest debt capacity
        financial_period = {
            "revenue": 1_000_000,
            "ebitda": 100_000,
            "existing_debt": 0,
            "annual_debt_service": 20_000,
        }

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=1_000_000,
            capex_assumption=5_000_000,
            existing_facilities=1_500_000,  # Debt of 1.5M > safe capacity
            financial_period_dict=financial_period,
        )

        warning_codes = [w["code"] for w in res["warnings"]]
        assert "EXCEEDS_SAFE_DEBT_CAPACITY" in warning_codes

    def test_collateral_shortfall_warning(self):
        """When debt is unsecured or collateral is partial, advisory warning is generated."""
        db = _MockSession([])
        project = _FakeProject(investment=3_000_000)
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=1_000_000,
            capex_assumption=3_000_000,
            existing_facilities=1_000_000,
            collateral_dicts=[{
                "id": 1,
                "collateral_type": "PROPERTY",
                "reported_value": 400_000,
                "verified_value": 400_000,
                "encumbrance_status": "UNENCUMBERED",
                "encumbrance_amount": 0,
                "verification_status": "VERIFIED",
            }],
        )

        warning_codes = [w["code"] for w in res["warnings"]]
        assert "COLLATERAL_SHORTFALL" in warning_codes
        assert res["collateral_coverage_ratio"] == 0.4

    def test_next_actions_generation(self):
        """Verify sequential next actions roadmap is generated."""
        db = _MockSession([])
        project = _FakeProject(investment=3_000_000)
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=750_000,
            capex_assumption=3_000_000,
        )

        actions = res["next_actions"]
        assert len(actions) == 4
        assert actions[0]["step_number"] == 1
        assert "السجل التجاري" in actions[0]["title_ar"]

    def test_mandatory_disclaimers(self):
        """Verify regulatory disclaimers are present in both languages."""
        db = _MockSession([])
        project = _FakeProject(investment=2_000_000)
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=500_000,
            capex_assumption=2_000_000,
        )

        assert res["disclaimer_ar"] == DISCLAIMER_AR
        assert res["disclaimer_en"] == DISCLAIMER_EN
        assert "استرشادي" in res["disclaimer_ar"]
        assert "advisory" in res["disclaimer_en"].lower()

    # ── Semantic Regression Tests (Wave 2 Final Correction) ─────────────────

    def test_possible_match_never_becomes_allocated_cash(self):
        """Rule 1: POSSIBLE_MATCH must NEVER be allocated as cash debt in Sources & Uses."""
        from tests.test_funding_matching import _FakeProgram
        prog = _FakeProgram(
            id=10,
            slug="test-loan-prog",
            program_type="DIRECT_LOAN",
            financing_min=100_000,
            financing_max=2_000_000,
            target_business_stage="ALL",
            target_sectors=["all"],
            collateral_rule={"required": True},  # Requires collateral
            revenue_rule=None,
        )
        db = _MockSession([prog])
        project = _FakeProject(investment=2_000_000, industry="technology", stage="startup")
        study = _FakeStudy()

        # Partial collateral yields UNKNOWN for collateral rule => overall POSSIBLE_MATCH
        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=1_000_000,
            capex_assumption=2_000_000,
            existing_facilities=0,
            collateral_dicts=[{
                "id": 1,
                "market_value": 300_000,
                "pledged_amount": 0,
                "reported_value": 300_000,
                "verified_value": 300_000,
                "collateral_type": "PROPERTY",
                "encumbrance_status": "UNENCUMBERED",
                "verification_status": "VERIFIED",
            }],
        )

        # Confirm program allocation has allocated_amount = None (never allocated cash)
        for pa in res["program_allocations"]:
            if pa["match_status"] == "POSSIBLE_MATCH":
                assert pa["allocated_amount"] is None
                assert pa["allocation_status"] == "VALIDATION_REQUIRED"

        # allocated_program_debt must be 0
        assert res["allocated_program_debt"] == 0.0
        # Sources must not contain any cash debt from this possible match
        prog_sources = [s for s in res["sources"] if s["source_type"] == "PROGRAM_DEBT"]
        assert len(prog_sources) == 0

    def test_guarantee_never_contributes_cash_to_sources(self):
        """Rule 2: Guarantee programs (e.g. Kafalah) must contribute 0 SAR cash to Sources & Uses."""
        from tests.test_funding_matching import _FakeProgram
        kafalah_prog = _FakeProgram(
            id=20,
            slug="kafalah-standard",
            provider="Kafalah",
            provider_ar="برنامج كفالة",
            program_type="GUARANTEE",
            financing_min=100_000,
            financing_max=15_000_000,
            target_business_stage="ALL",
            target_sectors=["all"],
            collateral_rule={"required": False},
            revenue_rule=None,
        )
        db = _MockSession([kafalah_prog])
        project = _FakeProject(investment=3_000_000, industry="technology", stage="startup")
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=1_000_000,
            capex_assumption=3_000_000,
            existing_facilities=0,
        )

        # Allocated program debt must be 0.0 (Guarantee is not a cash loan!)
        assert res["allocated_program_debt"] == 0.0
        assert res["residual_gap"] == 2_000_000.0

        # Guarantee must be in credit_enhancements, NOT in sources as debt cash
        assert len(res["credit_enhancements"]) == 1
        assert res["credit_enhancements"][0]["program_slug"] == "kafalah-standard"
        assert res["credit_enhancements"][0]["cash_contribution"] == 0.0

        # In sources: only equity and residual gap
        source_types = [s["source_type"] for s in res["sources"]]
        assert "PROGRAM_DEBT" not in source_types
        assert "EQUITY" in source_types
        assert "UNFUNDED" in source_types

    def test_unknown_financing_max_never_defaults_to_remaining_gap(self):
        """Rule 3: If financing_max is unknown, amount must not be invented or defaulted to remaining gap."""
        from tests.test_funding_matching import _FakeProgram
        prog_unknown_max = _FakeProgram(
            id=30,
            slug="unknown-max-loan",
            program_type="DIRECT_LOAN",
            financing_min=100_000,
            financing_max=None,  # Unknown limit
            target_business_stage="ALL",
            target_sectors=["all"],
            collateral_rule={"required": False},
            revenue_rule=None,
        )
        db = _MockSession([prog_unknown_max])
        project = _FakeProject(investment=3_000_000, industry="technology", stage="startup")
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=1_000_000,
            capex_assumption=3_000_000,
            existing_facilities=0,
        )

        # Must NOT allocate the 2,000,000 SAR gap!
        assert res["allocated_program_debt"] == 0.0
        pa = res["program_allocations"][0]
        assert pa["allocated_amount"] is None
        assert pa["allocation_status"] == "UNKNOWN_LIMIT"
        assert res["residual_gap"] == 2_000_000.0

    def test_potential_funding_is_not_counted_as_confirmed_funding(self):
        """Rule 4A: Potential program capacity is strictly separated from confirmed sources."""
        from tests.test_funding_matching import _FakeProgram
        loan_prog = _FakeProgram(
            id=40,
            slug="direct-loan",
            program_type="DIRECT_LOAN",
            financing_min=100_000,
            financing_max=1_500_000,
            target_business_stage="ALL",
            target_sectors=["all"],
            collateral_rule={"required": False},
            revenue_rule=None,
        )
        db = _MockSession([loan_prog])
        # Project 2.0M, owner 600k, existing 200k => gap = 1.2M <= 1.5M max => MATCH
        project = _FakeProject(investment=2_000_000, industry="technology", stage="startup")
        study = _FakeStudy()

        # Provide complete canonical financial period so capacity_status == CALCULATED
        # EBITDA 1M, annual debt service 100k => headroom 700k * 4.5 = 3.15M safe capacity
        financial_period = {
            "revenue": 5_000_000,
            "ebitda": 1_000_000,
            "existing_debt": 200_000,
            "annual_debt_service": 100_000,
        }

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=600_000,
            capex_assumption=2_000_000,
            existing_facilities=200_000,
            financial_period_dict=financial_period,
        )

        assert res["capacity_status"] == "CALCULATED"
        # Confirmed sources must strictly equal owner equity (600k) + existing facilities (200k) = 800k
        assert res["total_confirmed_sources"] == 800_000.0
        assert res["confirmed_sources"]["total_confirmed"] == 800_000.0
        assert res["confirmed_funding_gap"] == 1_200_000.0
        assert res["potential_program_capacity"] == 1_200_000.0
        assert res["potential_residual_gap"] == 0.0
        # Confirmed sources does NOT include the 1.2M potential loan!
        assert res["total_confirmed_sources"] != res["total_identified_sources"]
        assert res["total_identified_sources"] == 2_000_000.0

    def test_unknown_borrowing_capacity_never_allocates_debt(self):
        """Rule 2: When borrowing capacity is unknown/uncalculated, matched debt programs must NOT be allocated money."""
        from tests.test_funding_matching import _FakeProgram
        loan_prog = _FakeProgram(
            id=55,
            slug="direct-loan-unassessed",
            program_type="DIRECT_LOAN",
            financing_min=100_000,
            financing_max=1_500_000,
            target_business_stage="ALL",
            target_sectors=["all"],
            collateral_rule={"required": False},
            revenue_rule=None,
        )
        db = _MockSession([loan_prog])
        project = _FakeProject(investment=2_000_000, industry="technology", stage="startup")
        study = _FakeStudy()

        # No financial period provided -> capacity_status is NO_DATA
        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=600_000,
            capex_assumption=2_000_000,
            existing_facilities=0,
            financial_period_dict=None,
        )

        assert res["capacity_status"] == "NO_DATA"
        assert res["allocated_program_debt"] == 0.0
        assert res["potential_program_capacity"] == 0.0
        assert res["confirmed_funding_gap"] == 1_400_000.0
        assert res["potential_residual_gap"] == 1_400_000.0

        pa = res["program_allocations"][0]
        assert pa["match_status"] == "MATCH"
        assert pa["allocated_amount"] is None
        assert pa["allocation_status"] == "CAPACITY_NOT_EVALUATED"

    def test_screening_debt_does_not_exceed_borrowing_capacity(self):
        """Rule 4B: Screening debt allocation is strictly constrained by calculated safe borrowing capacity."""
        from tests.test_funding_matching import _FakeProgram
        loan_prog = _FakeProgram(
            id=50,
            slug="huge-loan",
            program_type="DIRECT_LOAN",
            financing_min=100_000,
            financing_max=4_000_000,  # Huge max
            target_business_stage="ALL",
            target_sectors=["all"],
            collateral_rule={"required": False},
            revenue_rule=None,
        )
        db = _MockSession([loan_prog])
        project = _FakeProject(investment=5_000_000, industry="technology", stage="startup")
        study = _FakeStudy()

        # Canonical fields: existing_debt and annual_debt_service
        financial_period = {
            "revenue": 1_000_000,
            "ebitda": 200_000,
            "existing_debt": 100_000,
            "annual_debt_service": 50_000,
        }

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=1_000_000,
            capex_assumption=5_000_000,
            existing_facilities=100_000,
            financial_period_dict=financial_period,
        )

        assert res["capacity_status"] == "CALCULATED"
        safe_cap = res["safe_debt_capacity"]
        assert safe_cap > 0
        # Program debt must NOT exceed safe_debt_capacity
        assert res["allocated_program_debt"] <= safe_cap

    def test_twenty_percent_assumption_not_represented_as_verified_external_rule(self):
        """Rule 5: 20% equity benchmark must be explicitly labeled as internal screening assumption."""
        db = _MockSession([])
        project = _FakeProject(investment=3_000_000)
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=300_000,  # 10%
            capex_assumption=3_000_000,
        )

        low_eq_warnings = [w for w in res["warnings"] if w["code"] == "INTERNAL_SCREENING_LOW_EQUITY"]
        assert len(low_eq_warnings) == 1
        w = low_eq_warnings[0]
        # Must explicitly mention internal screening assumption
        assert "INTERNAL_SCREENING_ASSUMPTION" in w["message_ar"] or "فرضية فحص داخلي" in w["message_ar"]
        assert "INTERNAL_SCREENING_ASSUMPTION" in w["message_en"]
        # Must NOT claim universal statutory lender minimum
        assert "المعايير التنموية" not in w["title_ar"]

    def test_match_never_implies_approval(self):
        """Rule 6 & 7: Matched programs must never show ELIGIBLE / APPROVED."""
        from tests.test_funding_matching import _FakeProgram
        prog = _FakeProgram(
            id=60,
            slug="direct-sme-loan",
            program_type="DIRECT_LOAN",
            financing_min=100_000,
            financing_max=1_000_000,
            target_business_stage="ALL",
            target_sectors=["all"],
            collateral_rule={"required": False},
            revenue_rule=None,
        )
        db = _MockSession([prog])
        # Project 1.5M, owner 500k => gap = 1.0M <= 1.0M max => MATCH
        project = _FakeProject(investment=1_500_000, industry="technology", stage="startup")
        study = _FakeStudy()

        res = compute_financing_structure(
            db,
            study=study,
            project=project,
            owner_contribution=500_000,
            capex_assumption=1_500_000,
        )

        # Next action step 4 status must be MATCHED_PROGRAM, not ELIGIBLE
        act_4 = [a for a in res["next_actions"] if a["step_number"] == 4][0]
        assert act_4["status"] == "MATCHED_PROGRAM"
        assert act_4["status"] != "ELIGIBLE"
        assert act_4["status"] != "APPROVED"
        assert "موافق" not in act_4["description_ar"]
        assert "approved" not in act_4["description_en"].lower()

    def test_real_api_integration_canonical_financial_period(self):
        """Requirement 3: Real integration test creating a CompanyFinancialPeriod with canonical fields:
        revenue, ebitda, existing_debt, annual_debt_service.
        Calls the real GET /studies/{study_id}/financing-structure API.
        Verifies:
        - financing structure reads those exact canonical fields
        - capacity_status = CALCULATED when inputs are complete
        - safe_debt_capacity equals the real Borrowing Capacity service result
        - program screening allocation never exceeds available safe debt capacity
        """
        import uuid
        from fastapi.testclient import TestClient
        from app.main import app
        from app import db as app_db
        from app.services.borrowing_capacity import estimate_borrowing_capacity

        app_db.init_db()
        client = TestClient(app)

        # 1. Register fresh test user
        email = f"real_api_test_{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123!"
        reg = client.post("/auth/register", json={"email": email, "password": password})
        assert reg.status_code in (200, 201), reg.text
        tok = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
        headers = {"Authorization": f"Bearer {tok}"}

        # 2. Create Project and Study
        proj = client.post("/projects/", headers=headers, json={
            "name": "شركة التقنية المتقدمة المتكاملة",
            "industry": "technology",
            "investment": 3_000_000,
        }).json()
        study = client.post("/feasibility/", headers=headers, json={
            "project_id": proj["id"],
            "title": "دراسة هيكلة التمويل الحقيقية",
            "industry": "technology",
            "investment": 3_000_000,
        }).json()
        study_id = study["id"]

        # 3. Add study assumptions for capex and owner_contribution
        client.post("/assumptions/", headers=headers, json={
            "study_id": study_id,
            "key": "capex",
            "label_en": "Capex",
            "label_ar": "النفقات الرأسمالية",
            "value_number": 3_000_000,
            "unit": "SAR",
            "origin": "USER",
        })
        client.post("/assumptions/", headers=headers, json={
            "study_id": study_id,
            "key": "owner_contribution",
            "label_en": "Owner contribution",
            "label_ar": "المساهمة الذاتية",
            "value_number": 1_000_000,
            "unit": "SAR",
            "origin": "USER",
        })

        # 4. Create CompanyFinancialPeriod using EXACT canonical production schema fields
        canonical_revenue = 3_500_000.0
        canonical_ebitda = 600_000.0
        canonical_existing_debt = 200_000.0
        canonical_annual_debt_service = 80_000.0

        fp_res = client.put(
            f"/studies/{study_id}/financial-periods/FY2025",
            headers=headers,
            json={
                "source": "audited_statement",
                "revenue": canonical_revenue,
                "ebitda": canonical_ebitda,
                "existing_debt": canonical_existing_debt,
                "annual_debt_service": canonical_annual_debt_service,
            },
        )
        assert fp_res.status_code == 200, fp_res.text

        # 5. Call real financing structure API endpoint
        resp = client.get(f"/studies/{study_id}/financing-structure", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Expected real Borrowing Capacity service result for exact same inputs
        expected_borrowing = estimate_borrowing_capacity(
            ebitda=canonical_ebitda,
            existing_debt=canonical_existing_debt,
            annual_debt_service=canonical_annual_debt_service,
        )

        # Verification:
        # - financing structure reads those exact fields
        assert data["capacity_status"] == "CALCULATED"
        # - safe_debt_capacity equals the real Borrowing Capacity service result
        assert data["safe_debt_capacity"] == expected_borrowing["base_capacity"]
        # - program screening allocation never exceeds available safe debt capacity
        assert data["allocated_program_debt"] <= data["safe_debt_capacity"]
        # - confirmed funding gap = total requirement - total confirmed sources
        expected_confirmed_gap = round(3_000_000 - data["total_confirmed_sources"], 2)
        assert data["confirmed_funding_gap"] == expected_confirmed_gap
        # - potential residual gap = total requirement - total identified sources
        expected_residual_gap = max(0.0, round(3_000_000 - data["total_identified_sources"], 2))
        assert data["potential_residual_gap"] == expected_residual_gap
        assert data["residual_gap"] == expected_residual_gap

