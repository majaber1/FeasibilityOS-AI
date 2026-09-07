"""Wave 4 — Validation OS Automated Test Suite.

Comprehensive tests covering:
1. Workspace initialization and ownership isolation.
2. Hypothesis lifecycle & strict evidence gate (no fake SUPPORTED without real evidence).
3. Experiment planning and status updates.
4. Customer interview recording and persistence.
5. Survey aggregate derivation with zero-denominator protection.
6. Demand signals and deterministic conversion calculations.
7. Pricing assumptions vs tested pricing.
8. Competitor claims and source URL verification.
9. Simulated AI content isolation (excluded from supporting hypotheses).
10. Transparent coverage calculation with ZERO fake percentage scores.
11. Immutable validation decisions (GO, GO_WITH_CONDITIONS, PIVOT, STOP) with snapshots.
12. Multi-version decision history preservation.
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
from app.services.validation import (
    WS_STATUS_NEEDS_EVIDENCE,
    WS_STATUS_IN_PROGRESS,
    WS_STATUS_PARTIALLY_VALIDATED,
    WS_STATUS_VALIDATED,
    WS_STATUS_NOT_VALIDATED,
    STATUS_NOT_TESTED,
    STATUS_TESTING,
    STATUS_SUPPORTED,
    STATUS_NOT_SUPPORTED,
    DECISION_GO,
    DECISION_GO_WITH_CONDITIONS,
    DECISION_STOP,
    DECISION_PIVOT,
)

client = TestClient(app)
PASSWORD = "Sup3rSecretPassword123!"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def _email(prefix="val"):
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(prefix="founder"):
    email = _email(prefix)
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return email, tok


def _create_project_and_study(tok: str, title="مشروع تجريبي للتحقق"):
    headers = _auth(tok)
    # 1. Create project
    r_p = client.post("/projects/", json={"name": title, "industry": "retail", "investment": 200000.0}, headers=headers)
    assert r_p.status_code == 201, r_p.text
    project_id = r_p.json()["id"]

    # 2. Create study
    r_s = client.post(
        "/feasibility/",
        json={"project_id": project_id, "title": f"دراسة: {title}", "industry": "retail", "investment": 200000.0},
        headers=headers,
    )
    assert r_s.status_code == 201, r_s.text
    study_id = r_s.json()["id"]
    return project_id, study_id


# ==============================================================================
# TESTS
# ==============================================================================

def test_validation_workspace_initialization_and_isolation():
    """Test creating validation workspace for study and verifying user isolation."""
    _, tok1 = _register_and_login("val_user1")
    _, tok2 = _register_and_login("val_user2")

    _, study_id = _create_project_and_study(tok1, "مشروع تجزئة أ")

    # User 1 accesses workspace -> auto-initialized with template hypotheses
    r1 = client.get(f"/api/v1/validation/study/{study_id}", headers=_auth(tok1))
    assert r1.status_code == 200
    data = r1.json()
    assert data["study_id"] == study_id
    assert data["status"] == WS_STATUS_NEEDS_EVIDENCE
    assert len(data["hypotheses"]) >= 3
    ws_id = data["id"]

    # User 2 attempts to access User 1's workspace -> 403 Forbidden
    r2 = client.get(f"/api/v1/validation/study/{study_id}", headers=_auth(tok2))
    assert r2.status_code == 403

    r2_direct = client.get(f"/api/v1/validation/workspaces/{ws_id}", headers=_auth(tok2))
    assert r2_direct.status_code == 403


def test_hypothesis_evidence_gate_prevents_fake_support():
    """Test that a hypothesis cannot be marked SUPPORTED without non-simulated evidence."""
    _, tok = _register_and_login("hypo_gate")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع أطعمة ومشروبات")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    h_id = ws["hypotheses"][0]["id"]

    # Attempt to change to SUPPORTED without any evidence -> 422 rejected!
    r_fail = client.patch(f"/api/v1/validation/hypotheses/{h_id}", json={"status": STATUS_SUPPORTED}, headers=headers)
    assert r_fail.status_code == 422
    assert "أدلة ميدانية" in r_fail.text or "evidence" in r_fail.text.lower()


def test_customer_interview_recording_and_hypothesis_support():
    """Test recording real customer interview evidence and transitioning hypothesis."""
    _, tok = _register_and_login("cust_interview")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "تطبيق خدمات لوجستية")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    h_problem = next(h for h in ws["hypotheses"] if h["hypothesis_type"] == "CUSTOMER_PROBLEM")

    # Record interview
    r_ev = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة ميدانية مع مدير عمليات لوجستية في الرياض",
            "hypothesis_id": h_problem["id"],
            "source_type": "USER_RECORDED",
            "source_owner": "أحمد الشمري - شركة نقليات الرياض",
            "evidence_strength": "STRONG",
            "evidence_direction": "SUPPORTING",
            "is_simulated": False,
            "structured_payload": {
                "segment": "B2B Logistics Operations",
                "interview_date": "2026-09-01",
                "problem_confirmed": True,
                "current_alternative": "جداول Excel واتصالات هاتفية",
                "pain_level": "HIGH",
                "willingness_to_switch": True,
                "price_reaction": "مستعد لدفع 1500 ر.س شهرياً",
                "notes": "العميل أكد خسارة شحنات شهرياً بسبب تأخر التتبع اليدوي.",
            },
        },
        headers=headers,
    )
    assert r_ev.status_code == 201
    ev_data = r_ev.json()
    assert ev_data["structured_payload"]["problem_confirmed"] is True

    # Check that hypothesis can now be marked or is auto-marked SUPPORTED
    ws_updated = client.get(f"/api/v1/validation/workspaces/{ws_id}", headers=headers).json()
    h_updated = next(h for h in ws_updated["hypotheses"] if h["id"] == h_problem["id"])
    assert h_updated["status"] == STATUS_SUPPORTED
    assert h_updated["evidence_count"] >= 1


def test_simulated_content_is_isolated_and_cannot_support_hypothesis():
    """Test that simulated / AI persona content cannot be used as validation proof."""
    _, tok = _register_and_login("sim_content")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "منصة تعليم إلكتروني")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    h_demand = next(h for h in ws["hypotheses"] if h["hypothesis_type"] == "DEMAND")

    # Add simulated AI persona interview
    r_sim = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "محاكاة شخصية طالب جامعي (AI Persona Simulation)",
            "hypothesis_id": h_demand["id"],
            "source_type": "USER_RECORDED",
            "is_simulated": True,  # SIMULATED
            "evidence_strength": "STRONG",
            "evidence_direction": "SUPPORTING",
            "structured_payload": {
                "problem_confirmed": True,
                "notes": "محاكاة نموذج ذكاء اصطناعي لاختبار الأسئلة فقط.",
            },
        },
        headers=headers,
    )
    assert r_sim.status_code == 201

    # Attempt to transition hypothesis to SUPPORTED with only simulated evidence -> 422 rejected!
    r_patch = client.patch(
        f"/api/v1/validation/hypotheses/{h_demand['id']}",
        json={"status": STATUS_SUPPORTED},
        headers=headers,
    )
    assert r_patch.status_code == 422


def test_survey_percentages_derived_from_actual_counts_and_zero_protected():
    """Test that survey response percentages derive from real counts only and zero denominator is protected."""
    _, tok = _register_and_login("survey_counts")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مركز رياضي نسائي")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # 1. Survey with 0 responses -> derived_agreement_rate is None (NO fake 0% or percentage)
    r_zero = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "SURVEY",
            "title": "استبيان أولي فارغ",
            "source_type": "USER_RECORDED",
            "structured_payload": {
                "responses_count": 0,
                "positive_responses": 0,
            },
        },
        headers=headers,
    )
    assert r_zero.status_code == 201
    assert r_zero.json()["structured_payload"]["derived_agreement_rate"] is None

    # 2. Survey with 50 actual responses and 41 positive
    r_real = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "SURVEY",
            "title": "استبيان الرغبة بالاشتراك في الحي",
            "source_type": "USER_RECORDED",
            "structured_payload": {
                "responses_count": 50,
                "positive_responses": 41,
            },
        },
        headers=headers,
    )
    assert r_real.status_code == 201
    assert r_real.json()["structured_payload"]["derived_agreement_rate"] == 82.0


def test_demand_signals_and_deterministic_conversion_calculation():
    """Test demand signals calculate conversion rate deterministically from actual numbers."""
    _, tok = _register_and_login("demand_signal")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "متجر تجارة إلكترونية متخصص")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Landing page test: 200 visitors, 16 waitlist signups -> exactly 8.0%
    r_ev = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "WAITLIST",
            "title": "تسجيلات قائمة الانتظار لصفحة الهبوط التجريبية",
            "source_type": "USER_RECORDED",
            "structured_payload": {
                "signal_type": "waitlist_conversion",
                "sample_size": 200,
                "positive_actions": 16,
            },
        },
        headers=headers,
    )
    assert r_ev.status_code == 201
    assert r_ev.json()["structured_payload"]["derived_conversion_rate"] == 8.0


def test_pricing_assumption_separated_from_tested_price():
    """Test pricing evidence separates assumed price from tested price."""
    _, tok = _register_and_login("price_test")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "خدمات استشارية تقنية")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Assumed 500 SAR vs Tested 450 SAR
    r_price = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "TRANSACTION",
            "title": "اختبار عروض أسعار تجريبية للعملاء",
            "source_type": "USER_RECORDED",
            "structured_payload": {
                "assumed_price": 500.0,
                "tested_price": 450.0,
                "customer_response": "ACCEPTED",
            },
        },
        headers=headers,
    )
    assert r_price.status_code == 201
    payload = r_price.json()["structured_payload"]
    assert payload["assumed_price"] == 500.0
    assert payload["tested_price"] == 450.0
    assert payload["price_variance"] == -50.0


def test_competitor_source_provenance_requires_valid_url():
    """Test competitor evidence enforces valid web source URL."""
    _, tok = _register_and_login("comp_evidence")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مقهى مختص")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # 1. COMPETITOR_BENCHMARK without source_url -> 400 Bad Request
    r_no_url = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "COMPETITOR_BENCHMARK",
            "title": "مقارنة أسعار المنافسين في السوق",
            "source_type": "COMPETITOR",
        },
        headers=headers,
    )
    assert r_no_url.status_code == 400
    assert "source_url" in r_no_url.text or "رابط" in r_no_url.text

    # 2. Invalid URL -> 400 Bad Request
    r_bad = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "URL_SOURCE",
            "title": "قائمة أسعار المنافس المحلي",
            "source_type": "URL_SOURCE",
            "source_url": "invalid_url_without_http",
        },
        headers=headers,
    )
    assert r_bad.status_code == 400

    # 3. Valid URL -> 201 Created
    r_good = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "COMPETITOR_BENCHMARK",
            "title": "قائمة أسعار المنافس المحلي",
            "source_type": "COMPETITOR",
            "source_url": "https://competitor-cafe.sa/menu",
            "source_owner": "منافس محلي - فرع الرياض",
            "structured_payload": {
                "observed_price": 22.0,
                "offering": "لاتيه 12 أونصة",
            },
        },
        headers=headers,
    )
    assert r_good.status_code == 201
    assert r_good.json()["source_url"] == "https://competitor-cafe.sa/menu"


def test_zero_synthetic_validation_score_and_transparent_evaluation():
    """Test workspace evaluation yields transparent status and counts, never a fake percentage score."""
    _, tok = _register_and_login("no_fake_score")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع صناعي خفيف")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    eval_res = ws["evaluation"]

    # Must NOT have synthetic score
    assert "score" not in eval_res
    assert "validation_score" not in eval_res
    assert "percentage" not in eval_res

    # Must have transparent counts
    assert "total_hypotheses" in eval_res
    assert "counts" in eval_res
    assert "critical_total" in eval_res
    assert "status" in eval_res
    assert eval_res["status"] in (
        WS_STATUS_NEEDS_EVIDENCE,
        WS_STATUS_IN_PROGRESS,
        WS_STATUS_PARTIALLY_VALIDATED,
        WS_STATUS_VALIDATED,
        WS_STATUS_NOT_VALIDATED,
    )


def test_immutable_validation_decisions_and_snapshot():
    """Test recording immutable validation decision (GO, GO_WITH_CONDITIONS, PIVOT, STOP) with evidence snapshot."""
    _, tok = _register_and_login("val_decision")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "استوديو تصميم وإنتاج")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # 1. Attempting GO_WITH_CONDITIONS from NEEDS_EVIDENCE status -> 400 rejected!
    r_dec_needs_ev = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={
            "decision": DECISION_GO_WITH_CONDITIONS,
            "decision_reason": "محاولة اتخاذ قرار مشروط قبل توفير أي أدلة",
            "conditions": ["الحصول على خطابات نوايا مبدئية"],
        },
        headers=headers,
    )
    assert r_dec_needs_ev.status_code == 400
    assert "PARTIALLY_VALIDATED" in r_dec_needs_ev.text or "مشروط" in r_dec_needs_ev.text

    # Provide real supporting evidence for one hypothesis to transition workspace to PARTIALLY_VALIDATED
    h_first = ws["hypotheses"][0]
    r_first_ev = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة مبدئية تدعم الفرضية الأولى",
            "hypothesis_id": h_first["id"],
            "evidence_strength": "STRONG",
            "evidence_direction": "SUPPORTING",
            "is_simulated": False,
        },
        headers=headers,
    )
    assert r_first_ev.status_code == 201

    # 2. In PARTIALLY_VALIDATED: GO_WITH_CONDITIONS without conditions -> 400
    r_bad_cond = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={"decision": DECISION_GO_WITH_CONDITIONS, "decision_reason": "سبب كافٍ للموافقة المشروطة", "conditions": []},
        headers=headers,
    )
    assert r_bad_cond.status_code == 400

    # 3. In PARTIALLY_VALIDATED: Record GO_WITH_CONDITIONS version 1 -> 201
    r_dec1 = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={
            "decision": DECISION_GO_WITH_CONDITIONS,
            "decision_reason": "الموافقة المشروطة على المضي قدماً مع الالتزام بالحصول على خطابات نوايا إضافية",
            "conditions": ["الحصول على 3 عقود مبدئية قبل توقيع عقد الإيجار"],
        },
        headers=headers,
    )
    assert r_dec1.status_code == 201
    d1 = r_dec1.json()
    assert d1["decision"] == DECISION_GO_WITH_CONDITIONS
    assert d1["decision_version"] == 1
    assert "evidence_snapshot" in d1

    # 3. Attempting GO before critical hypotheses are supported -> 400 blocked!
    r_dec_blocked = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={
            "decision": DECISION_GO,
            "decision_reason": "محاولة اتخاذ قرار GO دون دعم الفرضيات الحرجة بالأدلة",
        },
        headers=headers,
    )
    assert r_dec_blocked.status_code == 400
    assert "فرضيات حرجة" in r_dec_blocked.text or "critical" in r_dec_blocked.text.lower()

    # Provide real supporting evidence for the critical hypotheses
    crit_hypos = [h for h in ws["hypotheses"] if h["importance"] == "CRITICAL"]
    for ch in crit_hypos:
        r_ev = client.post(
            f"/api/v1/validation/workspaces/{ws_id}/evidence",
            json={
                "evidence_type": "INTERVIEW",
                "title": f"دليل إثبات الفرضية الحرجة {ch['id']}",
                "hypothesis_id": ch["id"],
                "evidence_strength": "STRONG",
                "evidence_direction": "SUPPORTING",
                "is_simulated": False,
                "structured_payload": {"problem_confirmed": True},
            },
            headers=headers,
        )
        assert r_ev.status_code == 201

    # Now record definitive GO decision (version 2)
    r_dec2 = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={
            "decision": DECISION_GO,
            "decision_reason": "تم استيفاء الشروط وتوقيع العقود المبدئية بنجاح والمضي نحو مرحلة الإطلاق",
        },
        headers=headers,
    )
    assert r_dec2.status_code == 201
    d2 = r_dec2.json()
    assert d2["decision"] == DECISION_GO
    assert d2["decision_version"] == 2

    # 4. History endpoint preserves both decisions immutably
    r_hist = client.get(f"/api/v1/validation/workspaces/{ws_id}/decisions", headers=headers)
    assert r_hist.status_code == 200
    hist = r_hist.json()
    assert len(hist) == 2
    assert hist[0]["decision_version"] == 2
    assert hist[1]["decision_version"] == 1


# ==============================================================================
# WAVE 4 HARDENED GATES DEDICATED TESTS
# ==============================================================================

def test_evidence_direction_validation_and_rejection():
    """Gate 1: Test evidence_direction defaults to NEUTRAL for unlinked, is required for hypotheses, and rejects invalid."""
    _, tok = _register_and_login("direction_test")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع اختبار اتجاه الأدلة")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    h_sample = ws["hypotheses"][0]

    # 1. Default direction for unlinked evidence is NEUTRAL (never SUPPORTING)
    r_def = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة عامة بدون ربط بالاتجاه التلقائي",
            "source_type": "USER_RECORDED",
        },
        headers=headers,
    )
    assert r_def.status_code == 201
    assert r_def.json()["evidence_direction"] == "NEUTRAL"

    # 2. Hypothesis-linked evidence WITHOUT direction -> 422 rejected!
    r_no_dir = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "دليل مرتبط بفرضية بدون تحديد أثر",
            "hypothesis_id": h_sample["id"],
            "source_type": "USER_RECORDED",
        },
        headers=headers,
    )
    assert r_no_dir.status_code == 422
    assert "أثر الدليل" in r_no_dir.text or "direction" in r_no_dir.text.lower()

    # 3. Explicit REFUTING
    r_ref = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة تثبت عدم رغبة العملاء بالمنتج",
            "hypothesis_id": h_sample["id"],
            "evidence_direction": "REFUTING",
            "source_type": "USER_RECORDED",
        },
        headers=headers,
    )
    assert r_ref.status_code == 201
    assert r_ref.json()["evidence_direction"] == "REFUTING"

    # 4. Explicit NEUTRAL
    r_neu = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة محايدة غير حاسمة",
            "hypothesis_id": h_sample["id"],
            "evidence_direction": "NEUTRAL",
            "source_type": "USER_RECORDED",
        },
        headers=headers,
    )
    assert r_neu.status_code == 201
    assert r_neu.json()["evidence_direction"] == "NEUTRAL"

    # 5. STRONG evidence with NEUTRAL direction must NOT auto-support a hypothesis
    h_second = ws["hypotheses"][1]
    r_strong_neu = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "دليل قوي لكنه محايد في اتجاهه",
            "hypothesis_id": h_second["id"],
            "evidence_strength": "STRONG",
            "evidence_direction": "NEUTRAL",
            "source_type": "USER_RECORDED",
        },
        headers=headers,
    )
    assert r_strong_neu.status_code == 201
    ws_after_neu = client.get(f"/api/v1/validation/workspaces/{ws_id}", headers=headers).json()
    h_second_checked = next(h for h in ws_after_neu["hypotheses"] if h["id"] == h_second["id"])
    assert h_second_checked["status"] != STATUS_SUPPORTED

    # 6. Invalid direction -> rejected
    r_inv = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "دليل باتجاه غير معروف",
            "evidence_direction": "UNKNOWN_DIRECTION",
            "source_type": "USER_RECORDED",
        },
        headers=headers,
    )
    assert r_inv.status_code in (400, 422)


def test_hypothesis_transition_gate_refuting_and_supporting():
    """Gate 2: Test hypothesis status transitions require matching evidence direction."""
    _, tok = _register_and_login("trans_gate")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع بوابة الفرضيات")

    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    h1 = ws["hypotheses"][0]

    # Cannot transition to SUPPORTED without SUPPORTING evidence
    r_bad_sup = client.patch(f"/api/v1/validation/hypotheses/{h1['id']}", json={"status": STATUS_SUPPORTED}, headers=headers)
    assert r_bad_sup.status_code == 422

    # Cannot transition to NOT_SUPPORTED without REFUTING evidence
    r_bad_not = client.patch(f"/api/v1/validation/hypotheses/{h1['id']}", json={"status": STATUS_NOT_SUPPORTED}, headers=headers)
    assert r_bad_not.status_code == 422

    # Add REFUTING evidence -> allows transition to NOT_SUPPORTED
    client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "دليل يدحض الفرضية الأولى",
            "hypothesis_id": h1["id"],
            "evidence_direction": "REFUTING",
            "evidence_strength": "STRONG",
            "is_simulated": False,
        },
        headers=headers,
    )
    ws_after_ref = client.get(f"/api/v1/validation/workspaces/{ws_id}", headers=headers).json()
    h1_ref = next(h for h in ws_after_ref["hypotheses"] if h["id"] == h1["id"])
    assert h1_ref["status"] == STATUS_NOT_SUPPORTED


def test_cross_workspace_ownership_rejection():
    """Gate 3: Cross-workspace linking of hypothesis, experiment, or evidence is strictly rejected."""
    _, tok = _register_and_login("cross_ws")
    headers = _auth(tok)
    _, study_id_1 = _create_project_and_study(tok, "مشروع مساحة 1")
    _, study_id_2 = _create_project_and_study(tok, "مشروع مساحة 2")

    ws1 = client.get(f"/api/v1/validation/study/{study_id_1}", headers=headers).json()
    ws2 = client.get(f"/api/v1/validation/study/{study_id_2}", headers=headers).json()
    h_ws1 = ws1["hypotheses"][0]["id"]

    # 1. Attempt to add evidence in WS2 linking to hypothesis in WS1 -> 400 rejected
    r_ev_cross = client.post(
        f"/api/v1/validation/workspaces/{ws2['id']}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "دليل عابر لمساحة العمل",
            "hypothesis_id": h_ws1,
            "evidence_direction": "SUPPORTING",
            "source_type": "USER_RECORDED",
        },
        headers=headers,
    )
    assert r_ev_cross.status_code in (400, 422)
    assert "مساحة عمل أخرى" in r_ev_cross.text or "prohibited" in r_ev_cross.text.lower()

    # 2. Attempt to add experiment in WS2 linking to hypothesis in WS1 -> 400 rejected
    r_exp_cross = client.post(
        f"/api/v1/validation/workspaces/{ws2['id']}/experiments",
        json={
            "experiment_type": "CUSTOMER_INTERVIEW",
            "title": "تجربة عابرة للمساحات",
            "objective": "اختبار الهدف",
            "method": "مقابلات",
            "success_criteria": "موافقة 80%",
            "hypothesis_id": h_ws1,
        },
        headers=headers,
    )
    assert r_exp_cross.status_code in (400, 422)


def test_cross_user_ownership_rejection():
    """Gate 4: Cross-user mutation and retrieval attempts are strictly forbidden (403)."""
    _, tok1 = _register_and_login("owner_user")
    _, tok2 = _register_and_login("intruder_user")

    _, study_id = _create_project_and_study(tok1, "مشروع المالك الأصلي")
    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=_auth(tok1)).json()
    ws_id = ws["id"]
    h_id = ws["hypotheses"][0]["id"]

    # Intruder tries GET workspace
    assert client.get(f"/api/v1/validation/workspaces/{ws_id}", headers=_auth(tok2)).status_code == 403

    # Intruder tries POST hypothesis
    assert client.post(
        f"/api/v1/validation/workspaces/{ws_id}/hypotheses",
        json={"hypothesis_type": "DEMAND", "statement": "فرضية من مستخدم غريب"},
        headers=_auth(tok2),
    ).status_code == 403

    # Intruder tries PATCH hypothesis
    assert client.patch(
        f"/api/v1/validation/hypotheses/{h_id}",
        json={"statement": "تعديل غير مصرح به"},
        headers=_auth(tok2),
    ).status_code == 403

    # Intruder tries POST evidence
    assert client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={"evidence_type": "INTERVIEW", "title": "دليل من مستخدم غريب"},
        headers=_auth(tok2),
    ).status_code == 403

    # Intruder tries POST decision
    assert client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={"decision": "STOP", "decision_reason": "محاولة إيقاف غير مصرح بها"},
        headers=_auth(tok2),
    ).status_code == 403


def test_url_source_validation_rejections():
    """Gate 5: Non-http/https source URLs are rejected, and URL_SOURCE requires valid URL."""
    _, tok = _register_and_login("url_rules")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع فحص الروابط")
    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # 1. Any evidence with invalid source_url format is rejected
    r_bad = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة برابط غير صالح",
            "source_url": "ftp://files.example.com/record.mp3",
        },
        headers=headers,
    )
    assert r_bad.status_code == 400

    # 2. URL_SOURCE without source_url is rejected
    r_empty = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "URL_SOURCE",
            "title": "دليل رابط دون إرفاق الرابط",
            "source_url": "",
        },
        headers=headers,
    )
    assert r_empty.status_code == 400


def test_decision_go_gate_and_simulated_evidence_isolation():
    """Gate 6 & 8: GO decision requires real evidence backing for all critical hypotheses; simulated rejected."""
    _, tok = _register_and_login("go_gate")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع اختبار بوابة الانطلاق GO")
    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    crit_hypos = [h for h in ws["hypotheses"] if h["importance"] == "CRITICAL"]
    assert len(crit_hypos) >= 2

    # 1. Attempt GO with untested critical hypotheses -> 400
    r_fail1 = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={"decision": DECISION_GO, "decision_reason": "محاولة اتخاذ قرار GO دون اختبار الفرضيات الحرجة"},
        headers=headers,
    )
    assert r_fail1.status_code == 400

    # 2. Add SIMULATED evidence for critical hypotheses and try GO -> still 400!
    for ch in crit_hypos:
        client.post(
            f"/api/v1/validation/workspaces/{ws_id}/evidence",
            json={
                "evidence_type": "INTERVIEW",
                "title": f"دليل محاكاة ذكاء اصطناعي {ch['id']}",
                "hypothesis_id": ch["id"],
                "evidence_strength": "STRONG",
                "evidence_direction": "SUPPORTING",
                "is_simulated": True,  # SIMULATED
            },
            headers=headers,
        )
    r_fail_sim = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={"decision": DECISION_GO, "decision_reason": "محاولة اتخاذ قرار GO بأدلة محاكاة فقط"},
        headers=headers,
    )
    assert r_fail_sim.status_code == 400

    # 3. Add REAL (non-simulated) SUPPORTING evidence for all critical hypotheses
    for ch in crit_hypos:
        client.post(
            f"/api/v1/validation/workspaces/{ws_id}/evidence",
            json={
                "evidence_type": "INTERVIEW",
                "title": f"دليل ميداني حقيقي موثق {ch['id']}",
                "hypothesis_id": ch["id"],
                "evidence_strength": "STRONG",
                "evidence_direction": "SUPPORTING",
                "is_simulated": False,  # REAL
                "structured_payload": {"problem_confirmed": True},
            },
            headers=headers,
        )

    # 4. Now GO succeeds!
    r_go = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={"decision": DECISION_GO, "decision_reason": "تم التحقق الكامل من كافة الفرضيات الحرجة بأدلة واقعية موثقة"},
        headers=headers,
    )
    assert r_go.status_code == 201
    assert r_go.json()["decision"] == DECISION_GO


def test_go_with_conditions_gate_with_refuted_assumptions():
    """Gate 7: GO_WITH_CONDITIONS requires conditions and mitigations for refuted critical hypotheses."""
    _, tok = _register_and_login("cond_gate")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع الموافقة المشروطة")
    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]
    crit_h = ws["hypotheses"][0]

    # Refute the first critical hypothesis with real evidence
    client.post(
        f"/api/v1/validation/workspaces/{ws_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة تدحض الفرضية الحرجة الأولى",
            "hypothesis_id": crit_h["id"],
            "evidence_strength": "STRONG",
            "evidence_direction": "REFUTING",
            "is_simulated": False,
        },
        headers=headers,
    )

    # 1. Attempt GO_WITH_CONDITIONS with empty conditions -> 400
    r_bad = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={"decision": DECISION_GO_WITH_CONDITIONS, "decision_reason": "موافقة مشروطة بدون شروط", "conditions": []},
        headers=headers,
    )
    assert r_bad.status_code == 400

    # 2. Attempt GO_WITH_CONDITIONS with conditions when critical hypothesis is NOT_SUPPORTED -> 400 BLOCKED!
    r_blocked = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={
            "decision": DECISION_GO_WITH_CONDITIONS,
            "decision_reason": "محاولة الموافقة المشروطة رغم دحض فرضية حرجة",
            "conditions": ["تعديل باقة التسعير وإعادة اختبارها مع 20 عميل جديد"],
        },
        headers=headers,
    )
    assert r_blocked.status_code == 400
    assert "NOT_VALIDATED" in r_blocked.text or "فرضيات حرجة" in r_blocked.text or "مشروط" in r_blocked.text

    # 3. PIVOT succeeds when critical hypotheses are refuted
    r_pivot = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={
            "decision": DECISION_PIVOT,
            "decision_reason": "تغيير مسار نموذج العمل بالكامل نظراً لرفض العملاء الفرضية الجوهرية",
        },
        headers=headers,
    )
    assert r_pivot.status_code == 201
    assert r_pivot.json()["decision"] == DECISION_PIVOT

    # 4. In a separate workspace that reaches PARTIALLY_VALIDATED without refuted critical hypotheses:
    _, tok2 = _register_and_login("cond_pass")
    _, study2 = _create_project_and_study(tok2, "مشروع مشروط ناجح")
    ws2 = client.get(f"/api/v1/validation/study/{study2}", headers=_auth(tok2)).json()
    ws2_id = ws2["id"]

    # Add supporting evidence for one hypothesis
    client.post(
        f"/api/v1/validation/workspaces/{ws2_id}/evidence",
        json={
            "evidence_type": "INTERVIEW",
            "title": "مقابلة داعمة أولية",
            "hypothesis_id": ws2["hypotheses"][0]["id"],
            "evidence_strength": "STRONG",
            "evidence_direction": "SUPPORTING",
            "is_simulated": False,
        },
        headers=_auth(tok2),
    )

    # Now GO_WITH_CONDITIONS succeeds with conditions
    r_cond_ok = client.post(
        f"/api/v1/validation/workspaces/{ws2_id}/decision",
        json={
            "decision": DECISION_GO_WITH_CONDITIONS,
            "decision_reason": "موافقة مشروطة مع استمرار اختبار بقية الفرضيات",
            "conditions": ["استكمال اختبار التسعير قبل التوسع"],
        },
        headers=_auth(tok2),
    )
    assert r_cond_ok.status_code == 201
    assert r_cond_ok.json()["decision"] == DECISION_GO_WITH_CONDITIONS


def test_evaluate_workspace_status_cannot_be_validated_without_real_evidence():
    """Gate 8: Stored hypothesis status cannot artificially show VALIDATED without genuine non-simulated evidence."""
    from app.services.validation import evaluate_workspace_status

    _, tok = _register_and_login("eval_gate")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع فحص دقة الحالة")
    ws_json = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws_json["id"]

    db_session = next(app_db.get_db())
    ws_obj = db_session.query(models.ValidationWorkspace).filter_by(id=ws_id).first()

    # Manually set all hypotheses to SUPPORTED in the database without adding any real evidence
    for h in ws_obj.hypotheses:
        h.status = STATUS_SUPPORTED
    db_session.commit()
    db_session.refresh(ws_obj)

    # evaluate_workspace_status MUST NOT return VALIDATED because real supporting evidence does not exist!
    eval_res = evaluate_workspace_status(ws_obj)
    assert eval_res["status"] != WS_STATUS_VALIDATED
    assert eval_res["critical_supported"] == 0
    assert eval_res["status"] in (WS_STATUS_PARTIALLY_VALIDATED, WS_STATUS_NEEDS_EVIDENCE)


def test_decision_snapshot_immutability():
    """Gate 9: Decision snapshot captures complete frozen state of hypotheses, experiments, and evidence."""
    _, tok = _register_and_login("snap_gate")
    headers = _auth(tok)
    _, study_id = _create_project_and_study(tok, "مشروع التحقق من تجميد اللقطة")
    ws = client.get(f"/api/v1/validation/study/{study_id}", headers=headers).json()
    ws_id = ws["id"]

    # Record experiment
    r_exp = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/experiments",
        json={
            "experiment_type": "SURVEY",
            "title": "استبيان الرضا",
            "objective": "قياس الرضا",
            "method": "نماذج إلكترونية",
            "success_criteria": "موافقة 70%",
        },
        headers=headers,
    )
    assert r_exp.status_code == 201

    # Record decision
    r_dec = client.post(
        f"/api/v1/validation/workspaces/{ws_id}/decision",
        json={
            "decision": DECISION_PIVOT,
            "decision_reason": "ضرورة تغيير الشريحة المستهدفة بناء على مراجعة السوق",
        },
        headers=headers,
    )
    assert r_dec.status_code == 201
    snap = r_dec.json()["evidence_snapshot"]
    assert "evaluation_summary" in snap
    assert "hypotheses" in snap
    assert "experiments" in snap
    assert "evidence" in snap
    assert "frozen_at" in snap
    assert len(snap["experiments"]) == 1
    assert snap["experiments"][0]["title"] == "استبيان الرضا"

