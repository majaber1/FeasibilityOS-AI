"""Phase 7C.1 — MISA live Saudi source slice (Monsha'at excluded)."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import DB_ENABLED, SessionLocal, init_db  # noqa: E402
from app import models  # noqa: E402
from app import auth as security  # noqa: E402
from app.main import app  # noqa: E402
from app.api.auth import _ensure_roles  # noqa: E402
from app.integrations.research.page_reader import PageFetchError  # noqa: E402
from app.integrations.research.security import UrlSecurityError, validate_url  # noqa: E402
from app.integrations.sources.gastat import GastatConnector, DEFAULT_GASTAT_URLS  # noqa: E402
from app.integrations.sources.misa import (  # noqa: E402
    DEFAULT_MISA_URLS,
    MISA_ALLOWED_DOMAINS,
    MisaConnector,
)
from app.integrations.sources.knowledge_adapter import (  # noqa: E402
    find_existing_by_content_hash,
    ingest_source_document,
)
from app.integrations.mcp.boundary import (  # noqa: E402
    build_mcp_server,
    list_bound_tool_names,
    source_fetch_payload,
    source_status_payload,
)
from app.services import source_registry_service as registry  # noqa: E402
from app.services import knowledge_service as ks  # noqa: E402

client = TestClient(app)
PASSWORD = "Sup3rSecret!"
LIVE_MISA_URLS = list(DEFAULT_MISA_URLS)


def setup_module(module):
    assert DB_ENABLED is True
    init_db()


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"


def _make_admin() -> tuple[str, int]:
    email = _email("admin7c1misa")
    db = SessionLocal()
    try:
        _ensure_roles(db)
        user = models.User(
            email=email,
            hashed_password=security.hash_password(PASSWORD),
            full_name="Phase7C1 MISA Admin",
            role_key="admin",
            locale="en",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return email, int(user.id)
    finally:
        db.close()


def _make_user() -> tuple[str, int]:
    email = _email("user7c1misa")
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Tester"},
    )
    assert resp.status_code in (200, 201), resp.text
    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(email=email).one()
        return email, int(u.id)
    finally:
        db.close()


def _token(email: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_b_misa_connector_contract_live():
    connector = MisaConnector(enabled=True)
    health = connector.health()
    assert health.status.value == "healthy", health.detail
    meta = connector.source_metadata
    assert meta["live"] is True
    assert meta["api"] is None
    assert meta["registry_key"] == "misa"
    assert "misa.gov.sa" in meta["allowed_domains"]
    docs = connector.retrieve(url=LIVE_MISA_URLS[0])
    assert len(docs) == 1
    doc = docs[0]
    assert doc.url and "misa.gov.sa" in doc.url
    assert doc.content and len(doc.content) > 100
    assert doc.content_hash
    assert doc.provenance.connector_id == connector.connector_id == "live.misa"
    assert doc.provenance.registry_key == "misa"
    assert doc.retrieved_at is not None
    assert doc.sector is None


def test_c_misa_domain_validation():
    misa = MisaConnector(enabled=True)
    with pytest.raises((UrlSecurityError, PageFetchError)):
        misa.fetch_url("https://example.com/fake-misa")
    with pytest.raises((UrlSecurityError, PageFetchError)):
        misa.fetch_url("https://evil.misa.gov.sa.attacker.com/x")


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.5/",
        "http://192.168.1.10/",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://misa.gov.sa/",
    ],
)
def test_d_misa_ssrf_protection(bad_url):
    with pytest.raises(UrlSecurityError):
        validate_url(bad_url, allowed_domains=MISA_ALLOWED_DOMAINS, resolve_dns=False)


def test_e_misa_provenance_preservation():
    misa_doc = MisaConnector().fetch_url(LIVE_MISA_URLS[0])
    ok, errors = MisaConnector().validate_provenance(misa_doc)
    assert ok, errors
    assert misa_doc.provenance.registry_key == "misa"
    assert misa_doc.provenance.connector_id == "live.misa"
    assert misa_doc.url and misa_doc.content_hash
    assert misa_doc.provenance.original_url
    assert misa_doc.provenance.retrieval_method == "http_html"


def test_f_g_misa_knowledge_ingest_and_idempotency():
    _admin_email, admin_id = _make_admin()
    db = SessionLocal()
    try:
        registry.ensure_seed_sources(db)
        row = registry.get_source_by_key(db, "misa")
        assert row is not None
        assert row.connector_type == "live"
        assert row.enabled is True

        misa_doc = MisaConnector().fetch_url(LIVE_MISA_URLS[0])
        kd1 = ingest_source_document(db, owner_id=admin_id, document=misa_doc)
        ext = (kd1.assumptions or {}).get("external_source") or {}
        assert (ext.get("provenance") or {}).get("registry_key") == "misa"
        assert ext.get("content_hash") == misa_doc.content_hash
        kd2 = ingest_source_document(db, owner_id=admin_id, document=misa_doc)
        assert kd2.id == kd1.id
        assert getattr(kd2, "_idempotent_reuse", False) is True
    finally:
        db.close()


def test_i_misa_tenant_isolation():
    _admin_email, admin_id = _make_admin()
    _other_email, other_id = _make_user()
    db = SessionLocal()
    try:
        doc = MisaConnector().fetch_url(LIVE_MISA_URLS[1])
        kd = ingest_source_document(db, owner_id=admin_id, document=doc)
        assert kd.id
        assert (
            find_existing_by_content_hash(db, owner_id=other_id, content_hash=doc.content_hash)
            is None
        )
        other_docs = ks.list_documents(db, owner_id=other_id)
        assert all(
            (d.assumptions or {}).get("external_source", {}).get("content_hash") != doc.content_hash
            for d in other_docs
        )
    finally:
        db.close()


def test_business_scenario_b_foreign_investment_misa_live():
    _admin_email, admin_id = _make_admin()
    db = SessionLocal()
    try:
        connector = MisaConnector()
        ingested_ids = []
        for url in LIVE_MISA_URLS:
            docs = connector.retrieve(url=url)
            assert docs, f"no live MISA doc for {url}"
            kd = ingest_source_document(db, owner_id=admin_id, document=docs[0])
            ingested_ids.append(kd.id)

        pack = ks.retrieve_evidence(
            db,
            owner_id=admin_id,
            query=(
                "What does MISA say about the National Investment Strategy "
                "and investment development support?"
            ),
            top_k=6,
        )
        citations = pack.get("citations") or pack.get("evidence") or []
        assert citations, pack
        cited_ids = {
            str(c.get("document_id") or c.get("source_document_id") or "")
            for c in citations
        }
        assert cited_ids.intersection({str(i) for i in ingested_ids}) or any(
            "investment" in (c.get("content") or c.get("claim") or "").lower()
            for c in citations
        ), pack
    finally:
        db.close()


def test_api_sync_documents_and_mcp_misa():
    admin_email, _admin_id = _make_admin()
    db = SessionLocal()
    try:
        registry.ensure_seed_sources(db)
        misa_row = registry.get_source_by_key(db, "misa")
        assert misa_row is not None
        assert registry.connector_for_source(misa_row) is not None
        misa_id = misa_row.id
        mon = registry.get_source_by_key(db, "monshaat")
        assert mon is None or registry.connector_for_source(mon) is None
    finally:
        db.close()

    tok = _token(admin_email)
    sync = client.post(
        f"/api/v2/sources/{misa_id}/sync",
        headers=_auth(tok),
        json={"urls": [LIVE_MISA_URLS[0]]},
    )
    assert sync.status_code == 200, sync.text
    body = sync.json()
    assert body["success"] is True
    assert body["count"] >= 1

    docs_resp = client.get(
        f"/api/v2/sources/{misa_id}/documents",
        headers=_auth(tok),
    )
    assert docs_resp.status_code == 200, docs_resp.text
    assert docs_resp.json()["count"] >= 1

    tools = list_bound_tool_names(build_mcp_server())
    assert "source_status" in tools
    assert "source_fetch" in tools
    misa_status = source_status_payload("misa")
    assert misa_status["ok"] is True
    assert "financial" in misa_status["forbidden"]
    fetched = source_fetch_payload("misa", {"url": LIVE_MISA_URLS[1]})
    assert fetched["count"] == 1
    assert fetched["documents"][0]["provenance"]["registry_key"] == "misa"


def test_j_v3_regression_smoke():
    from app.services import financial_health  # noqa: F401
    from app.services import financial_projection  # noqa: F401
    from app.services import decision_engine  # noqa: F401
    from app.api.v2 import sources as v2_sources  # noqa: F401

    assert hasattr(v2_sources, "sync_source")
    assert hasattr(v2_sources, "list_source_documents")


def test_k_phase7b_gastat_regression():
    connector = GastatConnector(enabled=True)
    health = connector.health()
    assert health.status.value == "healthy", health.detail
    docs = connector.retrieve(url=DEFAULT_GASTAT_URLS[0])
    assert len(docs) == 1
    assert docs[0].provenance.registry_key == "gastat"
    status = source_status_payload("gastat")
    assert status["ok"] is True
