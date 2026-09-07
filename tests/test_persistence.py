"""
Persistence tests. Runs against a throwaway SQLite database so CI needs no
external services, while exercising the exact ORM models and the projects
router's DB code path (DB_ENABLED=True).

Note: pytest may share one SQLite engine across test modules (app.db caches the
engine from the first DATABASE_URL seen). These tests are therefore written to
be isolation-safe: unique keys/emails and filtered assertions instead of global
row counts.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

# Configure a file-based SQLite DB BEFORE importing app.db so DB_ENABLED is True
# and all connections share the same database file.
if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_BACKEND))

from app import db as app_db  # noqa: E402
from app import models  # noqa: E402


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def test_project_round_trip():
    session = app_db.SessionLocal()
    try:
        p = models.Project(name="مصنع تمور", industry="agriculture", investment=750000, stage="mvp")
        session.add(p)
        session.commit()
        pid = p.id
    finally:
        session.close()

    session = app_db.SessionLocal()
    try:
        fetched = session.get(models.Project, pid)
        assert fetched is not None
        assert fetched.name == "مصنع تمور"
        assert fetched.investment == 750000
        assert fetched.created_at is not None
    finally:
        session.close()


def test_core_entities_persist():
    session = app_db.SessionLocal()
    try:
        org = models.Organization(name="Acme", name_ar="أكمي", sector="tech")
        session.add(org)
        session.flush()
        role = models.Role(key="tester_role", name_en="Tester", name_ar="مختبر", permissions={"projects": ["create"]})
        session.add(role)
        session.flush()
        user = models.User(
            email="persistence_probe@example.com",
            hashed_password="x",
            full_name="Probe",
            role_key="tester_role",
            organization_id=org.id,
        )
        session.add(user)
        prog = models.FundingProgram(
            slug="ntdp",
            program_name_en="NTDP",
            program_name_ar="المنشآت التقنية",
            provider="NTDP",
            provider_ar="البرنامج الوطني لتنمية تقنية المعلومات",
            program_type="DIRECT_LOAN",
            official_source_url="https://ntdp.gov.sa",
            source_owner="NTDP",
            verification_status="VERIFIED_CURRENT",
        )
        session.add(prog)
        idea = models.IdeaBankEntry(title_en="Cold chain SaaS", title_ar="سلسلة تبريد", industry="logistics")
        session.add(idea)
        session.commit()
        assert user.id is not None
    finally:
        session.close()

    session = app_db.SessionLocal()
    try:
        assert session.query(models.User).filter_by(email="persistence_probe@example.com").count() == 1
        assert session.query(models.FundingProgram).filter_by(slug="ntdp").one().program_name_ar == "المنشآت التقنية"
        assert session.query(models.IdeaBankEntry).filter_by(industry="logistics").count() >= 1
    finally:
        session.close()


def test_projects_router_persists_for_authenticated_owner():
    """The protected Projects API stores a real row for the authenticated owner
    and lets that owner read it back.

    The previous version of this test POSTed to /projects/ anonymously and
    expected 201; that is incompatible with the now-protected API (anonymous ->
    401). This replacement proves genuine authenticated persistence end to end:
    register -> login -> create with bearer token -> server assigns owner_id ->
    retrieve by owner -> confirm the row exists in the database.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    email = f"persist_owner_{uuid.uuid4().hex[:12]}@example.com"
    password = "Sup3rSecret!"

    reg = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Owner", "role_key": "entrepreneur"},
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Anonymous creation is rejected (documents the protected contract).
    anon = client.post("/projects/", json={"name": "Solar farm", "industry": "energy", "investment": 1000000, "stage": "growth"})
    assert anon.status_code == 401, anon.text

    # Authenticated creation succeeds and the server assigns ownership.
    created = client.post(
        "/projects/",
        json={"name": "Solar farm", "industry": "energy", "investment": 1000000, "stage": "growth"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["persisted"] is True
    assert body["owner_id"] == user_id
    new_id = body["id"]

    # The owner can read it back through the API.
    got = client.get(f"/projects/{new_id}", headers=headers)
    assert got.status_code == 200, got.text
    assert got.json()["name"] == "Solar farm"

    # And it appears in the owner's own listing.
    listing = client.get("/projects/", headers=headers)
    assert listing.status_code == 200
    assert any(p["id"] == new_id for p in listing.json())

    # It is truly persisted in the database with the correct owner.
    session = app_db.SessionLocal()
    try:
        row = session.get(models.Project, new_id)
        assert row is not None
        assert row.owner_id == user_id
        assert row.name == "Solar farm"
    finally:
        session.close()
