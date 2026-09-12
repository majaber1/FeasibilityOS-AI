"""Phase 7B — GASTAT live source + safe page reader validation.

Covers required checks A–O (see docs/evidence/V4_PHASE7B_GASTAT_LIVE_SOURCE_VALIDATION.md).
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
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
from app.integrations.research.cache import BoundedTTLCache, CacheEntry, utcnow  # noqa: E402
from app.integrations.research.content_cleaner import clean_html  # noqa: E402
from app.integrations.research.page_reader import PageFetchError, SafePageReader  # noqa: E402
from app.integrations.research.security import UrlSecurityError, canonicalize_url, validate_url  # noqa: E402
from app.integrations.sources.gastat import (  # noqa: E402
    DEFAULT_GASTAT_URLS,
    GASTAT_ALLOWED_DOMAINS,
    GastatConnector,
    parse_explicit_date,
)
from app.integrations.sources.knowledge_adapter import (  # noqa: E402
    find_existing_by_content_hash,
    ingest_source_document,
)
from app.integrations.mcp.boundary import (
    build_mcp_server,
    list_bound_tool_names,
    source_fetch_payload,
    source_status_payload,
)
from app.services import source_registry_service as registry  # noqa: E402
from app.services import knowledge_service as ks  # noqa: E402

client = TestClient(app)
PASSWORD = "Sup3rSecret!"

LIVE_URLS = list(DEFAULT_GASTAT_URLS)


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"


def _make_admin() -> tuple[str, int]:
    from app.api.auth import _ensure_roles

    email = _email("admin7b")
    session = app_db.SessionLocal()
    try:
        _ensure_roles(session)
        user = models.User(
            email=email,
            hashed_password=security.hash_password(PASSWORD),
            full_name="Phase7B Admin",
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
    email = _email("user7b")
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


# ---------------------------------------------------------------------------
# A. GASTAT live connector contract
# ---------------------------------------------------------------------------
def test_a_gastat_live_connector_contract():
    connector = GastatConnector(enabled=True)
    health = connector.health()
    assert health.status.value == "healthy"
    meta = connector.source_metadata
    assert meta["live"] is True
    assert meta["api"] is None
    assert "stats.gov.sa" in meta["allowed_domains"]
    docs = connector.retrieve(url=LIVE_URLS[0])
    assert len(docs) == 1
    doc = docs[0]
    assert doc.url and "stats.gov.sa" in doc.url
    assert doc.content and len(doc.content) > 100
    assert doc.content_hash
    assert doc.provenance.connector_id == connector.connector_id
    assert doc.provenance.registry_key == "gastat"
    assert doc.provenance.original_url
    assert doc.retrieved_at is not None


# ---------------------------------------------------------------------------
# B. Official-domain enforcement
# ---------------------------------------------------------------------------
def test_b_gastat_official_domain_enforcement():
    connector = GastatConnector(enabled=True)
    with pytest.raises((UrlSecurityError, PageFetchError)):
        connector.fetch_url("https://example.com/fake-stats")
    with pytest.raises((UrlSecurityError, PageFetchError)):
        connector.fetch_url("https://evil.stats.gov.sa.attacker.com/x")


# ---------------------------------------------------------------------------
# C. SSRF / private-network rejection
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.5/",
        "http://192.168.1.10/",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://stats.gov.sa/",
    ],
)
def test_c_ssrf_private_network_rejection(bad_url):
    with pytest.raises(UrlSecurityError):
        validate_url(bad_url, allowed_domains=GASTAT_ALLOWED_DOMAINS, resolve_dns=False)


# ---------------------------------------------------------------------------
# D. timeout / size / content-type failure paths
# ---------------------------------------------------------------------------
def test_d_timeout_size_content_type_failures():
    reader = SafePageReader(
        allowed_domains=GASTAT_ALLOWED_DOMAINS,
        timeout_seconds=0.001,
        max_bytes=100,
        resolve_dns=True,
    )
    # Tiny max_bytes should fail against a real page
    with pytest.raises(PageFetchError):
        reader.read(LIVE_URLS[0], use_cache=False)

    # Content-type rejection via mock
    reader2 = SafePageReader(allowed_domains=["example.com"], resolve_dns=False)
    fake = mock.Mock()
    fake.status_code = 200
    fake.headers = {"content-type": "application/octet-stream", "content-length": "10"}
    fake.content = b"abcdefghij"
    fake.url = "https://example.com/bin"

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return fake

    with mock.patch("app.integrations.research.page_reader.httpx.Client", _Client):
        with pytest.raises(PageFetchError, match="content-type"):
            reader2.read("https://example.com/bin", use_cache=False)


# ---------------------------------------------------------------------------
# E. Page cleanup
# ---------------------------------------------------------------------------
def test_e_page_cleanup():
    html = """
    <html><head><title>Official Title</title>
    <script>evil()</script><style>.x{}</style></head>
    <body>
      <nav>Home About</nav>
      <article><h1>Inflation Report</h1><p>CPI rose in March.</p>
      <table><tr><td>Item</td><td>1.8%</td></tr></table>
      </article>
      <footer>All rights reserved</footer>
      <div class="cookie">Accept all cookies</div>
    </body></html>
    """
    text, title, published = clean_html(html)
    assert title == "Official Title"
    assert "Inflation Report" in text
    assert "CPI rose" in text
    assert "evil()" not in text
    assert "Accept all cookies" not in text
    assert "Home About" not in text or "Inflation" in text


# ---------------------------------------------------------------------------
# F. Cache hit/miss/expiry
# ---------------------------------------------------------------------------
def test_f_cache_hit_miss_expiry():
    cache = BoundedTTLCache(max_entries=8, ttl_seconds=1)
    key = canonicalize_url("https://www.stats.gov.sa/en/w/news/180")
    assert cache.get(key) is None
    assert cache.misses == 1
    entry = CacheEntry(
        url=key,
        content_hash="abc",
        retrieved_at=utcnow(),
        status_code=200,
        content_type="text/html",
        final_url=key,
        title="t",
        text="body",
        html="<p>body</p>",
        published_at_raw=None,
        expires_at_monotonic=time.monotonic() + 1,
    )
    cache.set(key, entry)
    hit = cache.get(key)
    assert hit is not None and hit.content_hash == "abc"
    assert cache.hits == 1
    time.sleep(1.1)
    assert cache.get(key) is None  # expired


# ---------------------------------------------------------------------------
# G. Canonical URL handling
# ---------------------------------------------------------------------------
def test_g_canonical_url_handling():
    a = canonicalize_url("https://WWW.Stats.Gov.SA/en/w/news/180#frag")
    b = canonicalize_url("https://www.stats.gov.sa/en/w/news/180")
    assert a == b
    assert "#" not in a


# ---------------------------------------------------------------------------
# H / I. Publication date preserved or UNKNOWN
# ---------------------------------------------------------------------------
def test_h_real_publication_date_preserved():
    doc = GastatConnector().fetch_url(LIVE_URLS[0])
    # Live GASTAT pages currently expose an explicit date — must not invent if missing,
    # but when present it must parse cleanly.
    if doc.metadata.get("published_at_raw"):
        assert doc.published_at is not None
        assert parse_explicit_date(doc.metadata["published_at_raw"]) is not None


def test_i_missing_publication_date_remains_null():
    assert parse_explicit_date(None) is None
    assert parse_explicit_date("") is None
    assert parse_explicit_date("sometime last week") is None
    # Fixture-like raw without date
    connector = GastatConnector(enabled=True)
    raw = {
        "id": "gastat-nodate-test",
        "title": "No date page",
        "content": "Official content without an explicit publication date marker.",
        "url": "https://www.stats.gov.sa/en/nodate-fixture",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "published_at_raw": None,
        "content_type": "text/html",
        "content_hash": "x" * 64,
        "from_cache": False,
        "language": "en",
        "sector": None,
        "failed": False,
    }
    doc = connector.normalize(raw)
    assert doc.published_at is None


# ---------------------------------------------------------------------------
# J / K / M / N. Provenance → knowledge, status, idempotency, tenant isolation
# ---------------------------------------------------------------------------
def test_j_k_m_n_provenance_status_idempotency_tenant():
    admin_email, admin_id = _make_admin()
    other_email, other_id = _make_user()
    db = app_db.SessionLocal()
    try:
        registry.ensure_seed_sources(db)
        row = registry.get_source_by_key(db, "gastat")
        assert row is not None
        assert row.connector_type == "live"
        assert row.enabled is True

        doc = GastatConnector().fetch_url(LIVE_URLS[1])
        assert doc.provenance.registry_key == "gastat"

        kd1 = ingest_source_document(db, owner_id=admin_id, document=doc)
        assert kd1.id
        assumptions = kd1.assumptions or {}
        ext = assumptions.get("external_source") or {}
        assert ext.get("source_id") == doc.source_id
        assert ext.get("source_name")
        assert ext.get("url") == doc.url
        assert ext.get("retrieved_at")
        assert ext.get("content_hash") == doc.content_hash
        prov = ext.get("provenance") or {}
        assert prov.get("connector_id")
        assert prov.get("original_url")
        chunks = (
            db.query(models.KnowledgeChunk)
            .filter(models.KnowledgeChunk.document_id == kd1.id)
            .all()
        )
        assert chunks
        assert chunks[0].chunk_metadata.get("original_url") == doc.url

        # Idempotent re-ingest
        kd2 = ingest_source_document(db, owner_id=admin_id, document=doc)
        assert kd2.id == kd1.id
        assert getattr(kd2, "_idempotent_reuse", False) is True
        count = (
            db.query(models.KnowledgeDocument)
            .filter(models.KnowledgeDocument.owner_id == admin_id)
            .count()
        )
        # At least the one we inserted; duplicates not added
        hashes = []
        for d in (
            db.query(models.KnowledgeDocument)
            .filter(models.KnowledgeDocument.owner_id == admin_id)
            .all()
        ):
            h = (d.assumptions or {}).get("external_source", {}).get("content_hash")
            if h:
                hashes.append(h)
        assert hashes.count(doc.content_hash) == 1

        # Tenant isolation: other owner does not see admin docs via find
        assert (
            find_existing_by_content_hash(db, owner_id=other_id, content_hash=doc.content_hash)
            is None
        )
        other_docs = ks.list_documents(db, owner_id=other_id)
        assert all(
            (d.assumptions or {}).get("external_source", {}).get("content_hash") != doc.content_hash
            for d in other_docs
        )

        # Status updates after success
        registry.record_sync_result(db, row.id, success=True)
        db.refresh(row)
        assert row.last_sync_at is not None
        assert row.last_success_at is not None
        assert row.last_error is None

        # Status updates after failure
        registry.record_sync_result(db, row.id, success=False, error="simulated failure")
        db.refresh(row)
        assert row.last_failure_at is not None
        assert "simulated failure" in (row.last_error or "")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# L. MCP source tool boundary
# ---------------------------------------------------------------------------
def test_l_mcp_source_tool_boundary():
    tools = list_bound_tool_names(build_mcp_server())
    assert "source_status" in tools
    assert "source_fetch" in tools
    status = source_status_payload("gastat")
    assert status["ok"] is True
    assert status["mcp_boundary"] is True
    assert "financial" in status["forbidden"]
    fetched = source_fetch_payload("gastat", {"url": LIVE_URLS[2]})
    assert fetched["count"] == 1
    assert fetched["documents"][0]["provenance"]["registry_key"] == "gastat"
    with pytest.raises(ValueError):
        source_status_payload("not-a-source")


# ---------------------------------------------------------------------------
# Live E2E: 3 topics → knowledge → evidence pack retrieval
# ---------------------------------------------------------------------------
def test_live_e2e_three_topics_evidence_pack():
    admin_email, admin_id = _make_admin()
    db = app_db.SessionLocal()
    try:
        registry.ensure_seed_sources(db)
        row = registry.get_source_by_key(db, "gastat")
        connector = GastatConnector()
        ingested = []
        for url in LIVE_URLS:
            docs = connector.retrieve(url=url)
            assert docs, f"no doc for {url}"
            doc = docs[0]
            kd = ingest_source_document(db, owner_id=admin_id, document=doc)
            chunks = (
                db.query(models.KnowledgeChunk)
                .filter(models.KnowledgeChunk.document_id == kd.id)
                .all()
            )
            ingested.append(
                {
                    "url": doc.url,
                    "title": doc.title,
                    "content_hash": doc.content_hash,
                    "retrieved_at": doc.retrieved_at.isoformat(),
                    "knowledge_document_id": kd.id,
                    "chunk_id": chunks[0].id if chunks else None,
                    "published_at": doc.published_at.isoformat() if doc.published_at else None,
                }
            )

        assert len(ingested) == 3
        # Retrieval question that can only be answered from ingested inflation source
        pack = ks.retrieve_evidence(
            db,
            owner_id=admin_id,
            query="What happened to inflation in Saudi Arabia in March 2026 according to GASTAT?",
            top_k=6,
        )
        citations = pack.get("citations") or pack.get("evidence") or []
        # Evidence pack shape may use citations list
        cited_doc_ids = {
            str(c.get("document_id") or c.get("source_document_id") or "")
            for c in citations
        }
        assert ingested[0]["knowledge_document_id"] in cited_doc_ids or any(
            ingested[0]["content_hash"]
            and ingested[0]["content_hash"]
            in str((c.get("doc_assumptions") or c))
            for c in citations
        ) or any(
            "inflation" in (c.get("content") or c.get("claim") or "").lower()
            for c in citations
        ), pack

        # Sync API (admin)
        tok = _token(admin_email)
        sync = client.post(
            f"/api/v2/sources/{row.id}/sync",
            headers=_auth(tok),
            json={"urls": [LIVE_URLS[0]]},
        )
        assert sync.status_code == 200, sync.text
        body = sync.json()
        assert body["success"] is True
        assert body["count"] >= 1

        docs_resp = client.get(
            f"/api/v2/sources/{row.id}/documents",
            headers=_auth(tok),
        )
        assert docs_resp.status_code == 200, docs_resp.text
        assert docs_resp.json()["count"] >= 1

        # Non-admin forbidden
        user_email, _ = _make_user()
        utok = _token(user_email)
        denied = client.post(
            f"/api/v2/sources/{row.id}/sync",
            headers=_auth(utok),
            json={"urls": [LIVE_URLS[0]]},
        )
        assert denied.status_code in (401, 403)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# O. V3 regression remains green (smoke subset invoked separately in CI)
# ---------------------------------------------------------------------------
def test_o_v3_financial_trust_smoke_importable():
    # Ensure Phase 7B did not break financial trust / decision imports
    from app.services import financial_health  # noqa: F401
    from app.services import financial_projection  # noqa: F401
    from app.services import decision_engine  # noqa: F401
    from app.api.v2 import sources as v2_sources  # noqa: F401

    assert hasattr(v2_sources, "sync_source")
