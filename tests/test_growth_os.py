"""Wave 6 — Growth OS Automated Test Suite.

Comprehensive tests covering:
1. Business Health: No actuals recorded returns INSUFFICIENT_DATA, not healthy or at risk.
2. Business Health: Missing data != poor performance; missing values produce UNKNOWN / NOT_AVAILABLE.
3. Trend Engine: Requires at least 2 periods with known values; < 2 periods yields INSUFFICIENT_DATA.
4. Trend Engine: Zero denominator handled safely (percentage_change is None / NOT_AVAILABLE).
5. Trend Engine: Evaluates IMPROVING vs DETERIORATING based on metric optimization direction.
6. Unit Economics: CAC calculated ONLY when marketing spend AND acquired customers are both known.
7. Unit Economics: Contribution margin, ticket size, and fixed/variable cost breakdowns.
8. Growth Funding: Links to Wave 2 matched programs without duplicating logic; potential funding != cash.
9. What-If Model: Output provenance strictly separates ACTUAL, BASELINE, USER_ASSUMPTION, PLATFORM_DERIVED.
10. What-If Model: Deterministic cash payback months, runway impact, and minimum cash required.
11. Expansion Readiness: States READY, CONDITIONALLY_READY, NOT_READY, NEEDS_INFORMATION.
12. Expansion Readiness: Prerequisites evaluated as PASS, FAIL, UNKNOWN, NOT_APPLICABLE.
13. Risks: Detection of runway depletion, margin compression, capacity exhaustion, fixed-cost overhang.
14. Monthly Reviews: Immutable frozen snapshots with auto-incrementing review_version.
15. Strategic Decisions: Supports SCALE, FIX, PIVOT, HOLD, STOP, NEEDS_INFORMATION.
16. SCALE Guardrail: Rejected when readiness is NEEDS_INFORMATION (cannot scale on incomplete data).
17. SCALE Guardrail: Rejected when readiness is NOT_READY (cannot scale with deficits or material risks).
18. PIVOT Integration: Creates a NEW Wave 4 validation workspace and hypothesis without overwriting old.
19. HOLD and STOP Decisions: Workspace transitions to PAUSED and STOPPED while preserving history.
20. FIX Decision: Automatically generates remediation action items.
21. Growth Actions: Lifecycle tracking, status transitions, and completed_at timestamping.
22. Ownership Isolation: Cross-user 403 boundaries for growth workspaces and studies.
23. Cross-Workspace Rejection: Scenario from Workspace A cannot be used in Workspace B What-If.
24. Cross-Workspace Rejection: Decision from Workspace A cannot be linked to Action in Workspace B.
25. Persistence: State persists across fresh sessions and queries.
26. End-to-End Lifecycle: Actuals -> Health -> Trends -> Unit Econ -> Risks -> What-If -> Readiness -> Decision -> Actions.
"""
from __future__ import annotations

import os
import tempfile
import uuid
import pytest

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

from fastapi.testclient import TestClient

from app import db as app_db
from app import models
from app.main import app
from app.services.growth import (
    HEALTH_HEALTHY,
    HEALTH_WATCH,
    HEALTH_AT_RISK,
    HEALTH_INSUFFICIENT_DATA,
    TREND_IMPROVING,
    TREND_STABLE,
    TREND_DETERIORATING,
    TREND_INSUFFICIENT_DATA,
    READINESS_READY,
    READINESS_CONDITIONALLY_READY,
    READINESS_NOT_READY,
    READINESS_NEEDS_INFO,
    DECISION_SCALE,
    DECISION_FIX,
    DECISION_PIVOT,
    DECISION_HOLD,
    DECISION_STOP,
    DECISION_NEEDS_INFO,
    PREREQ_PASS,
    PREREQ_FAIL,
    PREREQ_UNKNOWN,
)

client = TestClient(app)
PASSWORD = "Sup3rSecretPassword123!"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def _email(prefix="growth"):
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(prefix="founder"):
    email = _email(prefix)
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return email, tok


def _create_project_and_study(tok: str, title="مشروع نمو تجريبي", investment=350000.0, monthly_projections=None):
    headers = _auth(tok)
    r_p = client.post("/projects/", json={"name": title, "industry": "food_beverage", "investment": investment}, headers=headers)
    assert r_p.status_code == 201, r_p.text
    project_id = r_p.json()["id"]

    study_payload = {
        "project_id": project_id,
        "title": f"دراسة: {title}",
        "industry": "food_beverage",
        "investment": investment,
    }
    r_s = client.post("/feasibility/", json=study_payload, headers=headers)
    assert r_s.status_code == 201, r_s.text
    study_id = r_s.json()["id"]

    if monthly_projections:
        r_step = client.patch(
            f"/feasibility/{study_id}/step",
            json={"step": 4, "data": {"monthly_projections": monthly_projections}},
            headers=headers,
        )
        assert r_step.status_code == 200, r_step.text

    return project_id, study_id


def _setup_launch_ready_study(tok: str):
    """Sets up a study with Wave 4 GO decision and initialized launch workspace."""
    headers = _auth(tok)
    pid, sid = _create_project_and_study(tok, title="مشروع جاهز للنمو")

    val_ws = client.get(f"/api/v1/validation/study/{sid}", headers=headers).json()
    for h in val_ws["hypotheses"]:
        if h.get("importance") == "CRITICAL":
            client.post(
                f"/api/v1/validation/workspaces/{val_ws['id']}/evidence",
                json={
                    "evidence_type": "INTERVIEW",
                    "title": f"دليل ميداني مثبت للفرضية {h['id']}",
                    "hypothesis_id": h["id"],
                    "evidence_strength": "STRONG",
                    "evidence_direction": "SUPPORTING",
                    "is_simulated": False,
                },
                headers=headers,
            )

    r_dec = client.post(
        f"/api/v1/validation/workspaces/{val_ws['id']}/decision",
        json={"decision": "GO", "decision_reason": "اعتماد كامل ومثبت بالأدلة"},
        headers=headers,
    )
    assert r_dec.status_code == 201, r_dec.text

    # Initialize launch workspace
    r_launch = client.get(f"/api/v1/launch/workspaces/study/{sid}", headers=headers)
    assert r_launch.status_code == 200, r_launch.text
    launch_ws = r_launch.json()
    return pid, sid, launch_ws["id"]


# ==============================================================================
# TESTS
# ==============================================================================

def test_01_health_insufficient_data_when_no_actuals():
    """Missing actuals yields INSUFFICIENT_DATA, never falsely healthy or at risk."""
    _, tok = _register_and_login("h_nodata")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["business_health"]["health_state"] == HEALTH_INSUFFICIENT_DATA
    assert "لا توجد دورات تشغيلية" in data["business_health"]["health_summary_ar"]
    assert data["actual_periods_count"] == 0


def test_02_missing_data_is_not_poor_performance():
    """Missing individual metric fields does not flag AT_RISK, but returns UNKNOWN/NOT_AVAILABLE."""
    _, tok = _register_and_login("h_missing")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Record actual period with revenue but missing OPEX breakdown and cash balance
    r_act = client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 50000.0,
            # opex fields omitted/null
        },
        headers=headers,
    )
    assert r_act.status_code == 201, r_act.text

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    # Since cash runway is unknown and only 1 period exists, state is WATCH or INSUFFICIENT_DATA, not AT_RISK
    assert res["business_health"]["health_state"] in {HEALTH_WATCH, HEALTH_INSUFFICIENT_DATA}
    assert res["business_health"]["health_state"] != HEALTH_AT_RISK


def test_03_trend_requires_at_least_two_periods():
    """Deterministic trend engine returns INSUFFICIENT_DATA if fewer than 2 periods recorded."""
    _, tok = _register_and_login("trend_min")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # 1 period only
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "actual_revenue": 40000.0},
        headers=headers,
    )

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    assert res["trends"]["periods_analyzed"] == 1
    rev_trend = res["trends"]["metrics"]["actual_revenue"]
    assert rev_trend["direction"] == TREND_INSUFFICIENT_DATA
    assert rev_trend["absolute_change"] is None
    assert rev_trend["percentage_change"] is None


def test_04_trend_zero_denominator_safe():
    """Zero denominator in trend returns None / NOT_AVAILABLE for percentage change without error."""
    _, tok = _register_and_login("trend_zero")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Period 1: 0 revenue, Period 2: 10,000 revenue
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "actual_revenue": 0.0},
        headers=headers,
    )
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 2, "period_label": "2026-M02", "actual_revenue": 10000.0},
        headers=headers,
    )

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    assert res["trends"]["periods_analyzed"] == 2
    rev_trend = res["trends"]["metrics"]["actual_revenue"]
    assert rev_trend["first_value"] == 0.0
    assert rev_trend["latest_value"] == 10000.0
    assert rev_trend["absolute_change"] == 10000.0
    assert rev_trend["percentage_change"] is None  # Safe zero denominator!
    assert rev_trend["direction"] == TREND_IMPROVING


def test_05_trend_evaluation_directions():
    """Evaluates IMPROVING vs DETERIORATING based on metric semantics (higher vs lower is better)."""
    _, tok = _register_and_login("trend_dirs")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Period 1: rev 50k, opex 30k
    # Period 2: rev 70k, opex 45k (revenue improved, but opex deteriorated)
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "actual_revenue": 50000.0, "total_actual_opex": 30000.0},
        headers=headers,
    )
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 2, "period_label": "2026-M02", "actual_revenue": 70000.0, "total_actual_opex": 45000.0},
        headers=headers,
    )

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    rev_trend = res["trends"]["metrics"]["actual_revenue"]
    opex_trend = res["trends"]["metrics"]["total_actual_opex"]

    assert rev_trend["direction"] == TREND_IMPROVING
    assert rev_trend["percentage_change"] == 40.0

    assert opex_trend["direction"] == TREND_DETERIORATING  # OPEX increased by 50%
    assert opex_trend["percentage_change"] == 50.0


def test_06_cac_calculation_strict_semantics():
    """CAC is calculated ONLY when marketing spend AND customer count are both known and > 0."""
    _, tok = _register_and_login("cac_rules")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Case A: marketing spend known, but customers unknown
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "actual_opex_marketing": 10000.0},
        headers=headers,
    )
    res_a = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    cac_a = res_a["unit_economics"]["metrics"]["cac"]
    assert cac_a["is_known"] is False
    assert cac_a["value"] is None
    assert "غير متوفر" in cac_a["note_ar"]

    # Case B: Both marketing spend and acquired customers known
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 2,
            "period_label": "2026-M02",
            "actual_opex_marketing": 12000.0,
            "acquired_customers_count": 400,
        },
        headers=headers,
    )
    res_b = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    cac_b = res_b["unit_economics"]["metrics"]["cac"]
    assert cac_b["is_known"] is True
    assert cac_b["value"] == 30.0  # 12,000 / 400 = 30 SAR


def test_07_unit_economics_exact_metrics():
    """Calculates ticket size, contribution margin, and fixed/variable proportions accurately."""
    _, tok = _register_and_login("unit_econ")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 100000.0,
            "transactions_count": 1000,
            "actual_opex_cogs": 30000.0,
            "actual_opex_salaries": 20000.0,
            "actual_opex_rent": 10000.0,
            "total_actual_opex": 60000.0,
        },
        headers=headers,
    )

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    metrics = res["unit_economics"]["metrics"]

    assert metrics["average_ticket_size"]["value"] == 100.0
    assert metrics["contribution_margin_pct"]["value"] == 70.0  # (100k - 30k COGS) / 100k = 70%
    assert metrics["fixed_cost_proportion_pct"]["value"] == 50.0  # (20k + 10k) / 60k = 50%


def test_08_no_invented_investments_or_funding():
    """Growth funding links to Wave 2 matched programs without creating synthetic funding or cash."""
    _, tok = _register_and_login("growth_funding")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    gf = res["growth_funding"]
    assert gf["context_type"] == "WAVE_2_INTEGRATION"
    assert "التمويل المحتمل ليس سيولة نقدية متاحة" in gf["disclaimer_ar"]
    assert isinstance(gf["wave2_matched_programs"], list)


def test_09_what_if_provenance_separation():
    """What-If simulation model separates ACTUAL, BASELINE, USER_ASSUMPTION, PLATFORM_DERIVED."""
    _, tok = _register_and_login("whatif_prov")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Record actuals to provide authentic baseline inputs
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 100000.0,
            "total_actual_opex": 60000.0,
            "closing_cash_balance": 200000.0,
        },
        headers=headers,
    )

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    res = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/what-if",
        json={
            "scenario_name": "محاكاة فرع جديد",
            "scenario_type": "NEW_BRANCH",
            "target_horizon_months": 12,
            "capex_required": 150000.0,
            "additional_monthly_opex": 20000.0,
            "expected_monthly_revenue_uplift": 35000.0,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    model = res.json()["model"]

    assert model["scenario_name"] == "محاكاة فرع جديد"
    prov = model["provenance"]
    assert prov["actuals_baseline"] == "ACTUAL"
    assert prov["capex_required"] == "USER_ASSUMPTION"
    assert prov["monthly_projections"] == "PLATFORM_DERIVED"
    assert len(model["derived_monthly_projections"]) == 12


def test_10_what_if_payback_and_runway_calculation():
    """Deterministic calculation of cash payback months and minimum cash required."""
    _, tok = _register_and_login("whatif_calc")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Record actuals to provide baseline
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 100000.0,
            "total_actual_opex": 60000.0,
            "closing_cash_balance": 200000.0,
        },
        headers=headers,
    )

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    # capex 120k, uplift 30k/mo, opex 10k/mo -> net +20k/mo -> payback = 6 months
    res = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/what-if",
        json={
            "scenario_name": "توسعة دقيقة",
            "scenario_type": "CAPACITY_EXPANSION",
            "target_horizon_months": 12,
            "capex_required": 120000.0,
            "additional_monthly_opex": 10000.0,
            "expected_monthly_revenue_uplift": 30000.0,
        },
        headers=headers,
    ).json()["model"]

    assert res["estimated_cash_payback_months"] == 6
    assert res["minimum_cash_required"] == 120000.0


def test_11_expansion_readiness_states():
    """Tests expansion readiness states across differing operational conditions."""
    _, tok = _register_and_login("readiness")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Initial state with no actuals: NEEDS_INFORMATION
    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    assert res["expansion_readiness"]["readiness_state"] == READINESS_NEEDS_INFO

    # Add 1 period with high losses -> NOT_READY
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 20000.0,
            "total_actual_opex": 80000.0,
            "closing_cash_balance": 10000.0,  # 10k / 60k burn = 0.16 months runway!
        },
        headers=headers,
    )
    res2 = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    assert res2["expansion_readiness"]["readiness_state"] == READINESS_NOT_READY


def test_12_expansion_readiness_prerequisites_mapping():
    """Verifies that all 5 prerequisites are categorized cleanly (PASS, FAIL, UNKNOWN, NOT_APPLICABLE)."""
    _, tok = _register_and_login("prereqs")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    prereqs = res["expansion_readiness"]["prerequisites"]
    assert len(prereqs) == 5
    codes = {p["code"] for p in prereqs}
    assert codes == {"OPERATING_STABILITY", "RUNWAY_ADEQUACY", "UNIT_ECONOMICS", "CAPACITY_UTILIZATION", "DATA_COMPLETENESS"}
    for p in prereqs:
        assert p["status"] in {PREREQ_PASS, PREREQ_FAIL, PREREQ_UNKNOWN, "NOT_APPLICABLE"}


def test_13_growth_risks_transparent_detection():
    """Detects concrete risks (high fixed cost, runway depletion, etc.)."""
    _, tok = _register_and_login("risks_detect")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Create high fixed costs (> 70% of OPEX)
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 50000.0,
            "actual_opex_salaries": 45000.0,
            "actual_opex_rent": 30000.0,
            "total_actual_opex": 80000.0,
            "closing_cash_balance": 50000.0,
        },
        headers=headers,
    )

    res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    risk_types = [r["risk_type"] for r in res["risks"]]
    assert "FIXED_COST_OVERHANG" in risk_types


def test_14_monthly_business_review_immutable_versioning():
    """Monthly review snapshots are immutable and increment review_version."""
    _, tok = _register_and_login("review_v")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    r1 = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/reviews",
        json={"review_period": "2026-M01", "review_notes": "مراجعة أولى للمشروع"},
        headers=headers,
    )
    assert r1.status_code == 201, r1.text
    rev1 = r1.json()["review"]
    assert rev1["review_version"] == 1

    r2 = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/reviews",
        json={"review_period": "2026-M02", "review_notes": "مراجعة الدورة الثانية"},
        headers=headers,
    )
    assert r2.status_code == 201, r2.text
    rev2 = r2.json()["review"]
    assert rev2["review_version"] == 2


def test_15_strategic_decisions_supported():
    """Strategic decision engine allows recording HOLD and FIX with reasons."""
    _, tok = _register_and_login("dec_supported")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "HOLD", "decision_reason": "التريث حتى اكتمال بيانات الدورة الثانية"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    dec = r.json()["decision"]
    assert dec["decision"] == "HOLD"
    assert dec["decision_version"] == 1


def test_16_scale_decision_guardrail_rejected_when_needs_info():
    """SCALE decision is blocked if prerequisites are in NEEDS_INFORMATION state."""
    _, tok = _register_and_login("scale_noinfo")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]
    scen = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={"name": "سيناريو تجريبي", "scenario_type": "NEW_BRANCH", "capex_required": 50000.0},
        headers=headers,
    ).json()["scenario"]

    # No actuals recorded -> readiness is NEEDS_INFORMATION
    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "SCALE", "growth_scenario_id": scen["id"], "decision_reason": "نرغب في التوسع مباشرة"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "NEEDS_INFORMATION" in r.json()["detail"] or "مجهولة" in r.json()["detail"]


def test_17_scale_decision_guardrail_rejected_when_not_ready():
    """SCALE decision is blocked if prerequisites fail or severe deficit exists."""
    _, tok = _register_and_login("scale_notready")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Record actuals showing high burn and low cash
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 10000.0,
            "total_actual_opex": 90000.0,
            "closing_cash_balance": 15000.0,
        },
        headers=headers,
    )

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]
    scen = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={"name": "سيناريو عجز", "scenario_type": "NEW_BRANCH", "capex_required": 50000.0},
        headers=headers,
    ).json()["scenario"]

    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "SCALE", "growth_scenario_id": scen["id"], "decision_reason": "رغم العجز نرغب بالتوسع"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "لا يمكن اعتماد قرار التوسع" in r.json()["detail"]


def test_18_pivot_decision_creates_new_wave4_validation_workspace():
    """PIVOT decision links to a NEW Wave 4 validation workspace without overwriting old one."""
    _, tok = _register_and_login("pivot_cycle")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={
            "decision": "PIVOT",
            "decision_reason": "النموذج التجاري القديم لم يحقق جدوى ونحتاج لاستهداف قطاع الشركات",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    dec = r.json()["decision"]
    assert dec["decision"] == "PIVOT"
    assert dec["pivot_validation_workspace_id"] is not None

    # Check that new validation workspace exists
    new_val_id = dec["pivot_validation_workspace_id"]
    val_ws = client.get(f"/api/v1/validation/workspaces/{new_val_id}", headers=headers).json()
    assert val_ws["id"] == new_val_id
    assert len(val_ws["hypotheses"]) >= 1
    assert "PIVOT" in val_ws["hypotheses"][0]["statement"]


def test_19_hold_and_stop_decisions():
    """HOLD sets status to PAUSED; STOP sets status to STOPPED while preserving data."""
    _, tok = _register_and_login("hold_stop")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    # HOLD
    r_hold = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "HOLD", "decision_reason": "تثبيت الأداء لمدة شهر"},
        headers=headers,
    )
    assert r_hold.status_code == 201
    ws_after_hold = client.get(f"/api/v1/growth/workspaces/{ws_id}", headers=headers).json()["workspace"]
    assert ws_after_hold["status"] == "PAUSED"

    # STOP
    r_stop = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "STOP", "decision_reason": "إيقاف العمليات لأسباب استراتيجية"},
        headers=headers,
    )
    assert r_stop.status_code == 201
    ws_after_stop = client.get(f"/api/v1/growth/workspaces/{ws_id}", headers=headers).json()["workspace"]
    assert ws_after_stop["status"] == "STOPPED"


def test_20_fix_decision_auto_generates_remediation_actions():
    """FIX decision automatically creates remediation action items in the workspace."""
    _, tok = _register_and_login("fix_actions")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "FIX", "decision_reason": "معالجة التكاليف المتضخمة في بند الرواتب"},
        headers=headers,
    )
    assert r.status_code == 201

    ws_data = client.get(f"/api/v1/growth/workspaces/{ws_id}", headers=headers).json()
    actions = ws_data["actions"]
    assert len(actions) >= 1
    assert any(a["action_type"] == "REMEDIATION" for a in actions)


def test_21_growth_action_lifecycle_and_completion_timestamp():
    """Actions can be created, updated, and toggling COMPLETED sets completed_at."""
    _, tok = _register_and_login("act_lifecycle")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    r_act = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/actions",
        json={
            "title": "مراجعة شروط عقد الإيجار",
            "action_type": "REMEDIATION",
            "category": "OPERATIONS",
        },
        headers=headers,
    )
    assert r_act.status_code == 201
    act = r_act.json()["action"]
    assert act["status"] == "PENDING"
    assert act["completed_at"] is None

    # Transition to COMPLETED
    r_upd = client.patch(
        f"/api/v1/growth/actions/{act['id']}",
        json={"status": "COMPLETED", "notes": "تم تخفيض الإيجار بنسبة 15%"},
        headers=headers,
    )
    assert r_upd.status_code == 200
    upd_act = r_upd.json()["action"]
    assert upd_act["status"] == "COMPLETED"
    assert upd_act["completed_at"] is not None


def test_22_growth_workspace_cross_user_isolation():
    """User B cannot access or mutate User A's Growth workspace (403 Forbidden)."""
    _, tok_a = _register_and_login("user_a")
    _, tok_b = _register_and_login("user_b")

    pid_a, sid_a, _ = _setup_launch_ready_study(tok_a)
    ws_a = client.get(f"/api/v1/growth/study/{sid_a}", headers=_auth(tok_a)).json()["workspace"]

    # User B attempts to access User A's study growth
    r1 = client.get(f"/api/v1/growth/study/{sid_a}", headers=_auth(tok_b))
    assert r1.status_code == 403, r1.text

    # User B attempts to access User A's workspace by id
    r2 = client.get(f"/api/v1/growth/workspaces/{ws_a['id']}", headers=_auth(tok_b))
    assert r2.status_code == 403, r2.text

    # User B attempts to add scenario to User A's workspace
    r3 = client.post(
        f"/api/v1/growth/workspaces/{ws_a['id']}/scenarios",
        json={"name": "قرصنة", "scenario_type": "OTHER"},
        headers=_auth(tok_b),
    )
    assert r3.status_code == 403, r3.text


def test_23_cross_workspace_scenario_rejection():
    """Scenario from Workspace A cannot be run in Workspace B (returns 400)."""
    _, tok = _register_and_login("cross_scen")
    pid_a, sid_a, _ = _setup_launch_ready_study(tok)
    pid_b, sid_b, _ = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_a = client.get(f"/api/v1/growth/study/{sid_a}", headers=headers).json()["workspace"]["id"]
    ws_b = client.get(f"/api/v1/growth/study/{sid_b}", headers=headers).json()["workspace"]["id"]

    # Create scenario in Workspace A
    scen_a = client.post(
        f"/api/v1/growth/workspaces/{ws_a}/scenarios",
        json={"name": "سيناريو A", "scenario_type": "NEW_BRANCH"},
        headers=headers,
    ).json()["scenario"]

    # Run what-if in Workspace B referencing scenario_id from A
    r = client.post(
        f"/api/v1/growth/workspaces/{ws_b}/what-if",
        json={"scenario_id": scen_a["id"], "scenario_name": "محاولة ربط خاطئة"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "belongs to a different workspace" in r.json()["detail"]


def test_24_cross_workspace_decision_action_rejection():
    """Decision from Workspace A cannot be attached to Action in Workspace B (returns 400)."""
    _, tok = _register_and_login("cross_dec")
    pid_a, sid_a, _ = _setup_launch_ready_study(tok)
    pid_b, sid_b, _ = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_a = client.get(f"/api/v1/growth/study/{sid_a}", headers=headers).json()["workspace"]["id"]
    ws_b = client.get(f"/api/v1/growth/study/{sid_b}", headers=headers).json()["workspace"]["id"]

    # Decision in Workspace A
    dec_a = client.post(
        f"/api/v1/growth/workspaces/{ws_a}/decisions",
        json={"decision": "HOLD", "decision_reason": "قرار في A"},
        headers=headers,
    ).json()["decision"]

    # Action in Workspace B pointing to dec_a
    r = client.post(
        f"/api/v1/growth/workspaces/{ws_b}/actions",
        json={"title": "إجراء غير شرعي", "decision_id": dec_a["id"]},
        headers=headers,
    )
    assert r.status_code == 400
    assert "does not belong to this workspace" in r.json()["detail"]


def test_25_persistence_across_sessions():
    """Growth workspace entities persist across fresh logins and queries."""
    email, tok1 = _register_and_login("persist_user")
    pid, sid, launch_id = _setup_launch_ready_study(tok1)
    headers1 = _auth(tok1)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers1).json()["workspace"]["id"]

    # Add scenario and action
    client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={"name": "سيناريو دائم", "scenario_type": "DIGITAL_TRANSFORMATION"},
        headers=headers1,
    )
    client.post(
        f"/api/v1/growth/workspaces/{ws_id}/actions",
        json={"title": "إطلاق المتجر الإلكتروني", "action_type": "EXPANSION"},
        headers=headers1,
    )

    # Fresh login
    tok2 = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    headers2 = _auth(tok2)

    fresh_data = client.get(f"/api/v1/growth/workspaces/{ws_id}", headers=headers2).json()
    assert len(fresh_data["scenarios"]) == 1
    assert fresh_data["scenarios"][0]["name"] == "سيناريو دائم"
    assert len(fresh_data["actions"]) == 1
    assert fresh_data["actions"][0]["title"] == "إطلاق المتجر الإلكتروني"


def test_26_end_to_end_growth_lifecycle():
    """Comprehensive E2E test covering the complete Growth OS lifecycle:
    ACTUALS -> HEALTH -> TRENDS -> UNIT ECON -> RISKS -> WHAT-IF -> READINESS -> FUNDING -> DECISION -> ACTIONS
    """
    _, tok = _register_and_login("growth_e2e")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # 1. Record two actual periods with positive economics
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 80000.0,
            "transactions_count": 800,
            "actual_opex_cogs": 24000.0,
            "actual_opex_salaries": 20000.0,
            "actual_opex_rent": 10000.0,
            "actual_opex_marketing": 6000.0,
            "acquired_customers_count": 200,
            "total_actual_opex": 60000.0,
            "closing_cash_balance": 200000.0,
        },
        headers=headers,
    )
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 2,
            "period_label": "2026-M02",
            "actual_revenue": 100000.0,
            "transactions_count": 1000,
            "actual_opex_cogs": 30000.0,
            "actual_opex_salaries": 20000.0,
            "actual_opex_rent": 10000.0,
            "actual_opex_marketing": 8000.0,
            "acquired_customers_count": 250,
            "total_actual_opex": 68000.0,
            "closing_cash_balance": 232000.0,
        },
        headers=headers,
    )

    # 2. Query Growth OS full data
    g_data = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()

    # Verify Health: Healthy with positive margin and ample runway
    assert g_data["business_health"]["health_state"] == HEALTH_HEALTHY

    # Verify Trends: Revenue improving (+25%)
    assert g_data["trends"]["metrics"]["actual_revenue"]["direction"] == TREND_IMPROVING
    assert g_data["trends"]["metrics"]["actual_revenue"]["percentage_change"] == 25.0

    # Verify Unit Economics: CAC = 8,000 / 250 = 32 SAR, Ticket = 100 SAR
    assert g_data["unit_economics"]["metrics"]["cac"]["value"] == 32.0
    assert g_data["unit_economics"]["metrics"]["average_ticket_size"]["value"] == 100.0

    # Verify Funding: Wave 2 context present
    assert g_data["growth_funding"]["context_type"] == "WAVE_2_INTEGRATION"

    # 3. Run What-If Simulation
    ws_id = g_data["workspace"]["id"]
    sim = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/what-if",
        json={
            "scenario_name": "توسع فرع ثانٍ",
            "scenario_type": "NEW_BRANCH",
            "target_horizon_months": 12,
            "capex_required": 100000.0,
            "additional_monthly_opex": 15000.0,
            "expected_monthly_revenue_uplift": 40000.0,
        },
        headers=headers,
    ).json()["model"]
    assert sim["estimated_cash_payback_months"] == 4

    # 4. Create scenario and record Strategic Decision (SCALE succeeds because health is HEALTHY and runway is solid)
    scen = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={
            "name": "توسع فرع ثانٍ",
            "scenario_type": "NEW_BRANCH",
            "capex_required": 100000.0,
            "additional_monthly_opex": 15000.0,
            "expected_monthly_revenue_uplift": 40000.0,
        },
        headers=headers,
    ).json()["scenario"]

    # Provide confirmed funding assumptions so funding gap is calculated
    session = app_db.SessionLocal()
    try:
        session.add(models.StudyAssumption(study_id=sid, key="owner_contribution", label_en="Owner Contribution", label_ar="مساهمة المالك", origin="USER", value_number=150000.0, is_active=True))
        session.add(models.StudyAssumption(study_id=sid, key="existing_available_facilities", label_en="Existing Available Facilities", label_ar="التسهيلات المتاحة", origin="USER", value_number=50000.0, is_active=True))
        session.commit()
    finally:
        session.close()

    dec_res = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={
            "decision": "SCALE",
            "growth_scenario_id": scen["id"],
            "decision_reason": "تحقيق أرباح مستقرة لشهرين متتاليين وتوفر سيولة تتجاوز 200 ألف ريال",
        },
        headers=headers,
    )
    assert dec_res.status_code == 201, dec_res.text
    dec = dec_res.json()["decision"]
    assert dec["decision"] == "SCALE"
    assert dec["growth_scenario_id"] == scen["id"]

    # 5. Verify Workspace Status is ACTIVE
    ws_final = client.get(f"/api/v1/growth/workspaces/{ws_id}", headers=headers).json()["workspace"]
    assert ws_final["status"] == "ACTIVE"


# ==============================================================================
# 12 FAILURE PATH INTEGRITY TESTS (A through L)
# ==============================================================================

def test_failure_path_a_no_actual_no_baseline_what_if_needs_information():
    """A. no actual + no baseline what-if -> no 100000/60000 -> NEEDS_INFORMATION."""
    _, tok = _register_and_login("whatif_no_base")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]
    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/what-if",
        json={"scenario_name": "محاكاة بدون بيانات", "target_horizon_months": 6},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    m = r.json()["model"]
    # No synthetic defaults 100000 or 60000
    assert m["baseline_inputs"]["base_revenue"] is None
    assert m["baseline_inputs"]["base_opex"] is None
    assert m["derived_outputs"]["status"] == "NEEDS_INFORMATION"
    assert m["derived_outputs"]["simulated_monthly_revenue"] is None
    assert m["derived_outputs"]["simulated_monthly_opex"] is None
    assert m["derived_outputs"]["simulated_net_monthly"] is None


def test_failure_path_b_no_wave2_funding_match_no_fake_matched_program():
    """B. no wave 2 funding match -> no fake MATCHED program."""
    _, tok = _register_and_login("no_fake_match")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    res = client.get(f"/api/v1/growth/study/{sid}/funding-context", headers=headers)
    assert res.status_code == 200, res.text
    ctx = res.json()["funding_context"]

    # Must NOT blindly claim programs are MATCHED without real rules pass
    matched = [p for p in ctx["wave2_matched_programs"] if p["fit_status"] == "MATCH"]
    assert ctx["wave2_matched_programs_count"] == len(matched)
    for p in ctx["wave2_matched_programs"]:
        assert p["fit_status"] in ("MATCH", "POSSIBLE_MATCH", "NEEDS_INFORMATION", "NOT_MATCHED", "NOT_EVALUATED")


def test_failure_path_c_wave2_possible_match_preserved():
    """C. wave 2 POSSIBLE_MATCH preserved as POSSIBLE_MATCH."""
    from app.services.growth import get_growth_funding_context
    from unittest.mock import patch

    session = app_db.SessionLocal()
    try:
        study = session.query(models.FeasibilityStudy).first()
        if not study:
            pytest.skip("No study available")
        mock_eval = {
            "matches_count": 0,
            "possible_matches_count": 1,
            "matches": [
                {
                    "program_id": 999,
                    "program_name_ar": "برنامج ممكن",
                    "overall_match_status": "POSSIBLE_MATCH",
                    "status_reason_ar": "مؤهل مبدئياً",
                }
            ],
        }
        with patch("app.services.growth.evaluate_study_funding_matches", return_value=mock_eval):
            ctx = get_growth_funding_context(study)
            assert len(ctx["wave2_matched_programs"]) == 1
            assert ctx["wave2_matched_programs"][0]["fit_status"] == "POSSIBLE_MATCH"
            assert ctx["wave2_matched_programs_count"] == 0
    finally:
        session.close()


def test_failure_path_d_unknown_cash_funding_gap_not_available():
    """D. unknown cash -> funding gap NOT_AVAILABLE."""
    _, tok = _register_and_login("unknown_cash_gap")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]
    scen = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={"name": "توسع جديد", "scenario_type": "NEW_BRANCH", "capex_required": 150000.0},
        headers=headers,
    ).json()["scenario"]

    # No actuals recorded -> closing_cash_balance is unknown
    res = client.get(f"/api/v1/growth/study/{sid}/funding-context?scenario_id={scen['id']}", headers=headers)
    assert res.status_code == 200, res.text
    ctx = res.json()["funding_context"]
    assert ctx["funding_gap_status"] == "NOT_AVAILABLE"
    assert ctx["funding_gap"]["gap_amount"] is None
    assert "cash_on_hand" in ctx["unknown_components"]


def test_failure_path_e_unknown_confirmed_facility_not_coerced_to_zero():
    """E. unknown confirmed facility -> not coerced to zero."""
    _, tok = _register_and_login("unknown_facility")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    res = client.get(f"/api/v1/growth/study/{sid}/funding-context", headers=headers)
    assert res.status_code == 200, res.text
    ctx = res.json()["funding_context"]
    assert "confirmed_facilities" in ctx["unknown_components"]
    assert ctx["confirmed_funding"]["confirmed_credit_facilities"] is None


def test_failure_path_f_previous_revenue_zero_risk_unknown():
    """F. previous revenue zero -> risk UNKNOWN."""
    _, tok = _register_and_login("prev_rev_zero")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Period 1 with revenue 0.0, Period 2 with revenue 50,000.0
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "actual_revenue": 0.0, "total_actual_opex": 10000.0},
        headers=headers,
    )
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 2, "period_label": "2026-M02", "actual_revenue": 50000.0, "total_actual_opex": 20000.0},
        headers=headers,
    )

    g_res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    rev_risk = next(r for r in g_res["risks"] if r["risk_type"] == "REVENUE_CONTRACTION")
    assert rev_risk["level"] == "UNKNOWN"
    assert rev_risk["input_value"] is None


def test_failure_path_g_missing_fixed_cost_inputs_risk_unknown():
    """G. missing fixed-cost inputs -> risk UNKNOWN."""
    _, tok = _register_and_login("missing_fixed_cost")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Missing salaries or rent
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "actual_revenue": 50000.0, "total_actual_opex": 30000.0, "actual_opex_salaries": None, "actual_opex_rent": None},
        headers=headers,
    )

    g_res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    cost_risk = next(r for r in g_res["risks"] if r["risk_type"] == "FIXED_COST_OVERHANG")
    assert cost_risk["level"] == "UNKNOWN"


def test_failure_path_h_cash_and_opex_without_valid_burn_runway_not_available():
    """H. cash + OPEX without valid burn -> runway NOT_AVAILABLE."""
    _, tok = _register_and_login("runway_noburn")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Cash and OPEX exist, but net_cashflow is None (cannot determine burn)
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "closing_cash_balance": 100000.0, "total_actual_opex": 50000.0, "actual_revenue": None},
        headers=headers,
    )

    g_res = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()
    cash_risk = next(r for r in g_res["risks"] if r["risk_type"] == "CASH_RUNWAY_DEPLETION")
    assert cash_risk["level"] == "UNKNOWN"
    assert cash_risk["input_value"] is None
    assert cash_risk.get("status") == "NOT_AVAILABLE"


def test_failure_path_i_scale_without_scenario_rejected():
    """I. SCALE without scenario -> REJECT."""
    _, tok = _register_and_login("scale_no_scen")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)
    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "SCALE", "decision_reason": "محاولة توسع بدون سيناريو"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "سيناريو نمو معتمد" in r.json()["detail"]


def test_failure_path_j_scale_with_foreign_workspace_scenario_rejected():
    """J. SCALE with foreign-workspace scenario -> REJECT."""
    _, tok1 = _register_and_login("scale_user1")
    pid1, sid1, launch_id1 = _setup_launch_ready_study(tok1)
    headers1 = _auth(tok1)
    ws1 = client.get(f"/api/v1/growth/study/{sid1}", headers=headers1).json()["workspace"]["id"]
    scen1 = client.post(
        f"/api/v1/growth/workspaces/{ws1}/scenarios",
        json={"name": "سيناريو مساحة 1", "scenario_type": "NEW_BRANCH", "capex_required": 50000.0},
        headers=headers1,
    ).json()["scenario"]

    # User 2 creates study
    _, tok2 = _register_and_login("scale_user2")
    pid2, sid2, launch_id2 = _setup_launch_ready_study(tok2)
    headers2 = _auth(tok2)
    ws2 = client.get(f"/api/v1/growth/study/{sid2}", headers=headers2).json()["workspace"]["id"]

    # Attempt to scale User 2's workspace using User 1's scenario
    r = client.post(
        f"/api/v1/growth/workspaces/{ws2}/decisions",
        json={"decision": "SCALE", "growth_scenario_id": scen1["id"], "decision_reason": "محاولة استخدام سيناريو مساحة أخرى"},
        headers=headers2,
    )
    assert r.status_code == 400, r.text
    assert "لا ينتمي إلى نفس مساحة عمل النمو" in r.json()["detail"]


def test_failure_path_k_scale_with_unknown_investment_requirement_rejected():
    """K. SCALE with unknown investment requirement -> REJECT."""
    _, tok = _register_and_login("scale_no_capex")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)
    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]

    # Create scenario with NO investment_required (capex_required = None)
    scen = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={"name": "سيناريو بدون تكلفة", "scenario_type": "CUSTOM", "capex_required": None},
        headers=headers,
    ).json()["scenario"]

    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={"decision": "SCALE", "growth_scenario_id": scen["id"], "decision_reason": "محاولة توسع بدون ميزانية استثمار"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "متطلبات الاستثمار" in r.json()["detail"] or "capex" in r.json()["detail"]


def test_failure_path_l_scale_with_valid_scenario_and_readiness_permitted():
    """L. valid same-workspace scenario + known requirement + valid readiness -> SCALE permitted."""
    _, tok = _register_and_login("scale_permitted")
    pid, sid, launch_id = _setup_launch_ready_study(tok)
    headers = _auth(tok)

    # Record 2 healthy actual periods with solid cash and revenue
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 1,
            "period_label": "2026-M01",
            "actual_revenue": 80000.0,
            "total_actual_opex": 40000.0,
            "actual_opex_salaries": 15000.0,
            "actual_opex_rent": 5000.0,
            "closing_cash_balance": 180000.0,
            "net_cashflow": 40000.0,
        },
        headers=headers,
    )
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={
            "period_order": 2,
            "period_label": "2026-M02",
            "actual_revenue": 100000.0,
            "total_actual_opex": 45000.0,
            "actual_opex_salaries": 15000.0,
            "actual_opex_rent": 5000.0,
            "closing_cash_balance": 235000.0,
            "net_cashflow": 55000.0,
        },
        headers=headers,
    )

    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]
    scen = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={"name": "توسع مستوفي الشروط", "scenario_type": "NEW_BRANCH", "capex_required": 120000.0},
        headers=headers,
    ).json()["scenario"]

    # Also make sure assumptions have confirmed facilities or owner equity so funding gap is calculated
    session = app_db.SessionLocal()
    try:
        session.add(models.StudyAssumption(study_id=sid, key="owner_contribution", label_en="Owner Contribution", label_ar="مساهمة المالك", origin="USER", value_number=150000.0, is_active=True))
        session.add(models.StudyAssumption(study_id=sid, key="existing_available_facilities", label_en="Existing Available Facilities", label_ar="التسهيلات المتاحة", origin="USER", value_number=50000.0, is_active=True))
        session.commit()
    finally:
        session.close()

    r = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={
            "decision": "SCALE",
            "growth_scenario_id": scen["id"],
            "decision_reason": "تحقيق أرباح مستمرة وسيولة كافية تغطي الاستثمار",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    dec = r.json()["decision"]
    assert dec["decision"] == "SCALE"
    assert dec["growth_scenario_id"] == scen["id"]


def test_capacity_utilization_requires_explicit_evidence():
    """Test 36: CAPACITY_UTILIZATION is not marked PASS merely because actual periods exist.
    Without explicit capacity evidence, returns UNKNOWN / NA as appropriate.
    For capacity-sensitive SCALE scenario (CAPACITY_EXPANSION), unknown capacity remains visible
    and blocks blind scale with NEEDS_INFORMATION.
    """
    _, tok = _register_and_login("caputil")
    headers = _auth(tok)
    pid, sid, launch_id = _setup_launch_ready_study(tok)

    # 2 actual periods recorded, but NO capacity metrics in assumptions or business profile
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 1, "period_label": "2026-M01", "actual_revenue": 50000.0, "total_actual_opex": 30000.0, "closing_cash_balance": 100000.0},
        headers=headers,
    )
    client.post(
        f"/api/v1/launch/workspaces/{launch_id}/actuals",
        json={"period_order": 2, "period_label": "2026-M02", "actual_revenue": 60000.0, "total_actual_opex": 32000.0, "closing_cash_balance": 120000.0},
        headers=headers,
    )

    # Check readiness without scenario: capacity_utilization must be UNKNOWN, NOT PASS
    r = client.get(f"/api/v1/growth/study/{sid}", headers=headers)
    assert r.status_code == 200
    expansion_readiness = r.json()["expansion_readiness"]
    prereqs = {p["code"]: p["status"] for p in expansion_readiness["prerequisites"]}
    prereqs_reasons = {p["code"]: p["reason_ar"] for p in expansion_readiness["prerequisites"]}
    assert prereqs["CAPACITY_UTILIZATION"] == "UNKNOWN", f"Expected UNKNOWN, got {prereqs['CAPACITY_UTILIZATION']}"
    assert "استغلال الطاقة الاستيعابية" in prereqs_reasons["CAPACITY_UTILIZATION"] or "UNKNOWN" in prereqs_reasons["CAPACITY_UTILIZATION"]

    ws_id = r.json()["workspace"]["id"]

    # Scenario: CAPACITY_EXPANSION (explicitly capacity-sensitive)
    scen = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/scenarios",
        json={"name": "توسع طاقة إنتاجية", "scenario_type": "CAPACITY_EXPANSION", "capex_required": 50000.0},
        headers=headers,
    ).json()["scenario"]

    # Trying to SCALE with CAPACITY_EXPANSION without capacity evidence must be rejected (NEEDS_INFORMATION)
    r_scale = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={
            "decision": "SCALE",
            "growth_scenario_id": scen["id"],
            "decision_reason": "محاولة توسع طاقة دون بيانات سعة",
        },
        headers=headers,
    )
    assert r_scale.status_code == 400
    assert "لا يمكن اعتماد قرار التوسع" in r_scale.json()["detail"] or "NEEDS_INFORMATION" in r_scale.json()["detail"]

    # Now add explicit capacity utilization assumption
    session = app_db.SessionLocal()
    try:
        session.add(models.StudyAssumption(
            study_id=sid,
            key="capacity_utilization",
            label_en="Capacity Utilization",
            label_ar="نسبة استغلال الطاقة",
            origin="USER",
            value_number=88.5,
            is_active=True,
        ))
        session.commit()
    finally:
        session.close()

    # With explicit capacity utilization, prerequisite is now PASS
    r_ready = client.get(f"/api/v1/growth/study/{sid}", headers=headers)
    assert r_ready.status_code == 200
    prereqs2 = {p["code"]: p["status"] for p in r_ready.json()["expansion_readiness"]["prerequisites"]}
    assert prereqs2["CAPACITY_UTILIZATION"] == "PASS"


def test_pivot_current_validation_cycle_and_history_preserved():
    """Test 37: PIVOT decision creates a new active validation cycle.
    - Default GET returns the latest (new) cycle as current.
    - Old validation history remains preserved and retrievable by workspace ID.
    - Cycle numbers and metadata are accurate.
    - Wave 4 launch gating continues to recognize approved historical GO.
    """
    _, tok = _register_and_login("pivotcycle")
    headers = _auth(tok)
    pid, sid, launch_id = _setup_launch_ready_study(tok)

    # 1. Get initial validation workspace (Cycle 1)
    r_v1 = client.get(f"/api/v1/validation/study/{sid}", headers=headers)
    assert r_v1.status_code == 200
    w1 = r_v1.json()
    w1_id = w1["id"]
    assert w1["cycle_number"] == 1
    assert w1["is_current_cycle"] is True

    # Record GO decision in Cycle 1
    client.post(
        f"/api/v1/validation/workspaces/{w1_id}/decision",
        json={"decision": "GO", "decision_reason": "تم التحقق الميداني بنجاح للدورة الأولى"},
        headers=headers,
    )

    # 2. In Growth OS, record a PIVOT strategic decision
    ws_id = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]["id"]
    r_piv = client.post(
        f"/api/v1/growth/workspaces/{ws_id}/decisions",
        json={
            "decision": "PIVOT",
            "decision_reason": "تغيير نموذج العمل بعد اختبارات ميدانية جديدة",
        },
        headers=headers,
    )
    assert r_piv.status_code == 201
    piv_data = r_piv.json()["decision"]
    new_cycle_wid = piv_data.get("pivot_validation_workspace_id")
    assert new_cycle_wid is not None
    assert new_cycle_wid != w1_id

    # 3. Query current validation workspace: MUST return new cycle (Cycle 2)
    r_v2 = client.get(f"/api/v1/validation/study/{sid}", headers=headers)
    assert r_v2.status_code == 200
    w2 = r_v2.json()
    assert w2["id"] == new_cycle_wid
    assert w2["cycle_number"] == 2
    assert w2["total_cycles"] == 2
    assert w2["is_current_cycle"] is True
    assert w1_id in w2["historical_cycle_ids"]

    # 4. Old validation cycle 1 must STILL be retrievable by workspace ID
    r_old = client.get(f"/api/v1/validation/workspaces/{w1_id}", headers=headers)
    assert r_old.status_code == 200
    old_data = r_old.json()
    assert old_data["id"] == w1_id
    assert old_data["cycle_number"] == 1
    assert old_data["is_current_cycle"] is False
    assert old_data["latest_decision"]["decision"] == "GO"

    # 5. Cycles listing endpoint returns both cycles in order
    r_cycles = client.get(f"/api/v1/validation/study/{sid}/cycles", headers=headers)
    assert r_cycles.status_code == 200
    cycles = r_cycles.json()["cycles"]
    assert len(cycles) == 2
    assert cycles[0]["cycle_number"] == 2 and cycles[0]["is_current"] is True
    assert cycles[1]["cycle_number"] == 1 and cycles[1]["is_current"] is False

    # 6. Launch gating check: Wave 4 launch workspace still honors the approved GO from cycle 1
    r_launch = client.get(f"/api/v1/launch/workspaces/study/{sid}", headers=headers)
    assert r_launch.status_code == 200


def test_current_validation_cycle_authoritative_for_launch_gate():
    """Test 38: Regression test - Current validation cycle is authoritative for launch workspace creation.
    - Cycle 1 = GO
    - Growth PIVOT creates Cycle 2
    - Cycle 2 has no GO yet
    - creating LaunchWorkspace MUST FAIL (historical Cycle 1 GO does not override)
    - Cycle 2 obtains GO
    - LaunchWorkspace creation PASS.
    """
    _, tok = _register_and_login("curgate")
    headers = _auth(tok)
    pid, sid = _create_project_and_study(tok, title="مشروع اختبار بوابة الإطلاق")

    # Cycle 1: Submit evidence and record GO
    r_v1 = client.get(f"/api/v1/validation/study/{sid}", headers=headers)
    assert r_v1.status_code == 200
    v1_data = r_v1.json()
    for h in v1_data.get("hypotheses", []):
        if h.get("importance") == "CRITICAL":
            client.post(
                f"/api/v1/validation/workspaces/{v1_data['id']}/evidence",
                json={
                    "evidence_type": "INTERVIEW",
                    "title": f"دليل تحقق للدورة 1 فرضية {h['id']}",
                    "hypothesis_id": h["id"],
                    "evidence_strength": "STRONG",
                    "evidence_direction": "SUPPORTING",
                    "is_simulated": False,
                },
                headers=headers,
            )
    r_dec1 = client.post(
        f"/api/v1/validation/workspaces/{v1_data['id']}/decision",
        json={"decision": "GO", "decision_reason": "اعتماد الدورة الأولى"},
        headers=headers,
    )
    assert r_dec1.status_code == 201

    # Growth PIVOT creates Cycle 2
    growth_ws = client.get(f"/api/v1/growth/study/{sid}", headers=headers).json()["workspace"]
    r_piv = client.post(
        f"/api/v1/growth/workspaces/{growth_ws['id']}/decisions",
        json={
            "decision": "PIVOT",
            "decision_reason": "تحول استراتيجي يتطلب دورة تحقق جديدة",
        },
        headers=headers,
    )
    assert r_piv.status_code == 201
    cycle2_id = r_piv.json()["decision"]["pivot_validation_workspace_id"]
    assert cycle2_id is not None

    # Verify Cycle 2 is active and has no decision
    r_v2 = client.get(f"/api/v1/validation/study/{sid}", headers=headers)
    assert r_v2.status_code == 200
    v2_data = r_v2.json()
    assert v2_data["id"] == cycle2_id
    assert v2_data["cycle_number"] == 2
    assert len(v2_data.get("decisions", [])) == 0

    # Creating LaunchWorkspace MUST FAIL: historical GO from Cycle 1 must NOT override
    r_launch_fail = client.get(f"/api/v1/launch/workspaces/study/{sid}", headers=headers)
    assert r_launch_fail.status_code in (400, 422)
    assert "دورة التحقق الحالية" in r_launch_fail.text or "قرار تحقق ميداني رسمي معتمد" in r_launch_fail.text

    # Cycle 2 now obtains GO
    for h in v2_data.get("hypotheses", []):
        if h.get("importance") == "CRITICAL":
            client.post(
                f"/api/v1/validation/workspaces/{cycle2_id}/evidence",
                json={
                    "evidence_type": "INTERVIEW",
                    "title": f"دليل تحقق للدورة 2 فرضية {h['id']}",
                    "hypothesis_id": h["id"],
                    "evidence_strength": "STRONG",
                    "evidence_direction": "SUPPORTING",
                    "is_simulated": False,
                },
                headers=headers,
            )
    r_dec2 = client.post(
        f"/api/v1/validation/workspaces/{cycle2_id}/decision",
        json={"decision": "GO", "decision_reason": "اعتماد الدورة الثانية بعد التحول"},
        headers=headers,
    )
    assert r_dec2.status_code == 201

    # LaunchWorkspace creation now SUCCEEDS (PASS)
    r_launch_pass = client.get(f"/api/v1/launch/workspaces/study/{sid}", headers=headers)
    assert r_launch_pass.status_code == 200
    assert r_launch_pass.json()["status"] == "PLANNED"



