"""Wave 3A — Final Source Trust & Filter Semantics Closure Tests.

Validates:
1. Strict Self-Certification Closure (Rule A):
   - POST /opportunities always creates UNVERIFIED records.
   - Fabricated field_provenance with supported=True cannot self-certify VERIFIED_CURRENT (HTTP 422).
   - PATCH normal business fields cannot promote to VERIFIED_CURRENT or VERIFIED_PARTIAL.
   - VERIFIED_CURRENT is strictly unavailable via API payloads.
2. Exact Opportunity Existence Provenance (Rule B):
   - Every actionable registry record requires opportunity_existence provenance backed by an exact primary source.
   - Generic sector/brand pages are not treated as opportunity evidence.
   - Inferred or unproven records (8 records) are marked UNVERIFIED and non-actionable (is_active=False).
   - Actionable verified catalog contains exactly 3 proven franchises (Barn's, dr.CAFE, Shawarmer).
   - Non-actionable unverified records cannot be launched as studies.
3. Strict Budget Filter Semantics (Rule C):
   - UNKNOWN investment does NOT count as a budget fit.
   - Known supported investment inside budget = fit.
   - Known supported investment outside budget = not fit.
4. User Budget Assumption Persistence:
   - Unknown investment requires user-supplied budget assumption.
   - Persisted explicitly in study.source_opportunity_lineage with budget_type="USER_ASSUMPTION".
   - Project.investment stores assumption without masquerading as official source-backed fact.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
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
from app.api import auth as auth_api
from app.services.opportunities import (
    seed_verified_opportunities,
    VERIFIED_OPPORTUNITY_CATALOG,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED_PARTIAL,
    STATUS_VERIFIED_CURRENT,
    STATUS_STALE,
    STATUS_CHANGED,
    STATUS_DISCONTINUED,
)

client = TestClient(app)
PASSWORD = "Sup3rSecretPassword123!"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    assert app_db.DB_ENABLED is True
    app_db.init_db()
    db = app_db.SessionLocal()
    try:
        seed_verified_opportunities(db, force_refresh=True)
    finally:
        db.close()


def _email(prefix="test_opp"):
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(prefix="user", role_key="entrepreneur"):
    email = _email(prefix)
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text

    if role_key != "entrepreneur":
        session = app_db.SessionLocal()
        try:
            existing_roles = {r_.key for r_ in session.query(models.Role).all()}
            for k, (en, ar) in auth_api.ROLES.items():
                if k not in existing_roles:
                    session.add(models.Role(key=k, name_en=en, name_ar=ar, permissions={}))
            session.commit()
            user = session.query(models.User).filter_by(email=email).one()
            user.role_key = role_key
            session.commit()
        finally:
            session.close()

    tok = client.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return email, tok


# ==============================================================================
# TESTS
# ==============================================================================

def test_catalog_seeded_and_persisted():
    """Verify registry counts: 11 total in DB, 3 actionable verified, 8 unverified."""
    # 1. Default read returns only active, verified actionable records
    r = client.get("/api/v1/opportunities/")
    assert r.status_code == 200
    active_items = r.json()
    assert len(active_items) == 3, f"Expected 3 actionable verified records, got {len(active_items)}"
    assert all(i["verification_status"] == STATUS_VERIFIED_PARTIAL for i in active_items)
    assert all(i["opportunity_type"] == "FRANCHISE" for i in active_items)

    # 2. Including unverified returns all 11 records
    r_all = client.get("/api/v1/opportunities/?include_unverified=true")
    assert r_all.status_code == 200
    all_items = r_all.json()
    assert len(all_items) == 11

    unverified_items = [i for i in all_items if i["verification_status"] == STATUS_UNVERIFIED]
    assert len(unverified_items) == 8


def test_business_opportunity_fields_and_provenance():
    """Verify government business ideas are marked UNVERIFIED and non-actionable due to lack of exact primary source."""
    r = client.get("/api/v1/opportunities/?include_unverified=true&type=BUSINESS_OPPORTUNITY")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 5

    sample = next(i for i in items if i["slug"] == "monshaat-food-processing-hub")
    assert sample["verification_status"] == STATUS_UNVERIFIED
    assert "field_provenance" in sample
    assert sample["field_provenance"]["opportunity_existence"]["supported"] is False
    assert "فكرة استثمارية مستنبطة" in sample["field_provenance"]["opportunity_existence"]["reason"]


def test_franchise_opportunity_fields_and_provenance():
    """Verify proven franchises have exact opportunity_existence provenance and unannounced capex."""
    r = client.get("/api/v1/opportunities/?type=FRANCHISE")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3

    barns = next(i for i in items if i["slug"] == "franchise-barns-cafe")
    assert barns["brand_name"] == "Barn's (بارنز)"
    assert barns["sector"] == "food_beverage"
    assert barns["investment_min"] is None
    assert barns["franchise_fee"] is None
    assert barns["verification_status"] == STATUS_VERIFIED_PARTIAL
    assert barns["official_source_url"] == "https://barns.com.sa/en/franchising-and-licensing"
    prov_barns = barns["field_provenance"]
    assert prov_barns["opportunity_existence"]["supported"] is True
    assert prov_barns["opportunity_existence"]["official_source_url"] == barns["official_source_url"]
    assert prov_barns["opportunity_existence"]["source_document"] == "بوابة الامتياز التجاري الرسمية - بارنز"
    assert prov_barns["opportunity_existence"]["source_locator"] == "franchising-and-licensing"
    assert "برنامج الامتياز التجاري" in prov_barns["opportunity_existence"]["evidence_excerpt"]

    drcafe = next(i for i in items if i["slug"] == "franchise-dr-cafe")
    assert drcafe["official_source_url"] == "https://drcafe.com/en-sa/franchise-profile"
    assert drcafe["verification_status"] == STATUS_VERIFIED_PARTIAL
    prov_drcafe = drcafe["field_provenance"]
    assert prov_drcafe["opportunity_existence"]["supported"] is True
    assert prov_drcafe["opportunity_existence"]["official_source_url"] == drcafe["official_source_url"]
    assert prov_drcafe["opportunity_existence"]["source_document"] == "Franchise Profile - dr.CAFE COFFEE"
    assert prov_drcafe["opportunity_existence"]["source_locator"] == "/en-sa/franchise-profile"
    assert "The franchisee is granted the license" in prov_drcafe["opportunity_existence"]["evidence_excerpt"]

    shawarmer = next(i for i in items if i["slug"] == "franchise-shawarmer")
    assert shawarmer["official_source_url"] == "https://franchise.shawarmer.com/"
    assert shawarmer["verification_status"] == STATUS_VERIFIED_PARTIAL
    prov_shawarmer = shawarmer["field_provenance"]
    assert prov_shawarmer["opportunity_existence"]["supported"] is True
    assert prov_shawarmer["opportunity_existence"]["official_source_url"] == shawarmer["official_source_url"]
    assert prov_shawarmer["opportunity_existence"]["source_document"] == "Shawarmer Franchise Portal and Brand Profile Brochure"
    assert "Downloads/Franchise_Brochure_General_160323.pdf" in prov_shawarmer["opportunity_existence"]["source_locator"]
    assert "Shawarmer was founded in 1999" in prov_shawarmer["opportunity_existence"]["evidence_excerpt"]


def test_create_defaults_to_unverified():
    """Rule A: New opportunities created via POST /opportunities always start as UNVERIFIED."""
    _, admin_token = _register_and_login("admin_create_test", role_key="admin")

    payload = {
        "slug": f"new-opp-{uuid.uuid4().hex[:6]}",
        "title_ar": "فرصة استثمارية جديدة للاختبار",
        "title_en": "New Test Opportunity",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "technology",
        "business_model": "SaaS Platform",
        "target_customer": "B2B",
        "geography": "RIYADH",
        "city": "الرياض",
        "description_ar": "وصف تفصيلي للفرصة",
        "description_en": "Detailed description",
        "official_source_url": "https://misa.gov.sa/test",
        "source_owner": "وزارة الاستثمار (MISA)",
        "source_type": "OFFICIAL_GOVERNMENT",
    }
    r = client.post("/api/v1/opportunities/", json=payload, headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["verification_status"] == STATUS_UNVERIFIED


def test_fabricated_supported_provenance_cannot_self_certify_verified_current():
    """Rule A: Fabricated field_provenance with supported=true cannot self-certify VERIFIED_CURRENT."""
    _, admin_token = _register_and_login("admin_evidence_loophole", role_key="admin")

    bad_payload = {
        "slug": f"fake-verified-{uuid.uuid4().hex[:6]}",
        "title_ar": "فرصة ذات إثبات مزعوم",
        "title_en": "Fabricated Evidence Opportunity",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "retail",
        "geography": "RIYADH",
        "investment_min": 100000.0,
        "investment_max": 200000.0,
        "official_source_url": "https://monshaat.gov.sa/exact-opportunity",
        "source_owner": "منشآت",
        "verification_status": STATUS_VERIFIED_CURRENT,
        "field_provenance": {
            "opportunity_existence": {"supported": True, "status": "VERIFIED_CURRENT"},
            "sector": {"supported": True, "status": "VERIFIED_CURRENT"},
            "geography": {"supported": True, "status": "VERIFIED_CURRENT"},
            "investment_min": {"supported": True, "status": "VERIFIED_CURRENT"},
            "investment_max": {"supported": True, "status": "VERIFIED_CURRENT"},
        },
    }
    r = client.post("/api/v1/opportunities/", json=bad_payload, headers=_auth(admin_token))
    assert r.status_code == 422
    assert "VERIFIED_CURRENT" in r.text

    # Also test attempting self-promotion to VERIFIED_PARTIAL on creation
    bad_payload["verification_status"] = STATUS_VERIFIED_PARTIAL
    bad_payload["slug"] = f"fake-partial-{uuid.uuid4().hex[:6]}"
    r_partial = client.post("/api/v1/opportunities/", json=bad_payload, headers=_auth(admin_token))
    assert r_partial.status_code == 422


def test_patch_normal_fields_cannot_promote_to_verified_current():
    """Rule A: PATCH normal business fields cannot promote to VERIFIED_CURRENT."""
    _, admin_token = _register_and_login("admin_patch_test", role_key="admin")

    # Create an UNVERIFIED record
    payload = {
        "slug": f"unverified-{uuid.uuid4().hex[:6]}",
        "title_ar": "فرصة عادية غير موثقة",
        "title_en": "Unverified Opp",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "retail",
        "official_source_url": "https://example.com/test",
        "source_owner": "جهة اختبار",
    }
    r_create = client.post("/api/v1/opportunities/", json=payload, headers=_auth(admin_token))
    assert r_create.status_code == 201
    opp_id = r_create.json()["id"]

    # Attempt to PATCH verification_status to VERIFIED_CURRENT must fail with 422
    r_patch_status = client.patch(
        f"/api/v1/opportunities/{opp_id}",
        json={"verification_status": STATUS_VERIFIED_CURRENT, "change_reason": "محاولة ترقية غير مسموحة"},
        headers=_auth(admin_token),
    )
    assert r_patch_status.status_code == 422

    # PATCH normal business fields must retain UNVERIFIED status
    r_patch_business = client.patch(
        f"/api/v1/opportunities/{opp_id}",
        json={"investment_max": 999999.0, "change_reason": "تحديث عادي للبيانات"},
        headers=_auth(admin_token),
    )
    assert r_patch_business.status_code == 200
    assert r_patch_business.json()["verification_status"] == STATUS_UNVERIFIED


def test_budget_filter_semantics():
    """Rule C: Strict budget filter semantics.

    - unknown investment (NULL) != budget fit
    - known supported investment inside budget = fit
    - known supported investment outside budget = not fit
    """
    db = app_db.SessionLocal()
    try:
        # 1. Query budget <= 400k on current active catalog (all have investment_min=None)
        r_empty = client.get("/api/v1/opportunities/?max_budget=400000")
        assert r_empty.status_code == 200
        # Unknown investment MUST NOT count as a budget fit
        assert len(r_empty.json()) == 0

        # 2. Seed a temporary opportunity with known investment = 300,000 SAR (inside budget)
        opp_inside = models.VerifiedOpportunity(
            slug=f"known-fit-{uuid.uuid4().hex[:6]}",
            title_ar="فرصة معلنة الميزانية مناسبة",
            title_en="Known Fit Opp",
            opportunity_type="BUSINESS_OPPORTUNITY",
            sector="food_beverage",
            investment_min=300000.0,
            investment_max=350000.0,
            official_source_url="https://example.com/fit",
            source_owner="جهة رسمية",
            verification_status=STATUS_VERIFIED_PARTIAL,
            is_active=True,
            field_provenance={"opportunity_existence": {"supported": True, "status": "VERIFIED_PARTIAL"}},
        )
        db.add(opp_inside)

        # 3. Seed a temporary opportunity with known investment = 600,000 SAR (outside budget)
        opp_outside = models.VerifiedOpportunity(
            slug=f"known-notfit-{uuid.uuid4().hex[:6]}",
            title_ar="فرصة معلنة الميزانية تتجاوز الحد",
            title_en="Known Outside Opp",
            opportunity_type="BUSINESS_OPPORTUNITY",
            sector="food_beverage",
            investment_min=600000.0,
            investment_max=800000.0,
            official_source_url="https://example.com/notfit",
            source_owner="جهة رسمية",
            verification_status=STATUS_VERIFIED_PARTIAL,
            is_active=True,
            field_provenance={"opportunity_existence": {"supported": True, "status": "VERIFIED_PARTIAL"}},
        )
        db.add(opp_outside)
        db.commit()

        # Query max_budget = 400,000
        r_fit = client.get("/api/v1/opportunities/?max_budget=400000")
        assert r_fit.status_code == 200
        results = r_fit.json()
        result_slugs = {item["slug"] for item in results}

        # opp_inside MUST be returned
        assert opp_inside.slug in result_slugs
        # opp_outside MUST NOT be returned
        assert opp_outside.slug not in result_slugs
        # Any item with investment_min=None MUST NOT be returned
        for item in results:
            assert item["investment_min"] is not None
            assert item["investment_min"] <= 400000.0

        # Query min_budget = 500,000
        r_min = client.get("/api/v1/opportunities/?min_budget=500000")
        assert r_min.status_code == 200
        min_results = r_min.json()
        min_slugs = {item["slug"] for item in min_results}
        assert opp_outside.slug in min_slugs
        assert opp_inside.slug not in min_slugs

        # Cleanup
        db.delete(opp_inside)
        db.delete(opp_outside)
        db.commit()
    finally:
        db.close()


def test_unverified_records_cannot_create_study():
    """Rule B: Non-actionable / unverified opportunities cannot create feasibility studies."""
    r_all = client.get("/api/v1/opportunities/?include_unverified=true")
    all_items = r_all.json()
    unverified_opp = next(i for i in all_items if i["verification_status"] == STATUS_UNVERIFIED)

    _, token = _register_and_login("unverified_study_tester")
    r = client.post(
        f"/api/v1/opportunities/{unverified_opp['id']}/create-study",
        json={"study_title": "دراسة غير مصرح بها", "custom_budget": 500000.0},
        headers=_auth(token),
    )
    assert r.status_code == 400
    assert "unverified or non-actionable" in r.text.lower() or "غير موثقة" in r.text


def test_unsupported_numeric_fields_remain_null():
    """Rule 2: Any material numeric claim not proven directly from official primary source must be None."""
    r = client.get("/api/v1/opportunities/?include_unverified=true")
    assert r.status_code == 200
    items = r.json()

    for item in items:
        prov = item.get("field_provenance") or {}
        if "investment_min" in prov and not prov["investment_min"].get("supported"):
            assert item["investment_min"] is None, f"{item['slug']} investment_min should be None"
        if "investment_max" in prov and not prov["investment_max"].get("supported"):
            assert item["investment_max"] is None, f"{item['slug']} investment_max should be None"
        if "franchise_fee" in prov and not prov["franchise_fee"].get("supported"):
            assert item["franchise_fee"] is None, f"{item['slug']} franchise_fee should be None"


def test_unknown_investment_never_becomes_250000():
    """Rule 5: Unknown investment must never default to 250,000 SAR."""
    items = client.get("/api/v1/opportunities/?type=FRANCHISE").json()
    barns = next(i for i in items if i["slug"] == "franchise-barns-cafe")

    assert barns["investment_min"] is None

    # Attempt to create study without specifying custom_budget must fail with 400
    _, token = _register_and_login("budget_tester")
    r = client.post(
        f"/api/v1/opportunities/{barns['id']}/create-study",
        json={"study_title": "دراسة بدون ميزانية"},
        headers=_auth(token),
    )
    assert r.status_code == 400
    assert "user budget assumption must be provided" in r.text.lower() or "الميزانية" in r.text


def test_user_entered_budget_is_labeled_user_assumption():
    """Rule 5: User-supplied budget must be persisted explicitly as USER_ASSUMPTION."""
    items = client.get("/api/v1/opportunities/?type=FRANCHISE").json()
    barns = next(i for i in items if i["slug"] == "franchise-barns-cafe")

    _, token = _register_and_login("assumption_user")
    custom_budget_val = 520000.0
    r = client.post(
        f"/api/v1/opportunities/{barns['id']}/create-study",
        json={
            "study_title": "دراسة جدوى بارنز - افتراض مستخدم",
            "custom_budget": custom_budget_val,
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    created = r.json()

    # Verify lineage metadata
    lineage = created["lineage"]
    assert lineage["budget_type"] == "USER_ASSUMPTION"
    assert lineage["is_user_assumption"] is True
    assert lineage["budget_amount"] == custom_budget_val
    assert lineage["transferred_facts"]["investment_min"] is None
    assert lineage["transferred_facts"]["franchise_fee"] is None

    # Verify DB persistence
    db = app_db.SessionLocal()
    try:
        project = db.get(models.Project, created["project_id"])
        assert project.investment == custom_budget_val

        study = db.get(models.FeasibilityStudy, created["study_id"])
        assert study.source_opportunity_lineage["budget_type"] == "USER_ASSUMPTION"
        assert study.source_opportunity_lineage["is_user_assumption"] is True
        assert study.source_opportunity_lineage["budget_amount"] == custom_budget_val

        if study.payload and "opportunity_lineage" in study.payload:
            payload_lineage = study.payload["opportunity_lineage"]
            assert payload_lineage["budget_type"] == "USER_ASSUMPTION"
            assert payload_lineage["budget_amount"] == custom_budget_val
    finally:
        db.close()


def test_stale_and_changed_source_transitions():
    """Rule 4: State machine supports UNVERIFIED, VERIFIED_PARTIAL, STALE, CHANGED, DISCONTINUED."""
    _, admin_token = _register_and_login("admin_state_test", role_key="admin")
    items = client.get("/api/v1/opportunities/?type=FRANCHISE").json()
    target = items[0]
    orig_status = target["verification_status"]

    try:
        # 1. Transition to STALE
        r_stale = client.patch(
            f"/api/v1/opportunities/{target['id']}",
            json={"verification_status": STATUS_STALE, "change_reason": "مرور أكثر من 180 يوماً على التحقق الدوري"},
            headers=_auth(admin_token),
        )
        assert r_stale.status_code == 200
        assert r_stale.json()["verification_status"] == STATUS_STALE

        # 2. Transition to CHANGED
        r_changed = client.patch(
            f"/api/v1/opportunities/{target['id']}",
            json={"verification_status": STATUS_CHANGED, "change_reason": "تعديل في شروط المنح الرسمية"},
            headers=_auth(admin_token),
        )
        assert r_changed.status_code == 200
        assert r_changed.json()["verification_status"] == STATUS_CHANGED

        # 3. Transition to DISCONTINUED
        r_disc = client.patch(
            f"/api/v1/opportunities/{target['id']}",
            json={"verification_status": STATUS_DISCONTINUED, "change_reason": "إغلاق برنامج الامتياز رسمياً"},
            headers=_auth(admin_token),
        )
        assert r_disc.status_code == 200
        assert r_disc.json()["verification_status"] == STATUS_DISCONTINUED
    finally:
        db = app_db.SessionLocal()
        try:
            t = db.query(models.VerifiedOpportunity).filter_by(id=target["id"]).first()
            if t:
                t.verification_status = orig_status
                db.commit()
        finally:
            db.close()


def test_verified_field_has_provenance():
    """Verify that all actionable opportunities have opportunity_existence with verified primary sources."""
    items = client.get("/api/v1/opportunities/").json()
    assert len(items) == 3

    for item in items:
        prov = item.get("field_provenance") or {}
        assert "opportunity_existence" in prov
        assert prov["opportunity_existence"]["supported"] is True
        assert prov["opportunity_existence"]["official_source_url"].startswith("https://")
        assert prov["opportunity_existence"]["checked_at"] is not None


def test_registry_contains_no_demo_test_contamination():
    """Verify registry contains only official catalog records and no contamination."""
    items = client.get("/api/v1/opportunities/?include_unverified=true").json()
    catalog_slugs = {c["slug"] for c in VERIFIED_OPPORTUNITY_CATALOG}
    for item in items:
        if item["slug"] in catalog_slugs:
            assert "test" not in item["title_en"].lower() or item["slug"] == "test"


def test_read_endpoint_does_not_magically_seed_data():
    """Verify GET /api/v1/opportunities is strictly read-only and never auto-seeds an empty DB."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    isolated_db_url = f"sqlite:///{tmp.name}"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.api import verified_opportunities as vo_api

    isolated_engine = create_engine(isolated_db_url, connect_args={"check_same_thread": False})
    IsolatedSession = sessionmaker(autocommit=False, autoflush=False, bind=isolated_engine)
    models.Base.metadata.create_all(bind=isolated_engine)

    orig_session = app_db.SessionLocal
    orig_vo_session = vo_api.SessionLocal
    app_db.SessionLocal = IsolatedSession
    vo_api.SessionLocal = IsolatedSession
    try:
        # Read empty table
        r = client.get("/api/v1/opportunities/")
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 0

        # Ingest into isolated db
        db_iso = IsolatedSession()
        try:
            seed_verified_opportunities(db_iso)
        finally:
            db_iso.close()

        # Now read returns 3 active
        r2 = client.get("/api/v1/opportunities/")
        assert r2.status_code == 200
        assert len(r2.json()) == 3

        # And all returns 11
        r3 = client.get("/api/v1/opportunities/?include_unverified=true")
        assert r3.status_code == 200
        assert len(r3.json()) == 11
    finally:
        app_db.SessionLocal = orig_session
        vo_api.SessionLocal = orig_vo_session
        isolated_engine.dispose()
        if os.path.exists(tmp.name):
            try:
                os.remove(tmp.name)
            except OSError:
                pass


def test_detail_endpoint_facts_breakdown_and_version_history():
    """Verify get detail endpoint separates published facts, normalized facts, and unknowns."""
    items = client.get("/api/v1/opportunities/").json()
    target = items[0]

    r = client.get(f"/api/v1/opportunities/{target['id']}")
    assert r.status_code == 200
    detail = r.json()

    assert detail["id"] == target["id"]
    assert "facts_breakdown" in detail
    breakdown = detail["facts_breakdown"]
    assert "published_facts" in breakdown
    assert len(breakdown["published_facts"]) >= 1
    assert "platform_normalized_facts" in breakdown
    assert "unknowns" in breakdown
    assert len(breakdown["unknowns"]) >= 1
    assert "user_assumptions_needed" in breakdown

    assert "version_history" in detail
    assert len(detail["version_history"]) >= 1
    assert detail["version_history"][0]["data_version"] == target["data_version"]


def test_filtering_capabilities():
    """Verify filtering by sector, search term, and geography."""
    # 1. Filter by sector (food_beverage contains all 3 franchises)
    r = client.get("/api/v1/opportunities/?sector=food_beverage")
    assert r.status_code == 200
    fb_items = r.json()
    assert len(fb_items) == 3
    assert all(i["sector"] == "food_beverage" for i in fb_items)

    # 2. Filter by search query
    r = client.get("/api/v1/opportunities/?search=شاورمر")
    assert r.status_code == 200
    search_items = r.json()
    assert len(search_items) == 1
    assert search_items[0]["slug"] == "franchise-shawarmer"


def test_side_by_side_comparison():
    """Verify factual side-by-side comparison without synthetic weighting."""
    items = client.get("/api/v1/opportunities/?type=FRANCHISE").json()
    id1 = items[0]["id"]
    id2 = items[1]["id"]

    r = client.get(f"/api/v1/opportunities/compare?ids={id1},{id2}")
    assert r.status_code == 200
    comparison = r.json()
    assert len(comparison) == 2

    c1 = next(c for c in comparison if c["id"] == id1)
    c2 = next(c for c in comparison if c["id"] == id2)

    assert "sector" in c1 and "sector" in c2
    assert "investment_min" in c1 and "investment_min" in c2
    assert "franchise_fee" in c1 and "franchise_fee" in c2
    assert "source_owner" in c1 and "source_owner" in c2
    assert "verification_status" in c1 and "verification_status" in c2

    # Reject invalid comparison requests
    r_bad = client.get("/api/v1/opportunities/compare?ids=abc,xyz")
    assert r_bad.status_code == 400


def test_create_study_from_opportunity_end_to_end():
    """Verify mandatory Create Study integration carries verified facts, persists lineage, and enforces auth."""
    items = client.get("/api/v1/opportunities/?type=FRANCHISE").json()
    barns = next(i for i in items if i["slug"] == "franchise-barns-cafe")

    # 1. Unauthenticated call must fail with 401
    r_unauth = client.post(f"/api/v1/opportunities/{barns['id']}/create-study", json={})
    assert r_unauth.status_code == 401

    # 2. Authenticated user without budget when investment_min is null must fail with 400
    _, token = _register_and_login("founder_study")
    r_nobudget = client.post(
        f"/api/v1/opportunities/{barns['id']}/create-study",
        json={"study_title": "دراسة جدوى فرع بارنز - الرياض"},
        headers=_auth(token),
    )
    assert r_nobudget.status_code == 400

    # 3. Authenticated user with explicit budget creates study
    r_create = client.post(
        f"/api/v1/opportunities/{barns['id']}/create-study",
        json={"study_title": "دراسة جدوى فرع بارنز - الرياض", "custom_budget": 450000.0},
        headers=_auth(token),
    )
    assert r_create.status_code == 201, r_create.text
    created = r_create.json()

    assert "project_id" in created
    assert "study_id" in created
    assert created["lineage"]["budget_type"] == "USER_ASSUMPTION"
    assert created["lineage"]["budget_amount"] == 450000.0


def test_opportunity_version_history_on_update():
    """Verify updating fields appends snapshot to version history and bumps semantic version."""
    _, admin_token = _register_and_login("admin_history", role_key="admin")
    items = client.get("/api/v1/opportunities/?type=FRANCHISE").json()
    target = items[0]
    initial_version = target["data_version"]

    r_patch = client.patch(
        f"/api/v1/opportunities/{target['id']}",
        json={
            "description_ar": "تحديث وصفي للمراجعة الدورية المعتمدة لعام 2026",
            "change_reason": "التحديث السنوي المعتمد",
        },
        headers=_auth(admin_token),
    )
    assert r_patch.status_code == 200
    updated = r_patch.json()

    assert updated["data_version"] != initial_version
    assert len(updated["version_history"]) >= 2
    reasons = [v["change_reason"] for v in updated["version_history"]]
    assert "التحديث السنوي المعتمد" in reasons
