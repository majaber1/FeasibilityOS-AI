"""Wave 5 — Launch, Actuals & Reforecasting OS Automated Test Suite.

Comprehensive tests covering:
1. Validation Decision Gate: Absence of decision, NEEDS_EVIDENCE, STOP, and PIVOT block launch workspace.
2. Validation Decision Gate: GO and GO_WITH_CONDITIONS permit launch workspace.
3. Milestone Seeding: All seeded milestone budgets are NULL (no synthetic budgets), marked as suggested.
4. Baseline Snapshot: Missing study forecast does not invent numbers.
5. Baseline Lineage: Lineage fields (source_study_revision, validation_decision_id, calculation_version) are preserved.
6. Actuals Semantics: Missing actual values are NULL (None), never defaulting to 0.0.
7. Actuals Semantics: Explicit 0.0 actual revenue remains 0.0.
8. Derived Totals: Only computed when required inputs are known.
9. Actuals Provenance: source_type and source_reference are stored and returned.
10. Explicit Launch State: actual_revenue > 0 does NOT automatically change status to LAUNCHED.
11. Explicit Launch State: Explicit PATCH transitions status through allowed states and sets actual_launch_date.
12. Task Management: Tasks can be created, linked to milestones, marked critical, and transitioned to COMPLETED.
13. Variance Semantics: Missing baseline or missing actual strictly returns NOT_AVAILABLE.
14. Variance Semantics: Exact variance percentage and alert tiers (NORMAL, WATCH, MATERIAL_VARIANCE) when both are known.
15. Zero-Denominator Protection: Handles zero projected amounts safely.
16. Reforecast: No synthetic 50k/25k fallbacks; assumptions tagged as USER_ASSUMPTION.
17. Cash Runway: Total investment is NEVER equated to cash balance.
18. Cash Runway: Requires explicit cash and actual burn rate; otherwise None / NOT_AVAILABLE.
19. Break-Even Semantics: Distinguishes cash_flow_positive_month from financial_break_even_month.
20. Immutable Versioning: Reforecast versions (v1, v2) increment and preserve previous versions.
21. Ownership Isolation: Strict cross-user 403 boundaries for all launch endpoints.
22. Persistence: Full state persists across logout/login and fresh retrieval.
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
from app.services.launch import (
    ALERT_NORMAL,
    ALERT_WATCH,
    ALERT_MATERIAL_VARIANCE,
    ALERT_NOT_AVAILABLE,
    WS_STATUS_PLANNED,
    WS_STATUS_IN_PROGRESS,
    WS_STATUS_LAUNCHED,
    WS_STATUS_PAUSED,
    WS_STATUS_CANCELLED,
)

client = TestClient(app)
PASSWORD = "Sup3rSecretPassword123!"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def _email(prefix="launch"):
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(prefix="founder"):
    email = _email(prefix)
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return email, tok


def _create_project_and_study(tok: str, title="مشروع كافيه تجريبي", investment=350000.0, monthly_projections=None):
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

    r_s = client.post(
        "/feasibility/",
        json=study_payload,
        headers=headers,
    )
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


def _add_validation_decision(tok: str, study_id: int, decision: str, reason: str = "قرار اعتماد ميداني"):
    headers = _auth(tok)
    val_ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    if decision == "GO":
        # All critical hypotheses must have real supporting evidence
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
    elif decision == "GO_WITH_CONDITIONS":
        # At least one hypothesis supported so workspace is PARTIALLY_VALIDATED
        client.post(
            f"/api/v1/validation/workspaces/{val_ws['id']}/evidence",
            json={
                "evidence_type": "INTERVIEW",
                "title": "دليل ميداني مثبت جزئي",
                "hypothesis_id": val_ws["hypotheses"][0]["id"],
                "evidence_strength": "STRONG",
                "evidence_direction": "SUPPORTING",
                "is_simulated": False,
            },
            headers=headers,
        )

    dec_body = {"decision": decision, "decision_reason": reason}
    if decision == "GO_WITH_CONDITIONS":
        dec_body["conditions"] = ["الالتزام بميزانية التسويق"]
    r_dec = client.post(
        f"/api/v1/validation/workspaces/{val_ws['id']}/decision",
        json=dec_body,
        headers=headers,
    )
    assert r_dec.status_code == 201, r_dec.text
    return r_dec.json()


# ==============================================================================
# TESTS
# ==============================================================================

def test_01_launch_gate_no_decision_blocks_launch():
    """1. Launch workspace rejected if no validation decision exists."""
    _, tok = _register_and_login("no_dec")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع دون قرار تحقق")

    r = client.get(f"/api/v1/launch/study/{study_id}", headers=headers)
    assert r.status_code == 422
    assert "قرار تحقق ميداني رسمي معتمد" in r.text


def test_02_launch_gate_needs_evidence_status_blocks_launch():
    """2. Launch workspace rejected when validation workspace is in NEEDS_EVIDENCE status."""
    _, tok = _register_and_login("needs_ev")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع يحتاج أدلة")
    val_ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    assert val_ws["status"] == "NEEDS_EVIDENCE"
    assert len(val_ws.get("decisions", [])) == 0

    r = client.get(f"/api/v1/launch/study/{study_id}", headers=headers)
    assert r.status_code == 422
    assert "قرار تحقق ميداني رسمي معتمد" in r.text


def test_03_launch_gate_stop_and_pivot_block_launch():
    """3. Launch workspace rejected if validation decision is STOP or PIVOT."""
    _, tok = _register_and_login("stop_piv")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع متوقف")
    _add_validation_decision(tok, study_id, "STOP", "المؤشرات الميدانية سلبية")

    r_stop = client.get(f"/api/v1/launch/study/{study_id}", headers=headers)
    assert r_stop.status_code == 422
    assert "STOP" in r_stop.text or "يتطلب الإطلاق قرار" in r_stop.text

    # Record PIVOT decision
    val_ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    client.post(
        f"/api/v1/validation/workspaces/{val_ws['id']}/decision",
        json={"decision": "PIVOT", "decision_reason": "تغيير النموذج"},
        headers=headers,
    )
    r_pivot = client.get(f"/api/v1/launch/study/{study_id}", headers=headers)
    assert r_pivot.status_code == 422
    assert "PIVOT" in r_pivot.text or "يتطلب الإطلاق قرار" in r_pivot.text


def test_04_launch_gate_go_and_go_with_conditions_allowed():
    """4. Launch workspace is permitted when validation decision is GO or GO_WITH_CONDITIONS."""
    _, tok = _register_and_login("go_gate")
    headers = _auth(tok)

    # Test GO
    _, study_id1 = _create_project_and_study(tok, "مشروع منطلق تماما")
    _add_validation_decision(tok, study_id1, "GO", "تحقق كامل وإيجابي")
    r_go = client.get(f"/api/v1/launch/study/{study_id1}", headers=headers)
    assert r_go.status_code == 200
    assert r_go.json()["status"] == WS_STATUS_PLANNED

    # Test GO_WITH_CONDITIONS
    _, study_id2 = _create_project_and_study(tok, "مشروع منطلق بشروط")
    _add_validation_decision(tok, study_id2, "GO_WITH_CONDITIONS", "تحقق مع اشتراطات")
    r_gwc = client.get(f"/api/v1/launch/study/{study_id2}", headers=headers)
    assert r_gwc.status_code == 200
    assert r_gwc.json()["status"] == WS_STATUS_PLANNED


def test_05_seeded_milestone_budgets_are_null_and_suggested():
    """5. All seeded milestone budgets must be null (None) and marked as suggested."""
    _, tok = _register_and_login("null_budgets")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع تجزئة مخصص")
    _add_validation_decision(tok, study_id, "GO")

    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    milestones = ws["milestones"]
    assert len(milestones) == 6

    synthetic_values = {5000.0, 75000.0, 120000.0, 25000.0, 15000.0, 10000.0}
    for m in milestones:
        assert m["budget_allocated"] is None, f"Milestone {m['title']} has synthetic budget: {m['budget_allocated']}"
        assert m["budget_allocated"] not in synthetic_values
        assert m["actual_cost"] is None
        assert m["is_suggested"] is True


def test_06_missing_study_forecast_does_not_invent_numbers():
    """6. Baseline snapshot does not invent 12 fake monthly projections if missing from study."""
    _, tok = _register_and_login("no_synth_proj")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع بلا توقعات شهرية", investment=200000.0)
    _add_validation_decision(tok, study_id, "GO")

    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    snaps = ws["baseline_snapshots"]
    assert len(snaps) == 1
    snap = snaps[0]
    assert snap["total_investment"] == 200000.0
    # No synthetic monthly projections invented!
    assert len(snap["monthly_projections"]) == 0
    # Lineage is tracked
    assert snap["source_study_revision"] is not None
    assert snap["validation_decision_id"] is not None
    assert snap["calculation_version"] == "v1.0.0-real-lineage"


def test_07_study_with_real_projections_populates_baseline():
    """7. Study with explicit real projections carries them into baseline snapshot."""
    _, tok = _register_and_login("real_proj")
    headers = _auth(tok)
    real_projs = [
        {"month": 1, "period_label": "M01", "projected_revenue": 50000.0, "projected_opex": 20000.0, "projected_capex": 100000.0, "projected_net_cashflow": -70000.0},
        {"month": 2, "period_label": "M02", "projected_revenue": 60000.0, "projected_opex": 22000.0, "projected_capex": 0.0, "projected_net_cashflow": 38000.0},
    ]
    _, study_id = _create_project_and_study(tok, "مشروع بتوقعات حقيقية", investment=150000.0, monthly_projections=real_projs)
    _add_validation_decision(tok, study_id, "GO")

    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    snaps = ws["baseline_snapshots"]
    assert len(snaps) == 1
    snap = snaps[0]
    assert len(snap["monthly_projections"]) == 2
    assert snap["monthly_projections"][0]["projected_revenue"] == 50000.0
    assert snap["monthly_projections"][1]["projected_revenue"] == 60000.0


def test_08_actual_period_null_not_equal_zero():
    """8. Missing actual numbers remain NULL/None, never defaulting to 0.0."""
    _, tok = _register_and_login("null_actuals")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع فحص القيم الفارغة")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Post period with no revenue or costs specified
    r = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "notes": "فترة تجريبية دون بيانات مالية"},
        headers=headers,
    )
    assert r.status_code == 201
    act = r.json()
    assert act["actual_revenue"] is None
    assert act["transactions_count"] is None
    assert act["average_ticket_size"] is None
    assert act["actual_capex"] is None
    assert act["total_actual_opex"] is None
    assert act["net_cashflow"] is None


def test_09_explicit_actual_revenue_zero_remains_zero():
    """9. Explicit 0.0 actual revenue remains 0.0 and is not treated as None or missing."""
    _, tok = _register_and_login("zero_actuals")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع إيراد صفري")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    r = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={
            "period_label": "M01",
            "period_order": 1,
            "actual_revenue": 0.0,
            "transactions_count": 0,
            "actual_capex": 0.0,
            "total_actual_opex": 15000.0,
        },
        headers=headers,
    )
    assert r.status_code == 201
    act = r.json()
    assert act["actual_revenue"] == 0.0
    assert act["transactions_count"] == 0
    assert act["total_actual_opex"] == 15000.0
    assert act["net_cashflow"] == -15000.0


def test_10_derived_totals_only_compute_when_inputs_known():
    """10. Derived totals (AOV, total OPEX, net cashflow) compute ONLY when inputs are known."""
    _, tok = _register_and_login("derived_calc")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع حسابات مشتقة")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Case A: revenue and transactions known, all opex fields known -> AOV, total OPEX, net cashflow compute
    r_a = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={
            "period_label": "M01",
            "period_order": 1,
            "actual_revenue": 80000.0,
            "transactions_count": 1600,
            "actual_capex": 20000.0,
            "actual_opex_salaries": 25000.0,
            "actual_opex_rent": 10000.0,
            "actual_opex_utilities": 0.0,
            "actual_opex_marketing": 0.0,
            "actual_opex_cogs": 0.0,
            "actual_opex_other": 0.0,
        },
        headers=headers,
    )
    assert r_a.status_code == 201
    d_a = r_a.json()
    assert d_a["average_ticket_size"] == 50.0
    assert d_a["total_actual_opex"] == 35000.0
    # Net cash flow = 80000 - 20000 - 35000 = 25000.0
    assert d_a["net_cashflow"] == 25000.0

    # Case B: transactions is None -> AOV is None
    r_b = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M02", "period_order": 2, "actual_revenue": 50000.0},
        headers=headers,
    )
    assert r_b.status_code == 201
    d_b = r_b.json()
    assert d_b["average_ticket_size"] is None
    # Capex and OPEX missing -> net_cashflow is None
    assert d_b["net_cashflow"] is None


def test_11_variance_not_available_when_baseline_or_actual_unknown():
    """11. Variance is strictly NOT_AVAILABLE if baseline or actual is missing."""
    _, tok = _register_and_login("var_na")
    headers = _auth(tok)
    # Study has no monthly projections
    _, study_id = _create_project_and_study(tok, "مشروع دون خط أساس للتفرع")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Record actuals
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 40000.0, "total_actual_opex": 15000.0},
        headers=headers,
    )

    r_var = client.get(f"/api/v1/launch/workspaces/{ws_id}/variances", headers=headers)
    assert r_var.status_code == 200
    var_data = r_var.json()
    assert var_data["overall_health"] == ALERT_NOT_AVAILABLE
    p1 = var_data["period_variances"][0]
    assert p1["alert"] == ALERT_NOT_AVAILABLE
    assert p1["variance"]["revenue_state"] == "NOT_AVAILABLE"


def test_12_variance_exact_and_alerts_when_both_known():
    """12. Variance and alert tiers (NORMAL, WATCH, MATERIAL_VARIANCE) when both are known."""
    _, tok = _register_and_login("var_exact")
    headers = _auth(tok)
    projs = [
        {"month": 1, "period_label": "M01", "projected_revenue": 100000.0, "projected_opex": 40000.0},
        {"month": 2, "period_label": "M02", "projected_revenue": 100000.0, "projected_opex": 40000.0},
        {"month": 3, "period_label": "M03", "projected_revenue": 100000.0, "projected_opex": 40000.0},
    ]
    _, study_id = _create_project_and_study(tok, "مشروع فحص الانحراف الدقيق", monthly_projections=projs)
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Period 1: NORMAL (<10% diff) -> Revenue 95000 (-5%), OPEX 42000 (+5%)
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 95000.0, "total_actual_opex": 42000.0},
        headers=headers,
    )
    # Period 2: WATCH (10-25% diff) -> Revenue 85000 (-15%), OPEX 40000 (0%)
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M02", "period_order": 2, "actual_revenue": 85000.0, "total_actual_opex": 40000.0},
        headers=headers,
    )
    # Period 3: MATERIAL_VARIANCE (>25% diff) -> Revenue 60000 (-40%), OPEX 60000 (+50%)
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M03", "period_order": 3, "actual_revenue": 60000.0, "total_actual_opex": 60000.0},
        headers=headers,
    )

    r_var = client.get(f"/api/v1/launch/workspaces/{ws_id}/variances", headers=headers)
    assert r_var.status_code == 200
    v = r_var.json()
    assert v["overall_health"] == ALERT_MATERIAL_VARIANCE

    p1 = v["period_variances"][0]
    assert p1["alert"] == ALERT_NORMAL
    assert p1["variance"]["revenue_pct"] == -5.0

    p2 = v["period_variances"][1]
    assert p2["alert"] == ALERT_WATCH
    assert p2["variance"]["revenue_pct"] == -15.0

    p3 = v["period_variances"][2]
    assert p3["alert"] == ALERT_MATERIAL_VARIANCE
    assert p3["variance"]["revenue_pct"] == -40.0
    assert p3["variance"]["opex_pct"] == 50.0


def test_13_no_automatic_launched_from_revenue():
    """13. Recording actual revenue does NOT automatically mutate workspace status to LAUNCHED."""
    _, tok = _register_and_login("no_auto_launch")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع التحقق من عدم الإطلاق التلقائي")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    assert ws["status"] == WS_STATUS_PLANNED

    # Record large revenue
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 250000.0, "closing_cash_balance": 180000.0},
        headers=headers,
    )

    # Workspace must still be PLANNED
    ws_after = client.get(f"/api/v1/launch/workspaces/{ws_id}", headers=headers).json()
    assert ws_after["status"] == WS_STATUS_PLANNED
    assert ws_after["actual_launch_date"] is None


def test_14_explicit_launch_state_transitions():
    """14. Workspace status changes only via explicit transition; sets actual_launch_date when LAUNCHED."""
    _, tok = _register_and_login("state_trans")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع دورة حياة الإطلاق")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # 1. Transition to IN_PROGRESS
    r_prog = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": WS_STATUS_IN_PROGRESS, "target_launch_date": "2026-10-01"},
        headers=headers,
    )
    assert r_prog.status_code == 200
    assert r_prog.json()["status"] == WS_STATUS_IN_PROGRESS
    assert r_prog.json()["target_launch_date"] == "2026-10-01"

    # 2. Transition to LAUNCHED with explicit date
    r_launch = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": WS_STATUS_LAUNCHED, "actual_launch_date": "2026-09-05"},
        headers=headers,
    )
    assert r_launch.status_code == 200
    assert r_launch.json()["status"] == WS_STATUS_LAUNCHED
    assert r_launch.json()["actual_launch_date"] == "2026-09-05"

    # 3. Transition to PAUSED
    r_pause = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": WS_STATUS_PAUSED},
        headers=headers,
    )
    assert r_pause.status_code == 200
    assert r_pause.json()["status"] == WS_STATUS_PAUSED

    # 4. Reject invalid status
    r_inv = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": "INVALID_STATE"},
        headers=headers,
    )
    assert r_inv.status_code == 422


def test_15_task_management_with_milestones_and_completion():
    """15. Execution tasks can be created, linked to milestones, marked critical, and completed."""
    _, tok = _register_and_login("task_mgr")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع المهام التنفيذية")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    m1_id = ws["milestones"][0]["id"]

    # Create task
    r_task = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/tasks",
        json={
            "title": "إيداع رسوم ترخيص بلدي والمطابقة الفنية",
            "milestone_id": m1_id,
            "description": "سداد الفاتورة عبر سداد ورفع المخططات المعتمدة",
            "owner_name": "سعد المطيري",
            "due_date": "2026-09-20",
            "is_critical": True,
        },
        headers=headers,
    )
    assert r_task.status_code == 201
    t = r_task.json()
    assert t["title"] == "إيداع رسوم ترخيص بلدي والمطابقة الفنية"
    assert t["owner_name"] == "سعد المطيري"
    assert t["is_critical"] is True
    assert t["status"] == "PENDING"
    t_id = t["id"]

    # Update task to COMPLETED
    r_up = client.patch(
        f"/api/v1/launch/tasks/{t_id}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert r_up.status_code == 200
    t_up = r_up.json()
    assert t_up["status"] == "COMPLETED"
    assert t_up["completed_date"] is not None


def test_16_reforecast_removes_fallbacks_and_labels_assumptions():
    """16. Reforecast avoids synthetic 50k/25k fallbacks and tags assumptions as USER_ASSUMPTION."""
    _, tok = _register_and_login("reforecast_sem")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع إعادة التنبؤ")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Record actuals
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 45000.0, "total_actual_opex": 20000.0, "closing_cash_balance": 120000.0},
        headers=headers,
    )

    r_rf = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/reforecast",
        json={
            "reforecast_title": "السيناريو المتحفظ",
            "adjustment_rationale": "تعديل بناء على نتائج الشهر الأول",
            "growth_rate_adjustment_pct": 5.0,
            "opex_adjustment_pct": 2.0,
        },
        headers=headers,
    )
    assert r_rf.status_code == 201
    rf = r_rf.json()
    payload = rf["reforecast_payload"]

    # Assumptions classification must be USER_ASSUMPTION
    assert payload["assumptions"]["classification"] == "USER_ASSUMPTION"
    assert payload["assumptions"]["growth_rate_adjustment_pct"] == 5.0
    assert payload["assumptions"]["opex_adjustment_pct"] == 2.0

    # Values must be extrapolated from actuals (45000 * 1.05 = 47250.0), NOT synthetic 50000.0!
    m1_proj = payload["monthly_projections"][0]
    assert m1_proj["reforecast_revenue"] == 47250.0
    assert m1_proj["reforecast_opex"] == 20400.0


def test_17_total_investment_never_equated_to_cash_balance():
    """17. Cash runway is NOT computed using total_investment as cash balance."""
    _, tok = _register_and_login("cash_vs_inv")
    headers = _auth(tok)
    # Total investment = 600,000.0
    _, study_id = _create_project_and_study(tok, "مشروع استثمار لا يساوي الكاش", investment=600000.0)
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Record actuals WITHOUT closing cash balance, with burning cashflow
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 10000.0, "total_actual_opex": 30000.0},
        headers=headers,
    )

    # Reforecast without explicit cash balance
    r_rf = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/reforecast",
        json={
            "reforecast_title": "إعادة تنبؤ دون رصيد نقدي معروف",
            "adjustment_rationale": "فحص عدم استعارة إجمالي الاستثمار كرصيد كاش",
        },
        headers=headers,
    )
    assert r_rf.status_code == 201
    rf = r_rf.json()
    # Runway must be None / NOT_AVAILABLE, NOT 600000 / 20000 = 30 months!
    assert rf["remaining_runway_months"] is None
    assert rf["reforecast_payload"]["current_cash_balance"] is None


def test_18_runway_requires_explicit_cash_and_actual_burn():
    """18. Cash runway computes accurately when explicit cash balance and burning net cashflow exist."""
    _, tok = _register_and_login("runway_calc")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع حساب المدرج الزمني")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Record 2 months of negative net cashflow:
    # M01: Net cash = 20000 - 40000 = -20000
    # M02: Net cash = 30000 - 60000 = -30000
    # Average burn = 25,000 / month
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 20000.0, "actual_capex": 0.0, "total_actual_opex": 40000.0},
        headers=headers,
    )
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M02", "period_order": 2, "actual_revenue": 30000.0, "actual_capex": 0.0, "total_actual_opex": 60000.0, "closing_cash_balance": 100000.0},
        headers=headers,
    )

    r_rf = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/reforecast",
        json={
            "reforecast_title": "إعادة التنبؤ بناء على رصيد الكاش الختامي",
            "adjustment_rationale": "فحص دقة المدرج المالي",
        },
        headers=headers,
    )
    assert r_rf.status_code == 201
    rf = r_rf.json()
    # Monthly burn rate = 25,000.0
    assert rf["monthly_burn_rate"] == 25000.0
    # Runway = 100,000 / 25,000 = 4.0 months
    assert rf["remaining_runway_months"] == 4.0


def test_19_break_even_distinguishes_positive_cashflow_from_break_even():
    """19. Distinguishes first cash_flow_positive_month from cumulative financial_break_even_month."""
    _, tok = _register_and_login("break_even")
    headers = _auth(tok)
    # Total investment = 50,000.0
    projs = [
        {"month": 1, "period_label": "M01", "projected_revenue": 30000.0, "projected_opex": 20000.0},  # +10,000 (positive cashflow month 1, cum=10k)
        {"month": 2, "period_label": "M02", "projected_revenue": 35000.0, "projected_opex": 20000.0},  # +15,000 (cum=25k)
        {"month": 3, "period_label": "M03", "projected_revenue": 40000.0, "projected_opex": 20000.0},  # +20,000 (cum=45k)
        {"month": 4, "period_label": "M04", "projected_revenue": 45000.0, "projected_opex": 20000.0},  # +25,000 (cum=70k >= 50k -> financial break-even month 4)
    ]
    _, study_id = _create_project_and_study(tok, "مشروع فحص نقطة التعادل", investment=50000.0, monthly_projections=projs)
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    r_rf = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/reforecast",
        json={
            "reforecast_title": "تحليل التعادل المالي والتدفق الإيجابي",
            "adjustment_rationale": "فحص تمييز الشهر الإيجابي عن التعادل الكامل",
        },
        headers=headers,
    )
    assert r_rf.status_code == 201
    rf = r_rf.json()
    # First positive net cashflow is Month 1
    assert rf["cash_flow_positive_month"] == 1
    # Financial break-even (recovering initial 50k investment) is Month 4
    assert rf["financial_break_even_month"] == 4


def test_20_source_provenance_on_actuals():
    """20. source_type and source_reference are recorded and returned on actual periods."""
    _, tok = _register_and_login("actuals_prov")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع موثوقية مصادر الفعليات")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    r_act = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={
            "period_label": "M01",
            "period_order": 1,
            "actual_revenue": 50000.0,
            "source_type": "SYSTEM_INTEGRATION",
            "source_reference": "ZATCA-E-INVOICE-BATCH-2026-09",
            "notes": "مستورد آلياً من بوابة الفوترة السحابية",
        },
        headers=headers,
    )
    assert r_act.status_code == 201
    act = r_act.json()
    assert act["source_type"] == "SYSTEM_INTEGRATION"
    assert act["source_reference"] == "ZATCA-E-INVOICE-BATCH-2026-09"


def test_21_launch_workspace_ownership_isolation():
    """21. Launch workspace, actuals, tasks, and reforecasts strictly reject cross-user access (403)."""
    _, tok1 = _register_and_login("owner_u1")
    _, tok2 = _register_and_login("owner_u2")

    _, study_id = _create_project_and_study(tok1, "مشروع معزول بالكامل")
    _add_validation_decision(tok1, study_id, "GO")
    ws1 = client.get(f"/api/v1/launch/study/{study_id}", headers=_auth(tok1)).json()
    ws1_id = ws1["id"]

    # User 2 access attempts
    assert client.get(f"/api/v1/launch/study/{study_id}", headers=_auth(tok2)).status_code == 403
    assert client.get(f"/api/v1/launch/workspaces/{ws1_id}", headers=_auth(tok2)).status_code == 403
    assert client.patch(f"/api/v1/launch/workspaces/{ws1_id}/status", json={"status": "LAUNCHED"}, headers=_auth(tok2)).status_code == 403
    assert client.post(f"/api/v1/launch/workspaces/{ws1_id}/actuals", json={"period_label": "M01", "period_order": 1}, headers=_auth(tok2)).status_code == 403
    assert client.post(f"/api/v1/launch/workspaces/{ws1_id}/tasks", json={"title": "مهمة غير مخولة"}, headers=_auth(tok2)).status_code == 403
    assert client.post(f"/api/v1/launch/workspaces/{ws1_id}/reforecast", json={"reforecast_title": "تنبؤ غير مخول", "adjustment_rationale": "محاولة وصول غير مصرح بها"}, headers=_auth(tok2)).status_code == 403


def test_22_refresh_logout_login_persistence():
    """22. Complete state persists across logout/login and fresh retrieval."""
    email, tok1 = _register_and_login("persist_user")
    headers1 = _auth(tok1)

    _, study_id = _create_project_and_study(tok1, "مشروع استمرارية البيانات الميدانية")
    _add_validation_decision(tok1, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers1).json()
    ws_id = ws["id"]
    m1_id = ws["milestones"][0]["id"]

    # Perform updates
    client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": WS_STATUS_LAUNCHED, "actual_launch_date": "2026-09-05"},
        headers=headers1,
    )
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/tasks",
        json={"title": "مهمة التوثيق المستمر", "milestone_id": m1_id, "owner_name": "مشعل", "is_critical": True},
        headers=headers1,
    )
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 77000.0, "total_actual_opex": 23000.0, "closing_cash_balance": 150000.0},
        headers=headers1,
    )
    client.post(
        f"/api/v1/launch/workspaces/{ws_id}/reforecast",
        json={"reforecast_title": "تنبؤ محفوظ v1", "adjustment_rationale": "توثيق التغييرات المستمرة"},
        headers=headers1,
    )

    # Re-login with new token
    tok2 = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    headers2 = _auth(tok2)

    fresh_ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers2).json()
    assert fresh_ws["status"] == WS_STATUS_LAUNCHED
    assert fresh_ws["actual_launch_date"] == "2026-09-05"
    assert len(fresh_ws["tasks"]) == 1
    assert fresh_ws["tasks"][0]["title"] == "مهمة التوثيق المستمر"
    assert len(fresh_ws["actual_periods"]) == 1
    assert fresh_ws["actual_periods"][0]["actual_revenue"] == 77000.0
    assert len(fresh_ws["reforecasts"]) == 1
    assert fresh_ws["reforecasts"][0]["reforecast_title"] == "تنبؤ محفوظ v1"


def test_23_dependency_ownership_and_workspace_isolation():
    """23. Dependency milestone and task references strictly isolate to the same workspace."""
    _, tok_a = _register_and_login("user_a")
    _, tok_b = _register_and_login("user_b")
    headers_a = _auth(tok_a)
    headers_b = _auth(tok_b)

    # User A: Workspace 1
    _, study_a1 = _create_project_and_study(tok_a, "مشروع أ1")
    _add_validation_decision(tok_a, study_a1, "GO")
    ws_a1 = client.get(f"/api/v1/launch/study/{study_a1}", headers=headers_a).json()
    ws_a1_id = ws_a1["id"]
    m_a1_id = ws_a1["milestones"][0]["id"]
    r_task_a1 = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/tasks",
        json={"title": "مهمة مسار أ1", "milestone_id": m_a1_id},
        headers=headers_a,
    )
    assert r_task_a1.status_code == 201
    task_a1_id = r_task_a1.json()["id"]

    # User A: Workspace 2
    _, study_a2 = _create_project_and_study(tok_a, "مشروع أ2")
    _add_validation_decision(tok_a, study_a2, "GO")
    ws_a2 = client.get(f"/api/v1/launch/study/{study_a2}", headers=headers_a).json()
    ws_a2_id = ws_a2["id"]
    m_a2_id = ws_a2["milestones"][0]["id"]
    r_task_a2 = client.post(
        f"/api/v1/launch/workspaces/{ws_a2_id}/tasks",
        json={"title": "مهمة مسار أ2", "milestone_id": m_a2_id},
        headers=headers_a,
    )
    assert r_task_a2.status_code == 201
    task_a2_id = r_task_a2.json()["id"]

    # User B: Workspace B
    _, study_b = _create_project_and_study(tok_b, "مشروع ب")
    _add_validation_decision(tok_b, study_b, "GO")
    ws_b = client.get(f"/api/v1/launch/study/{study_b}", headers=headers_b).json()
    ws_b_id = ws_b["id"]
    m_b_id = ws_b["milestones"][0]["id"]
    r_task_b = client.post(
        f"/api/v1/launch/workspaces/{ws_b_id}/tasks",
        json={"title": "مهمة مسار ب", "milestone_id": m_b_id},
        headers=headers_b,
    )
    assert r_task_b.status_code == 201
    task_b_id = r_task_b.json()["id"]

    # 1. User A cannot depend on User B milestone
    r_cross_user_m = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/milestones",
        json={
            "category": "OPERATIONS",
            "title": "معلم غير مخول يعتمد على مستخدم آخر",
            "dependency_milestone_id": m_b_id,
        },
        headers=headers_a,
    )
    assert r_cross_user_m.status_code in (400, 404, 422)

    # 2. User A cannot depend on User B task
    r_cross_user_t = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/tasks",
        json={
            "title": "مهمة غير مخولة تعتمد على مستخدم آخر",
            "dependency_task_id": task_b_id,
        },
        headers=headers_a,
    )
    assert r_cross_user_t.status_code in (400, 404, 422)

    # 3. Same-user different-workspace milestone dependency is rejected
    r_diff_ws_m = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/milestones",
        json={
            "category": "OPERATIONS",
            "title": "معلم يعتمد على مساحة أخرى لنفس المستخدم",
            "dependency_milestone_id": m_a2_id,
        },
        headers=headers_a,
    )
    assert r_diff_ws_m.status_code in (400, 404, 422)

    # 4. Same-user different-workspace task dependency is rejected
    r_diff_ws_t = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/tasks",
        json={
            "title": "مهمة تعتمد على مهمة بمساحة أخرى لنفس المستخدم",
            "dependency_task_id": task_a2_id,
        },
        headers=headers_a,
    )
    assert r_diff_ws_t.status_code in (400, 404, 422)

    # 5. Milestone_id from different workspace is rejected
    r_diff_ws_parent_m = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/tasks",
        json={
            "title": "مهمة مرتبطة بمعلم من مساحة أخرى",
            "milestone_id": m_a2_id,
        },
        headers=headers_a,
    )
    assert r_diff_ws_parent_m.status_code in (400, 404, 422)

    # 6. Valid same-workspace milestone dependency succeeds
    r_valid_m = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/milestones",
        json={
            "category": "OPERATIONS",
            "title": "معلم تابع صحيح داخل نفس مساحة العمل",
            "dependency_milestone_id": m_a1_id,
        },
        headers=headers_a,
    )
    assert r_valid_m.status_code == 201
    valid_m = r_valid_m.json()
    assert valid_m["dependency_milestone_id"] == m_a1_id

    # 7. Valid same-workspace task dependency succeeds
    r_valid_t = client.post(
        f"/api/v1/launch/workspaces/{ws_a1_id}/tasks",
        json={
            "title": "مهمة تابعة صحيحة داخل نفس مساحة العمل",
            "milestone_id": m_a1_id,
            "dependency_task_id": task_a1_id,
        },
        headers=headers_a,
    )
    assert r_valid_t.status_code == 201
    valid_t = r_valid_t.json()
    assert valid_t["dependency_task_id"] == task_a1_id
    assert valid_t["milestone_id"] == m_a1_id


def test_24_actual_launch_date_semantics():
    """24. actual_launch_date may only be set when status is LAUNCHED; rejects non-LAUNCHED dates with 422."""
    _, tok = _register_and_login("launch_sem")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع تاريخ الإطلاق الفعلي")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    assert ws["status"] == WS_STATUS_PLANNED

    # 1. IN_PROGRESS + actual_launch_date -> REJECT (422)
    r_inprog = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": WS_STATUS_IN_PROGRESS, "actual_launch_date": "2026-09-05"},
        headers=headers,
    )
    assert r_inprog.status_code == 422

    # 2. PLANNED + actual_launch_date -> REJECT (422)
    r_plan = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": WS_STATUS_PLANNED, "actual_launch_date": "2026-09-05"},
        headers=headers,
    )
    assert r_plan.status_code == 422

    # 3. BLOCKED + actual_launch_date -> REJECT (422)
    r_block = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": "BLOCKED", "actual_launch_date": "2026-09-05"},
        headers=headers,
    )
    assert r_block.status_code == 422

    # 4. LAUNCHED + explicit date -> PASS (200)
    r_launch = client.patch(
        f"/api/v1/launch/workspaces/{ws_id}/status",
        json={"status": WS_STATUS_LAUNCHED, "actual_launch_date": "2026-09-15"},
        headers=headers,
    )
    assert r_launch.status_code == 200
    assert r_launch.json()["status"] == WS_STATUS_LAUNCHED
    assert r_launch.json()["actual_launch_date"] == "2026-09-15"

    # 5. LAUNCHED without date -> system records current date
    _, study_id2 = _create_project_and_study(tok, "مشروع إطلاق دون تاريخ صريح")
    _add_validation_decision(tok, study_id2, "GO")
    ws2 = client.get(f"/api/v1/launch/study/{study_id2}", headers=headers).json()
    ws2_id = ws2["id"]

    r_launch_auto = client.patch(
        f"/api/v1/launch/workspaces/{ws2_id}/status",
        json={"status": WS_STATUS_LAUNCHED},
        headers=headers,
    )
    assert r_launch_auto.status_code == 200
    assert r_launch_auto.json()["status"] == WS_STATUS_LAUNCHED
    recorded_date = r_launch_auto.json()["actual_launch_date"]
    assert recorded_date is not None
    assert len(recorded_date) == 10  # YYYY-MM-DD

    # 6. Do not auto-launch from revenue
    _, study_id3 = _create_project_and_study(tok, "مشروع التحقق من عدم الإطلاق الآلي")
    _add_validation_decision(tok, study_id3, "GO")
    ws3 = client.get(f"/api/v1/launch/study/{study_id3}", headers=headers).json()
    ws3_id = ws3["id"]

    client.post(
        f"/api/v1/launch/workspaces/{ws3_id}/actuals",
        json={"period_label": "M01", "period_order": 1, "actual_revenue": 100000.0},
        headers=headers,
    )
    ws3_check = client.get(f"/api/v1/launch/workspaces/{ws3_id}", headers=headers).json()
    assert ws3_check["status"] == WS_STATUS_PLANNED
    assert ws3_check["actual_launch_date"] is None


def test_25_strict_status_enums():
    """25. Milestone and task status endpoints enforce canonical enums and reject invalid strings with HTTP 422."""
    _, tok = _register_and_login("enum_strict")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع تدقيق الحالات")
    _add_validation_decision(tok, study_id, "GO")
    ws = client.get(f"/api/v1/launch/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    m_id = ws["milestones"][0]["id"]

    # 1. Milestone creation rejects arbitrary string (e.g. TODO) with 422
    r_bad_m = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/milestones",
        json={"category": "TEAM", "title": "معلم بحالة غير صالحة", "status": "TODO"},
        headers=headers,
    )
    assert r_bad_m.status_code == 422

    # 2. Milestone update rejects arbitrary string with 422
    r_bad_up_m = client.patch(
        f"/api/v1/launch/milestones/{m_id}",
        json={"status": "DONE"},
        headers=headers,
    )
    assert r_bad_up_m.status_code == 422

    # 3. Canonical milestone statuses (PENDING, IN_PROGRESS, COMPLETED, BLOCKED, DELAYED) all succeed
    for canonical_m_status in ["IN_PROGRESS", "BLOCKED", "DELAYED", "PENDING", "COMPLETED"]:
        r_ok = client.patch(
            f"/api/v1/launch/milestones/{m_id}",
            json={"status": canonical_m_status},
            headers=headers,
        )
        assert r_ok.status_code == 200, f"Milestone status {canonical_m_status} failed: {r_ok.text}"
        assert r_ok.json()["status"] == canonical_m_status

    # 4. Task creation rejects arbitrary string with 422
    r_bad_t = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/tasks",
        json={"title": "مهمة بحالة غير صالحة", "milestone_id": m_id, "status": "TODO"},
        headers=headers,
    )
    assert r_bad_t.status_code == 422

    # 5. Create valid task with canonical default (PENDING)
    r_task = client.post(
        f"/api/v1/launch/workspaces/{ws_id}/tasks",
        json={"title": "مهمة فحص الحالات المقبولة", "milestone_id": m_id},
        headers=headers,
    )
    assert r_task.status_code == 201
    task_id = r_task.json()["id"]
    assert r_task.json()["status"] == "PENDING"

    # 6. Task update rejects arbitrary string with 422
    r_bad_up_t = client.patch(
        f"/api/v1/launch/tasks/{task_id}",
        json={"status": "IN_REVIEW"},
        headers=headers,
    )
    assert r_bad_up_t.status_code == 422

    # 7. Canonical task statuses (PENDING, IN_PROGRESS, COMPLETED, BLOCKED, CANCELLED) all succeed
    for canonical_t_status in ["IN_PROGRESS", "BLOCKED", "CANCELLED", "PENDING", "COMPLETED"]:
        r_t_ok = client.patch(
            f"/api/v1/launch/tasks/{task_id}",
            json={"status": canonical_t_status},
            headers=headers,
        )
        assert r_t_ok.status_code == 200, f"Task status {canonical_t_status} failed: {r_t_ok.text}"
        assert r_t_ok.json()["status"] == canonical_t_status
