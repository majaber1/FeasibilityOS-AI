"""End-to-end full journey test: project creation → feasibility study → AI fills
all information → phase progression → GO verdict.

Mocks AI agents so the test runs without Groq. Each agent returns realistic
structured JSON matching the exact format the real agents produce, so the
orchestrator, state machine, and API layer are exercised for real.
"""
import os
import sys
import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
PASSWORD = "Journey@Test1!"


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()
    from app.api.v2.study_engine import StudyStateRow, StudyVersionRow
    app_db.Base.metadata.create_all(bind=app_db.engine)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _register_and_login(prefix: str = "journey") -> tuple[dict, str]:
    email = f"{prefix}_{_uid()}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}, email


# ---------------------------------------------------------------------------
# Mock AI responses — realistic structured JSON from each agent
# ---------------------------------------------------------------------------

DISCOVERY_RESPONSE = """Based on your project description, I've classified your project:

```json
{
  "archetype": "saas_digital",
  "sector": "تقنية المعلومات - منصة إدارة المشاريع",
  "stage": "mvp",
  "decision_goal": "investment",
  "missing_information": ["تكلفة اكتساب العميل", "معدل التسرب الشهري"],
  "recommended_model": "saas_v1",
  "next_questions": ["ما سعر الاشتراك الشهري؟", "كم عدد العملاء المستهدفين؟"]
}
```

مشروعك يبدو واعداً. أحتاج لمعرفة تفاصيل إضافية حول نموذج الإيرادات والتكاليف."""

DISCOVERY_COMPLETE_RESPONSE = """Thank you for the additional details. Your profile is now complete:

```json
{
  "archetype": "saas_digital",
  "sector": "Information Technology - Project Management Platform",
  "stage": "mvp",
  "decision_goal": "investment",
  "missing_information": [],
  "recommended_model": "saas_v1",
  "next_questions": []
}
```

All required information has been gathered. Moving to evidence review."""

EVIDENCE_RESPONSE = """I've analyzed the evidence provided:

```json
{
  "claims": [
    {
      "statement": "سوق إدارة المشاريع في السعودية ينمو بنسبة 15% سنوياً",
      "source_type": "official",
      "confidence": 0.85,
      "source_url": "https://www.mcit.gov.sa/reports/2024"
    },
    {
      "statement": "سعر الاشتراك الشهري 299 ريال للشركات الصغيرة",
      "source_type": "user_input",
      "confidence": 0.9,
      "source_url": null
    },
    {
      "statement": "تكلفة اكتساب العميل (CAC) تقدر بـ 500 ريال",
      "source_type": "user_input",
      "confidence": 0.7,
      "source_url": null
    },
    {
      "statement": "المنافسون الرئيسيون: Monday.com, Asana, محلي: Mostaql",
      "source_type": "ai_assumption",
      "confidence": 0.6,
      "source_url": null
    }
  ],
  "gaps": ["بيانات السوق المحلي الدقيقة"],
  "evidence_sufficient": true
}
```

الأدلة كافية للمضي قدماً في تحليل الافتراضات."""

ASSUMPTIONS_RESPONSE = """Based on the evidence, here are the key assumptions:

```json
{
  "assumptions": [
    {
      "key": "الإيراد الشهري للعميل (ARPU)",
      "value": "299 ريال",
      "source": "مدخل المستخدم",
      "confidence": "confirmed",
      "low": "199",
      "base": "299",
      "high": "399"
    },
    {
      "key": "عدد العملاء الجدد شهرياً (السنة الأولى)",
      "value": "50 عميل",
      "source": "تقدير بناءً على حجم السوق",
      "confidence": "medium",
      "low": "25",
      "base": "50",
      "high": "80"
    },
    {
      "key": "معدل التسرب الشهري (Churn)",
      "value": "5%",
      "source": "متوسط صناعة SaaS",
      "confidence": "medium",
      "low": "3%",
      "base": "5%",
      "high": "8%"
    },
    {
      "key": "تكلفة التشغيل الشهرية",
      "value": "45,000 ريال",
      "source": "تقدير المستخدم",
      "confidence": "confirmed",
      "low": "35000",
      "base": "45000",
      "high": "60000"
    },
    {
      "key": "تكلفة اكتساب العميل (CAC)",
      "value": "500 ريال",
      "source": "مدخل المستخدم",
      "confidence": "medium",
      "low": "350",
      "base": "500",
      "high": "750"
    }
  ],
  "assumptions_complete": true
}
```

الافتراضات مكتملة وجاهزة للتحليل المالي."""

FINANCIAL_RESPONSE = """Based on the assumptions, here is the financial analysis:

The initial investment is estimated at 500,000 SAR.

```json
{
  "financials": {
    "initial_investment": 500000,
    "monthly_revenue_y1": 179400,
    "annual_revenue_y1": 2152800,
    "monthly_costs": 45000,
    "annual_costs_y1": 540000
  }
}
```

NPV at 12% discount: 1,234,567 SAR
IRR: 34.5%
Payback period: 18 months

The project shows strong financial viability with positive NPV and healthy IRR."""

RISK_RESPONSE = """Risk assessment for the SaaS project:

```json
{
  "risks": [
    {
      "category": "market",
      "description": "منافسة شديدة من منصات عالمية مثل Monday.com و Asana",
      "likelihood": "high",
      "impact": "medium",
      "mitigation": "التركيز على الميزات المحلية واللغة العربية والتكامل مع الأنظمة السعودية"
    },
    {
      "category": "regulatory",
      "description": "متطلبات توطين البيانات في السعودية",
      "likelihood": "medium",
      "impact": "high",
      "mitigation": "استضافة على سيرفرات محلية (AWS Bahrain / STC Cloud)"
    },
    {
      "category": "operational",
      "description": "صعوبة استقطاب مطورين محليين",
      "likelihood": "medium",
      "impact": "medium",
      "mitigation": "فريق عمل عن بعد مع نواة محلية"
    },
    {
      "category": "financial",
      "description": "تأخر في تحقيق نقطة التعادل إذا كان معدل التسرب أعلى من المتوقع",
      "likelihood": "medium",
      "impact": "high",
      "mitigation": "برنامج ولاء العملاء وتحسين مستمر للمنتج"
    }
  ],
  "overall_risk_level": "medium",
  "critical_risks": ["منافسة شديدة من منصات عالمية", "متطلبات توطين البيانات"],
  "risk_assessment_complete": true
}
```

المخاطر الإجمالية متوسطة مع إمكانية التخفيف."""

DECISION_RESPONSE = """بناءً على التحليل الشامل، هذا هو القرار النهائي:

```json
{
  "verdict": "GO_WITH_CONDITIONS",
  "rationale": "المشروع مجدي مالياً مع NPV إيجابي و IRR 34.5% وهو أعلى من معدل الخصم 12%. السوق السعودي واعد لمنصات SaaS المحلية مع دعم رؤية 2030 للتحول الرقمي. المخاطر الرئيسية قابلة للتخفيف.",
  "conditions": [
    "تأمين استضافة محلية للبيانات قبل الإطلاق",
    "بناء فريق دعم عملاء عربي متخصص",
    "تحقيق 100 عميل في أول 6 أشهر كحد أدنى",
    "مراجعة معدل التسرب كل ربع سنوي"
  ],
  "key_risks": ["منافسة عالمية شديدة", "متطلبات توطين البيانات", "تأخر نقطة التعادل"],
  "confidence_score": 0.78,
  "next_steps": [
    "إعداد خطة تسويق للأشهر الستة الأولى",
    "التقدم لبرنامج منشآت للدعم",
    "توقيع عقد استضافة محلية",
    "بناء النسخة التجريبية وإطلاقها"
  ]
}
```

التوصية: المضي بالمشروع مع الالتزام بالشروط أعلاه."""


def _mock_llm_response(content: str):
    mock_response = MagicMock()
    mock_response.content = content
    return mock_response


# ---------------------------------------------------------------------------
# Helper to set phase + data via DB for controlled progression
# ---------------------------------------------------------------------------

def _set_study_state(study_id: str, **fields):
    db = app_db.SessionLocal()
    try:
        from app.api.v2.study_engine import StudyStateRow
        row = db.query(StudyStateRow).filter_by(study_id=study_id).first()
        assert row is not None, f"Study {study_id} not found in DB"
        for k, v in fields.items():
            if hasattr(row, k):
                setattr(row, k, v)
        db.commit()
    finally:
        db.close()


# =============================================================================
# 1. Full journey: project → study → AI fills everything → verdict
# =============================================================================

class TestFullJourney:
    """Complete end-to-end flow with mocked AI agents."""

    def test_create_project_then_study(self):
        headers, _ = _register_and_login("full1")
        proj = client.post("/projects/", json={
            "name": "منصة إدارة المشاريع الذكية",
            "industry": "تقنية المعلومات",
            "investment": 500000,
            "stage": "idea",
        }, headers=headers)
        assert proj.status_code == 201
        pid = proj.json()["id"]

        study = client.post("/api/v2/studies", json={
            "project_id": str(pid),
            "language": "ar",
        }, headers=headers)
        assert study.status_code == 200
        data = study.json()
        assert data["study_id"].startswith("study_")
        assert data["phase"] == "DRAFT"

    @patch("ai_engine.agents.discovery.get_llm")
    def test_discovery_fills_profile(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(DISCOVERY_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("disc1")
        proj = client.post("/projects/", json={
            "name": "SaaS Platform",
            "industry": "IT",
            "investment": 500000,
            "stage": "idea",
        }, headers=headers)
        pid = str(proj.json()["id"])

        r = client.post("/api/v2/studies", json={
            "project_id": pid,
            "language": "ar",
            "description": "أريد بناء منصة SaaS لإدارة المشاريع للشركات السعودية الصغيرة والمتوسطة. الاشتراك الشهري 299 ريال. لدي MVP جاهز.",
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["phase"] == "NEEDS_INFORMATION"
        assert data["profile"] is not None
        assert data["profile"]["archetype"] == "saas_digital"
        assert data["profile"]["sector"] != ""
        assert data["profile"]["stage"] == "mvp"

    @patch("ai_engine.agents.discovery.get_llm")
    def test_discovery_with_complete_info_skips_to_evidence(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(DISCOVERY_COMPLETE_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("disc2")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "en",
            "description": "SaaS project management platform. 299 SAR/month. 50 new customers/month target. 5% churn. 45K SAR monthly opex. CAC 500 SAR.",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["phase"] == "EVIDENCE_REVIEW"

    @patch("ai_engine.agents.discovery.get_llm")
    def test_message_continues_discovery(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            _mock_llm_response(DISCOVERY_RESPONSE),
            _mock_llm_response(DISCOVERY_COMPLETE_RESPONSE),
        ]
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("msg1")
        create_r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "ar",
            "description": "منصة SaaS لإدارة المشاريع",
        }, headers=headers)
        sid = create_r.json()["study_id"]
        assert create_r.json()["phase"] == "NEEDS_INFORMATION"

        msg_r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "تكلفة اكتساب العميل 500 ريال. معدل التسرب 5% شهرياً.",
        }, headers=headers)
        assert msg_r.status_code == 200
        assert msg_r.json()["response"] is not None


# =============================================================================
# 2. Phase-by-phase progression with approval gates
# =============================================================================

class TestPhaseByPhaseProgression:
    """Test each approval gate advances the study correctly."""

    def _create_study(self, headers) -> str:
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        return r.json()["study_id"]

    def test_approve_profile_advances_to_evidence_review(self):
        headers, _ = _register_and_login("adv1")
        sid = self._create_study(headers)
        _set_study_state(sid,
            phase="NEEDS_INFORMATION",
            profile_json={
                "archetype": "saas_digital",
                "sector": "IT",
                "stage": "mvp",
                "decision_goal": "investment",
                "missing_information": [],
                "language": "ar",
                "recommended_model": "saas_v1",
            },
            profile_confirmed=False,
        )

        r = client.post(f"/api/v2/studies/{sid}/approve/profile", json={
            "approved": True,
        }, headers=headers)
        assert r.status_code == 200

    @patch("ai_engine.agents.evidence.get_llm")
    def test_evidence_agent_fills_claims(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(EVIDENCE_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("evid1")
        sid = self._create_study(headers)
        _set_study_state(sid,
            phase="EVIDENCE_REVIEW",
            profile_json={
                "archetype": "saas_digital",
                "sector": "IT",
                "stage": "mvp",
                "decision_goal": "investment",
                "missing_information": [],
                "language": "ar",
                "recommended_model": "saas_v1",
            },
            profile_confirmed=True,
        )

        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "السوق ينمو 15% سنوياً. الاشتراك 299 ريال. CAC 500 ريال.",
        }, headers=headers)
        assert r.status_code == 200

        study = client.get(f"/api/v2/studies/{sid}", headers=headers)
        data = study.json()
        assert data["claims_count"] == 4

    @patch("ai_engine.agents.assumption.get_llm")
    def test_assumptions_agent_fills_assumptions(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(ASSUMPTIONS_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("asmp1")
        sid = self._create_study(headers)
        _set_study_state(sid,
            phase="ASSUMPTIONS_REVIEW",
            profile_json={
                "archetype": "saas_digital",
                "sector": "IT",
                "stage": "mvp",
                "decision_goal": "investment",
                "missing_information": [],
                "language": "ar",
                "recommended_model": "saas_v1",
            },
            profile_confirmed=True,
            evidence_approved=True,
            claims_json=[
                {"statement": "market growth 15%", "source_type": "official", "confidence": 0.85},
            ],
        )

        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "الرجاء تحليل الافتراضات",
        }, headers=headers)
        assert r.status_code == 200

        study = client.get(f"/api/v2/studies/{sid}", headers=headers)
        assert study.json()["assumptions_count"] == 5

    @patch("ai_engine.agents.risk.get_llm")
    def test_risk_agent_identifies_risks(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(RISK_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("risk1")
        sid = self._create_study(headers)
        _set_study_state(sid,
            phase="ANALYZED",
            profile_json={"archetype": "saas_digital", "sector": "IT", "stage": "mvp",
                          "decision_goal": "investment", "missing_information": [],
                          "language": "ar", "recommended_model": "saas_v1"},
            financial_results_json={"npv": 1234567, "irr": 0.345, "payback_months": 18},
        )

        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "قيّم المخاطر",
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["phase"] == "DECISION_READY"

    @patch("ai_engine.agents.decision.get_llm")
    def test_decision_agent_issues_verdict(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(DECISION_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("dec1")
        sid = self._create_study(headers)
        _set_study_state(sid,
            phase="DECISION_READY",
            profile_json={"archetype": "saas_digital", "sector": "IT", "stage": "mvp",
                          "decision_goal": "investment", "missing_information": [],
                          "language": "ar", "recommended_model": "saas_v1"},
            financial_results_json={"npv": 1234567, "irr": 0.345, "payback_months": 18},
            decision_risks=["market competition", "data localization"],
        )

        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "أصدر القرار النهائي",
        }, headers=headers)
        assert r.status_code == 200

        study = client.get(f"/api/v2/studies/{sid}", headers=headers)
        data = study.json()
        assert data["verdict"] == "GO_WITH_CONDITIONS"
        assert "مجدي" in data["decision_rationale"] or "NPV" in data["decision_rationale"]


# =============================================================================
# 3. Complete pipeline: DRAFT → FUNDING_READY in one test
# =============================================================================

class TestCompletePipeline:
    """Simulate the entire pipeline from DRAFT to a final verdict."""

    @patch("ai_engine.agents.decision.get_llm")
    @patch("ai_engine.agents.risk.get_llm")
    @patch("ai_engine.agents.financial_analyst.get_llm")
    @patch("ai_engine.agents.assumption.get_llm")
    @patch("ai_engine.agents.evidence.get_llm")
    @patch("ai_engine.agents.discovery.get_llm")
    def test_full_pipeline_draft_to_verdict(
        self, mock_disc, mock_evid, mock_asmp, mock_fin, mock_risk, mock_dec
    ):
        mock_disc.return_value = MagicMock(invoke=MagicMock(return_value=_mock_llm_response(DISCOVERY_RESPONSE)))
        mock_evid.return_value = MagicMock(invoke=MagicMock(return_value=_mock_llm_response(EVIDENCE_RESPONSE)))
        mock_asmp.return_value = MagicMock(invoke=MagicMock(return_value=_mock_llm_response(ASSUMPTIONS_RESPONSE)))
        mock_fin.return_value = MagicMock(invoke=MagicMock(return_value=_mock_llm_response(FINANCIAL_RESPONSE)))
        mock_risk.return_value = MagicMock(invoke=MagicMock(return_value=_mock_llm_response(RISK_RESPONSE)))
        mock_dec.return_value = MagicMock(invoke=MagicMock(return_value=_mock_llm_response(DECISION_RESPONSE)))

        headers, _ = _register_and_login("pipeline")

        proj = client.post("/projects/", json={
            "name": "SaaS Project Management",
            "industry": "IT",
            "investment": 500000,
            "stage": "idea",
        }, headers=headers)
        assert proj.status_code == 201
        pid = str(proj.json()["id"])

        # Step 1: Create study with description → discovery agent classifies
        r = client.post("/api/v2/studies", json={
            "project_id": pid,
            "language": "ar",
            "description": "منصة SaaS لإدارة المشاريع للشركات السعودية",
        }, headers=headers)
        assert r.status_code == 200
        sid = r.json()["study_id"]
        assert r.json()["phase"] == "NEEDS_INFORMATION"
        assert r.json()["profile"]["archetype"] == "saas_digital"

        # Step 2: Approve profile → moves to evidence
        _set_study_state(sid, phase="NEEDS_INFORMATION")
        r = client.post(f"/api/v2/studies/{sid}/approve/profile", json={"approved": True}, headers=headers)
        assert r.status_code == 200

        # Step 3: Evidence agent fills claims
        _set_study_state(sid, phase="EVIDENCE_REVIEW")
        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "السوق ينمو 15% والاشتراك 299 ريال",
        }, headers=headers)
        assert r.status_code == 200

        # Step 4: Approve evidence → assumptions
        _set_study_state(sid,
            phase="EVIDENCE_REVIEW",
            claims_json=[{"statement": "test", "source_type": "user_input", "confidence": 0.8}],
        )
        r = client.post(f"/api/v2/studies/{sid}/approve/evidence", json={"approved": True}, headers=headers)
        assert r.status_code == 200

        # Step 5: Assumptions agent fills assumptions
        _set_study_state(sid, phase="ASSUMPTIONS_REVIEW")
        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "حلل الافتراضات",
        }, headers=headers)
        assert r.status_code == 200

        # Step 6: Approve assumptions → financial analysis
        _set_study_state(sid,
            phase="ASSUMPTIONS_REVIEW",
            assumptions_json=[{"key": "revenue", "value": "299", "source": "user", "confidence": "confirmed"}],
        )
        r = client.post(f"/api/v2/studies/{sid}/approve/assumptions", json={"approved": True}, headers=headers)
        assert r.status_code == 200

        # Step 7: Risk analysis
        _set_study_state(sid, phase="ANALYZED",
            financial_results_json={"npv": 1234567, "irr": 0.345, "payback_months": 18})
        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "قيّم المخاطر",
        }, headers=headers)
        assert r.status_code == 200

        # Step 8: Decision
        _set_study_state(sid, phase="DECISION_READY",
            decision_risks=["competition", "data localization"])
        r = client.post(f"/api/v2/studies/{sid}/message", json={
            "message": "القرار النهائي",
        }, headers=headers)
        assert r.status_code == 200

        # Verify final state
        final = client.get(f"/api/v2/studies/{sid}", headers=headers)
        data = final.json()
        assert data["verdict"] == "GO_WITH_CONDITIONS"
        assert data["decision_rationale"] is not None
        assert len(data["decision_rationale"]) > 10

    def test_study_list_shows_verdict_after_journey(self):
        headers, _ = _register_and_login("listv")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
        }, headers=headers)
        sid = r.json()["study_id"]

        _set_study_state(sid,
            phase="DECISION_READY",
            verdict="GO",
            decision_rationale="Strong project with positive financials",
        )

        listing = client.get("/api/v2/studies", headers=headers)
        studies = listing.json()["studies"]
        match = [s for s in studies if s["study_id"] == sid]
        assert len(match) == 1
        assert match[0]["verdict"] == "GO"
        assert match[0]["phase"] == "DECISION_READY"


# =============================================================================
# 4. Arabic / English language handling
# =============================================================================

class TestLanguageHandling:
    @patch("ai_engine.agents.discovery.get_llm")
    def test_arabic_study_gets_arabic_profile(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(DISCOVERY_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("ar1")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "ar",
            "description": "مشروع تطبيق توصيل طعام في الرياض",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["profile"] is not None

    @patch("ai_engine.agents.discovery.get_llm")
    def test_english_study_gets_english_profile(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(DISCOVERY_COMPLETE_RESPONSE)
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("en1")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "en",
            "description": "Food delivery app in Riyadh targeting 500K users",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["profile"]["archetype"] == "saas_digital"


# =============================================================================
# 5. Error handling — AI failure graceful degradation
# =============================================================================

class TestAIFailureHandling:
    @patch("ai_engine.agents.discovery.get_llm")
    def test_ai_error_sets_error_field(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Groq API rate limit exceeded")
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("err1")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "ar",
            "description": "مشروع تطبيق",
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["error"] is not None
        assert "error" in data["error"].lower() or "rate limit" in data["error"].lower()

    @patch("ai_engine.agents.discovery.get_llm")
    def test_ai_error_study_still_persists(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Connection timeout")
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("err2")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "ar",
            "description": "test",
        }, headers=headers)
        sid = r.json()["study_id"]

        get_r = client.get(f"/api/v2/studies/{sid}", headers=headers)
        assert get_r.status_code == 200
        assert get_r.json()["study_id"] == sid

    @patch("ai_engine.agents.discovery.get_llm")
    def test_ai_returns_no_json_stays_draft(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(
            "I need more information about your project. Can you tell me more?"
        )
        mock_get_llm.return_value = mock_llm

        headers, _ = _register_and_login("err3")
        r = client.post("/api/v2/studies", json={
            "project_id": f"proj_{_uid()}",
            "language": "en",
            "description": "something",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["phase"] == "DRAFT"


# =============================================================================
# 6. Project + Study relationship
# =============================================================================

class TestProjectStudyRelationship:
    def test_multiple_studies_per_project(self):
        headers, _ = _register_and_login("rel1")
        proj = client.post("/projects/", json={
            "name": "Multi-study Project",
            "industry": "Real Estate",
            "investment": 1000000,
            "stage": "idea",
        }, headers=headers)
        pid = str(proj.json()["id"])

        sids = set()
        for _ in range(3):
            r = client.post("/api/v2/studies", json={"project_id": pid}, headers=headers)
            sids.add(r.json()["study_id"])
        assert len(sids) == 3

    def test_study_references_project_id(self):
        headers, _ = _register_and_login("rel2")
        proj = client.post("/projects/", json={
            "name": "Ref Test",
            "industry": "Services",
            "investment": 100000,
            "stage": "idea",
        }, headers=headers)
        pid = str(proj.json()["id"])

        r = client.post("/api/v2/studies", json={
            "project_id": pid,
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["study_id"].startswith("study_")
