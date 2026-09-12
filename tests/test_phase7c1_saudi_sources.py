"""Phase 7C.1 — Monsha'at + MISA Saudi source expansion validation.

Covers required checks A–K (see docs/evidence/V4_PHASE7C1_SAUDI_SOURCES_VALIDATION.md).
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db as app_db  # noqa: E402
from app import models  # noqa: E402
from app import auth as security  # noqa: E402
from app.main import app  # noqa: E402
from app.integrations.research.page_reader import PageFetchError  # noqa: E402
from app.integrations.research.security import UrlSecurityError, validate_url  # noqa: E402
from app.integrations.sources.gastat import GastatConnector  # noqa: E402
from app.integrations.sources.monshaat import (  # noqa: E402
    DEFAULT_MONSHAAT_URLS,
    MONSHAAT_ALLOWED_DOMAINS,
    MonshaatConnector,
)
from app.integrations.sources.misa import (  # noqa: E402
    DEFAULT_MISA_URLS,
    MISA_ALLOWED_DOMAINS,
    MisaConnector,
)
from app.integrations.sources.knowledge_adapter import (  # noqa: E402
    find_existing_by_content_hash,
    ingest_source_document,
)
from app.integrations.sources.validation import compute_content_hash  # noqa: E402
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
MONSHAAT_FIXTURE_URLS = list(DEFAULT_MONSHAAT_URLS)


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"


def _make_admin() -> tuple[str, int]:
    from app.api.auth import _ensure_roles

    email = _email("admin7c1")
    session = app_db.SessionLocal()
    try:
        _ensure_roles(session)
        user = models.User(
            email=email,
            hashed_password=security.hash_password(PASSWORD),
            full_name="Phase7C1 Admin",
            role_key="admin",
            locale="en",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return email, int(user.id)
    finally:
        session.close()


def _make_user() -> tuple[str, int]:
    email = _email("user7c1")
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Tester"},
    )
    assert resp.status_code in (200, 201), resp.text
    session = app_db.SessionLocal()
    try:
        u = session.query(models.User).filter_by(email=email).one()
        return email, int(u.id)
    finally:
        session.close()


def _token(email: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _fake_page(*, url: str, title: str, text: str, published_at_raw: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        status_code=200,
        title=title,
        text=text,
        html=f"<html><body><h1>{title}</h1><p>{text}</p></body></html>",
        final_url=url,
        requested_url=url,
        retrieved_at=datetime.now(timezone.utc),
        published_at_raw=published_at_raw,
        content_type="text/html",
        content_hash=compute_content_hash(text),
        from_cache=False,
    )


class _StubMonshaatReader:
    """Deterministic official-domain pages when live TLS to monshaat.gov.sa is unavailable."""

    def __init__(self) -> None:
        self.pages = {
            MONSHAAT_FIXTURE_URLS[0]: _fake_page(
                url=MONSHAAT_FIXTURE_URLS[0],
                title="Monsha'at Reports — SME market intelligence",
                text=(
                    "Monsha'at publishes SME sector analysis and entrepreneurship indicators "
                    "to support market feasibility and the business environment in Saudi Arabia. "
                    "Small and medium enterprises are a strategic growth pillar."
                ),
                published_at_raw="2024-06-15",
            ),
            MONSHAAT_FIXTURE_URLS[1]: _fake_page(
                url=MONSHAAT_FIXTURE_URLS[1],
                title="Monsha'at business environment briefing",
                text=(
                    "Official Monsha'at guidance on entrepreneurship programs, SME financing "
                    "context, and business-environment indicators for startups and founders."
                ),
                published_at_raw=None,
            ),
            "https://www.monshaat.gov.sa/en": _fake_page(
                url="https://www.monshaat.gov.sa/en",
                title="Monsha'at",
                text="Small & Medium Enterprises General Authority home",
            ),
        }

    def read(self, url: str, use_cache: bool = True):
        validate_url(url, allowed_domains=MONSHAAT_ALLOWED_DOMAINS, resolve_dns=False)
        key = url.rstrip("/")
        for k, page in self.pages.items():
            if key == k.rstrip("/") or url == k:
                return page
        raise PageFetchError(f"stub miss for {url}")


# ---------------------------------------------------------------------------
# A. Monsha'at connector contract
# ---------------------------------------------------------------------------
def test_a_monshaat_connector_contract():
    connector = MonshaatConnector(enabled=True, reader=_StubMonshaatReader())
    health = connector.health()
    assert health.status.value == "healthy"
    meta = connector.source_metadata
    assert meta["live"] is True
    assert meta["api"] is None
    assert meta["registry_key"] == "monshaat"
    assert "monshaat.gov.sa" in meta["allowed_domains"]
    assert "sme" in meta["supported_sectors"]
    docs = connector.retrieve(url=MONSHAAT_FIXTURE_URLS[0])
    assert len(docs) == 1
    doc = docs[0]
    assert doc.url and "monshaat.gov.sa" in doc.url
    assert doc.content and "SME" in doc.content
    assert doc.content_hash
    assert doc.provenance.connector_id == connector.connector_id
    assert doc.provenance.registry_key == "monshaat"
    assert doc.provenance.original_url
    assert doc.retrieved_at is not None
    assert doc.sector is None


# ---------------------------------------------------------------------------
# B. MISA connector contract (live)
# ---------------------------------------------------------------------------
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
    assert doc.provenance.connector_id == connector.connector_id
    assert doc.provenance.registry_key == "misa"
    assert doc.retrieved_at is not None
    assert doc.sector is None


# ---------------------------------------------------------------------------
# C. Domain validation
# ---------------------------------------------------------------------------
def test_c_domain_validation():
    mon = MonshaatConnector(enabled=True, reader=_StubMonshaatReader())
    misa = MisaConnector(enabled=True)
    with pytest.raises((UrlSecurityError, PageFetchError)):
        mon.fetch_url("https://example.com/fake-monshaat")
    with pytest.raises((UrlSecurityError, PageFetchError)):
        mon.fetch_url("https://evil.monshaat.gov.sa.attacker.com/x")
    with pytest.raises((UrlSecurityError, PageFetchError)):
        misa.fetch_url("https://example.com/fake-misa")
    with pytest.raises((UrlSecurityError, PageFetchError)):
        misa.fetch_url("https://evil.misa.gov.sa.attacker.com/x")


# ---------------------------------------------------------------------------
# D. SSRF protection regression
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "bad_url,domains",
    [
        ("http://127.0.0.1/", MONSHAAT_ALLOWED_DOMAINS),
        ("http://localhost/", MONSHAAT_ALLOWED_DOMAINS),
        ("http://10.0.0.5/", MISA_ALLOWED_DOMAINS),
        ("http://192.168.1.10/", MISA_ALLOWED_DOMAINS),
        ("http://169.254.169.254/latest/meta-data/", MONSHAAT_ALLOWED_DOMAINS),
        ("file:///etc/passwd", MISA_ALLOWED_DOMAINS),
        ("ftp://misa.gov.sa/", MISA_ALLOWED_DOMAINS),
    ],
)
def test_d_ssrf_protection_regression(bad_url, domains):
    with pytest.raises(UrlSecurityError):
        validate_url(bad_url, allowed_domains=domains, resolve_dns=False)


# ---------------------------------------------------------------------------
# E. Provenance preservation
# ---------------------------------------------------------------------------
def test_e_provenance_preservation():
    mon = MonshaatConnector(enabled=True, reader=_StubMonshaatReader())
    doc = mon.fetch_url(MONSHAAT_FIXTURE_URLS[0])
    ok, errors = mon.validate_provenance(doc)
    assert ok, errors
    assert doc.provenance.connector_id == "live.monshaat"
    assert doc.provenance.registry_key == "monshaat"
    assert doc.provenance.original_url
    assert doc.provenance.retrieval_method == "http_html"
    assert doc.provenance.retrieved_at is not None

    misa_doc = MisaConnector().fetch_url(LIVE_MISA_URLS[0])
    ok2, errors2 = MisaConnector().validate_provenance(misa_doc)
    assert ok2, errors2
    assert misa_doc.provenance.registry_key == "misa"
    assert misa_doc.url and misa_doc.content_hash


# ---------------------------------------------------------------------------
# F / G. Knowledge ingestion + duplicate prevention
# ---------------------------------------------------------------------------
def test_f_g_knowledge_ingest_and_idempotency():
    _admin_email, admin_id = _make_admin()
    db = app_db.SessionLocal()
    try:
        registry.ensure_seed_sources(db)
        for key in ("monshaat", "misa"):
            row = registry.get_source_by_key(db, key)
            assert row is not None
            assert row.connector_type == "live"
            assert row.enabled is True

        mon_doc = MonshaatConnector(enabled=True, reader=_StubMonshaatReader()).fetch_url(
            MONSHAAT_FIXTURE_URLS[0]
        )
        kd1 = ingest_source_document(db, owner_id=admin_id, document=mon_doc)
        ext = (kd1.assumptions or {}).get("external_source") or {}
        assert ext.get("source_id") == mon_doc.source_id
        assert ext.get("content_hash") == mon_doc.content_hash
        assert (ext.get("provenance") or {}).get("registry_key") == "monshaat"
        chunks = (
            db.query(models.KnowledgeChunk)
            .filter(models.KnowledgeChunk.document_id == kd1.id)
            .all()
        )
        assert chunks
        assert chunks[0].chunk_metadata.get("registry_key") == "monshaat"
        assert chunks[0].chunk_metadata.get("original_url") == mon_doc.url

        kd2 = ingest_source_document(db, owner_id=admin_id, document=mon_doc)
        assert kd2.id == kd1.id
        assert getattr(kd2, "_idempotent_reuse", False) is True

        misa_doc = MisaConnector().fetch_url(LIVE_MISA_URLS[1])
        kd_m = ingest_source_document(db, owner_id=admin_id, document=misa_doc)
        ext_m = (kd_m.assumptions or {}).get("external_source") or {}
        assert (ext_m.get("provenance") or {}).get("registry_key") == "misa"
        assert ext_m.get("url") and "misa.gov.sa" in ext_m["url"]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# H. Source failure handling
# ---------------------------------------------------------------------------
def test_h_source_failure_handling():
    disabled = MonshaatConnector(enabled=False, reader=_StubMonshaatReader())
    assert disabled.health().status.value == "disabled"
    assert disabled.retrieve() == []

    failing = MonshaatConnector(enabled=True)

    def _boom(*_a, **_k):
        raise PageFetchError("TLS handshake timed out")

    with mock.patch.object(failing._reader, "read", side_effect=_boom):
        health = failing.health()
        assert health.status.value == "unavailable"
        assert "timed out" in (health.detail or "").lower()
        assert failing.retrieve(url=MONSHAAT_FIXTURE_URLS[0]) == []

    _admin_email, _admin_id = _make_admin()
    db = app_db.SessionLocal()
    try:
        registry.ensure_seed_sources(db)
        row = registry.get_source_by_key(db, "monshaat")
        registry.record_sync_result(db, row.id, success=False, error="simulated monshaat outage")
        db.refresh(row)
        assert row.last_failure_at is not None
        assert "outage" in (row.last_error or "")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# I. Tenant isolation
# ---------------------------------------------------------------------------
def test_i_tenant_isolation():
    _admin_email, admin_id = _make_admin()
    _other_email, other_id = _make_user()
    db = app_db.SessionLocal()
    try:
        doc = MonshaatConnector(enabled=True, reader=_StubMonshaatReader()).fetch_url(
            MONSHAAT_FIXTURE_URLS[1]
        )
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


# ---------------------------------------------------------------------------
# Business scenarios (evidence availability only — no financial calc changes)
# ---------------------------------------------------------------------------
def test_business_scenario_a_startup_feasibility_monshaat():
    _admin_email, admin_id = _make_admin()
    db = app_db.SessionLocal()
    try:
        connector = MonshaatConnector(enabled=True, reader=_StubMonshaatReader())
        for url in MONSHAAT_FIXTURE_URLS:
            ingest_source_document(db, owner_id=admin_id, document=connector.fetch_url(url))

        pack = ks.retrieve_evidence(
            db,
            owner_id=admin_id,
            query=(
                "What Monsha'at SME market and entrepreneurship context supports "
                "a startup feasibility study?"
            ),
            top_k=6,
        )
        citations = pack.get("citations") or pack.get("evidence") or []
        assert citations, pack
        blob = str(citations).lower()
        assert "sme" in blob or "entrepreneur" in blob or "monshaat" in blob or "business" in blob
        for c in citations:
            assert (
                c.get("document_id")
                or c.get("source_document_id")
                or c.get("url")
                or c.get("source")
            ), c
    finally:
        db.close()


def test_business_scenario_b_foreign_investment_misa_live():
    _admin_email, admin_id = _make_admin()
    db = app_db.SessionLocal()
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
        assert cited_ids.intersection(set(ingested_ids)) or any(
            "investment" in (c.get("content") or c.get("claim") or "").lower()
            for c in citations
        ), pack
        for c in citations:
            assert (
                c.get("document_id")
                or c.get("source_document_id")
                or c.get("url")
                or c.get("source")
            ), c
    finally:
        db.close()


# ---------------------------------------------------------------------------
# API sync / documents + MCP
# ---------------------------------------------------------------------------
def test_api_sync_documents_and_mcp():
    admin_email, _admin_id = _make_admin()
    db = app_db.SessionLocal()
    try:
        registry.ensure_seed_sources(db)
        misa_row = registry.get_source_by_key(db, "misa")
        mon_row = registry.get_source_by_key(db, "monshaat")
        assert misa_row and mon_row
        assert registry.connector_for_source(misa_row) is not None
        assert registry.connector_for_source(mon_row) is not None
        misa_id = misa_row.id
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
    assert body["documents"][0]["content_hash"]

    docs_resp = client.get(
        f"/api/v2/sources/{misa_id}/documents",
        headers=_auth(tok),
    )
    assert docs_resp.status_code == 200, docs_resp.text
    assert docs_resp.json()["count"] >= 1

    user_email, _ = _make_user()
    utok = _token(user_email)
    denied = client.post(
        f"/api/v2/sources/{misa_id}/sync",
        headers=_auth(utok),
        json={"urls": [LIVE_MISA_URLS[0]]},
    )
    assert denied.status_code in (401, 403)

    tools = list_bound_tool_names(build_mcp_server())
    assert "source_status" in tools
    assert "source_fetch" in tools
    misa_status = source_status_payload("misa")
    assert misa_status["ok"] is True
    assert "financial" in misa_status["forbidden"]
    mon_status = source_status_payload("monshaat")
    assert mon_status["connector_id"] == "live.monshaat"
    assert mon_status["mcp_boundary"] is True
    fetched = source_fetch_payload("misa", {"url": LIVE_MISA_URLS[1]})
    assert fetched["count"] == 1
    assert fetched["documents"][0]["provenance"]["registry_key"] == "misa"
    with mock.patch(
        "app.integrations.mcp.boundary.MonshaatConnector",
        lambda enabled=True: MonshaatConnector(enabled=True, reader=_StubMonshaatReader()),
    ):
        mon_fetched = source_fetch_payload("monshaat", {"url": MONSHAAT_FIXTURE_URLS[0]})
        assert mon_fetched["count"] == 1


# ---------------------------------------------------------------------------
# J. V3 regression smoke
# ---------------------------------------------------------------------------
def test_j_v3_regression_smoke():
    from app.services import financial_health  # noqa: F401
    from app.services import financial_projection  # noqa: F401
    from app.services import decision_engine  # noqa: F401
    from app.api.v2 import sources as v2_sources  # noqa: F401

    assert hasattr(v2_sources, "sync_source")
    assert hasattr(v2_sources, "list_source_documents")


# ---------------------------------------------------------------------------
# K. Phase 7B GASTAT regression
# ---------------------------------------------------------------------------
def test_k_phase7b_gastat_regression():
    connector = GastatConnector(enabled=True)
    health = connector.health()
    assert health.status.value == "healthy", health.detail
    docs = connector.retrieve(url="https://www.stats.gov.sa/en/w/news/180")
    assert len(docs) == 1
    assert docs[0].provenance.registry_key == "gastat"
    status = source_status_payload("gastat")
    assert status["ok"] is True


def test_live_monshaat_reachability_documented():
    """Live official Monsha'at TLS may be unreachable from this agent network.

    Connector must surface UNAVAILABLE (or healthy if reachable) — never invent content.
    """
    live = MonshaatConnector(enabled=True)
    health = live.health()
    assert health.status.value in {"healthy", "degraded", "unavailable"}
    if health.status.value == "unavailable":
        assert health.detail
        assert live.retrieve() == []
    else:
        docs = live.retrieve()
        assert len(docs) >= 1
        assert all("monshaat.gov.sa" in (d.url or "") for d in docs)
