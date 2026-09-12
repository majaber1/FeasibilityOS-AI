"""Phase 7A — Source Registry + Connector Contract foundation tests.

A. Source Registry CRUD / read
B. Tenant/admin authorization
C. SourceDocument schema validation
D. Provenance preservation
E. UNKNOWN stays unknown
F. Fake/missing source cannot become verified evidence
G. Connector contract
H. Knowledge adapter
I. MCP boundary smoke
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app import db as app_db  # noqa: E402
from app import models  # noqa: E402
from app import auth as security  # noqa: E402
from app.main import app  # noqa: E402
from app.integrations.sources import (  # noqa: E402
    AuthorityType,
    FixtureSaudiOpenDataConnector,
    Provenance,
    SourceDocument,
    SourceType,
    VerificationEligibility,
    ingest_source_document,
    provenance_is_complete,
    validate_source_document,
)
from app.integrations.sources.validation import (  # noqa: E402
    compute_content_hash,
    verification_status_for,
)
from app.integrations.sources.knowledge_adapter import (  # noqa: E402
    ProvenanceError,
    source_document_to_ingest_payload,
)
from app.integrations.mcp import (  # noqa: E402
    MCP_AVAILABLE,
    build_mcp_server,
    connector_health_payload,
    list_bound_tool_names,
)
from app.services import source_registry_service as registry  # noqa: E402

client = TestClient(app)
PASSWORD = "Sup3rSecret!"

EXPECTED_SEED_KEYS = {
    "gastat",
    "monshaat",
    "misa",
    "sama",
    "nca",
    "zatca",
    "saudi_open_data",
}


def setup_module(module):
    assert app_db.DB_ENABLED is True
    app_db.init_db()


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"


def _make_admin_via_orm(password: str = PASSWORD) -> str:
    from app.api.auth import _ensure_roles

    email = _email("admin")
    session = app_db.SessionLocal()
    try:
        _ensure_roles(session)
        session.add(
            models.User(
                email=email,
                hashed_password=security.hash_password(password),
                full_name="Root Admin",
                role_key="admin",
                locale="en",
                is_active=True,
            )
        )
        session.commit()
    finally:
        session.close()
    return email


def _register_user(prefix: str = "user") -> str:
    email = _email(prefix)
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Tester"},
    )
    assert resp.status_code == 201, resp.text
    return email


def _token_for(email: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_doc(**overrides) -> SourceDocument:
    retrieved = _now()
    content = "Official SME indicator extract for testing."
    data = {
        "source_id": "doc-1",
        "source_name": "Test Source",
        "source_type": SourceType.OPEN_DATA,
        "authority_type": AuthorityType.OFFICIAL_PRIMARY,
        "url": "https://data.gov.sa/example",
        "canonical_url": "https://data.gov.sa/example",
        "title": "Example",
        "content": content,
        "published_at": None,
        "retrieved_at": retrieved,
        "country": "SA",
        "content_hash": compute_content_hash(content),
        "provenance": Provenance(
            connector_id="fixture.saudi_open_data",
            original_url="https://data.gov.sa/example",
            retrieval_method="fixture",
            retrieved_at=retrieved,
            registry_key="saudi_open_data",
        ),
        "verification_eligibility": VerificationEligibility.ELIGIBLE,
    }
    data.update(overrides)
    return SourceDocument(**data)


def test_a_registry_seed_list_and_persistence():
    admin = _make_admin_via_orm()
    tok = _token_for(admin)
    resp = client.get("/api/v2/sources", headers=_auth(tok))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] >= 7
    keys = {item["key"] for item in body["items"]}
    assert EXPECTED_SEED_KEYS.issubset(keys)

    db = app_db.SessionLocal()
    try:
        row = registry.get_source_by_key(db, "saudi_open_data")
        assert row is not None
        assert row.connector_type == "fixture"
        updated = registry.update_source(db, row.id, {"enabled": True, "quality_score": 0.8})
        assert updated.enabled is True
        assert updated.quality_score == 0.8
        dirty = registry.update_source(
            db,
            row.id,
            {"connector_config": {"dataset": "sme", "api_key": "SUPERSECRET", "token": "x"}},
        )
        assert "api_key" not in (dirty.connector_config or {})
        assert "token" not in (dirty.connector_config or {})
        assert dirty.connector_config.get("dataset") == "sme"
        synced = registry.record_sync_result(db, row.id, success=True)
        assert synced.last_success_at is not None
        assert synced.last_error is None
        again = registry.get_source(db, row.id)
        assert again.last_success_at is not None
        assert again.connector_config.get("dataset") == "sme"
    finally:
        db.close()


def test_b_admin_mutations_forbidden_for_regular_user():
    user = _register_user("member")
    tok = _token_for(user)
    r = client.get("/api/v2/sources", headers=_auth(tok))
    assert r.status_code == 200, r.text

    create = client.post(
        "/api/v2/sources",
        headers=_auth(tok),
        json={"key": f"x_{uuid.uuid4().hex[:8]}", "name": "Nope"},
    )
    assert create.status_code == 403, create.text
    assert client.get("/api/v2/sources").status_code == 401


def test_b_admin_can_create_patch_and_status():
    admin = _make_admin_via_orm()
    tok = _token_for(admin)
    key = f"custom_{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/v2/sources",
        headers=_auth(tok),
        json={
            "key": key,
            "name": "Custom Registry Source",
            "source_type": "other",
            "authority_type": "UNVERIFIED",
            "connector_config": {"path": "/data", "password": "nope"},
        },
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["key"] == key
    assert "password" not in payload["connector_config"]

    patched = client.patch(
        f"/api/v2/sources/{payload['id']}",
        headers=_auth(tok),
        json={"enabled": True, "description": "patched"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["enabled"] is True
    assert patched.json()["description"] == "patched"

    status = client.get(f"/api/v2/sources/{payload['id']}/status", headers=_auth(tok))
    assert status.status_code == 200, status.text
    assert status.json()["key"] == key


def test_c_e_schema_validation_and_unknown_preserved():
    doc = _valid_doc(
        source_type=SourceType.UNKNOWN,
        authority_type=AuthorityType.UNKNOWN,
        published_at=None,
        url=None,
        canonical_url=None,
        verification_eligibility=VerificationEligibility.UNKNOWN,
    )
    assert doc.published_at is None
    assert doc.url is None
    assert doc.authority_type == AuthorityType.UNKNOWN
    ok, errors = validate_source_document(doc)
    assert ok, errors

    bad = _valid_doc(
        source_type=SourceType.UNKNOWN,
        authority_type=AuthorityType.OFFICIAL_PRIMARY,
    )
    ok2, errors2 = validate_source_document(bad)
    assert not ok2
    assert any("OFFICIAL_PRIMARY" in e for e in errors2)

    with pytest.raises(ValidationError):
        SourceDocument(
            source_id="",
            source_name="x",
            content="y",
            retrieved_at=_now(),
            provenance=Provenance(
                connector_id="c",
                retrieval_method="m",
                retrieved_at=_now(),
            ),
        )


def test_d_f_provenance_and_no_verified_without_provenance():
    assert provenance_is_complete(None) is False

    broken = _valid_doc(
        authority_type=AuthorityType.AI_INFERENCE,
        verification_eligibility=VerificationEligibility.ELIGIBLE,
    )
    ok, _errors = validate_source_document(broken)
    assert not ok
    assert verification_status_for(broken) != "verified"

    fake = _valid_doc(
        url=None,
        canonical_url=None,
        authority_type=AuthorityType.AI_INFERENCE,
        verification_eligibility=VerificationEligibility.NOT_ELIGIBLE,
        published_at=None,
    )
    status = verification_status_for(fake)
    assert status in {"unverified", "user_provided"}
    assert status != "verified"
    assert verification_status_for(_valid_doc()) != "verified"


def test_g_fixture_connector_contract():
    conn = FixtureSaudiOpenDataConnector(enabled=True)
    assert conn.connector_id == "fixture.saudi_open_data"
    assert conn.health().status.value == "healthy"
    docs = conn.retrieve(query="SME")
    assert len(docs) == 1
    doc = docs[0]
    assert doc.published_at is None
    assert doc.provenance.connector_id == conn.connector_id
    assert doc.provenance.retrieval_method == "fixture"
    ok, errors = conn.validate_provenance(doc)
    assert ok, errors

    disabled = FixtureSaudiOpenDataConnector(enabled=False)
    assert disabled.health().status.value == "disabled"
    assert disabled.retrieve() == []


def test_h_knowledge_adapter_preserves_provenance():
    user_email = _register_user("know")
    db = app_db.SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=user_email).first()
        assert user is not None
        doc = FixtureSaudiOpenDataConnector().retrieve(query="adapter")[0]
        saved = ingest_source_document(db, owner_id=user.id, document=doc)
        assert saved.id
        assert saved.source.startswith("connector:")
        ext = (saved.assumptions or {}).get("external_source") or {}
        assert ext.get("provenance", {}).get("connector_id") == "fixture.saudi_open_data"
        assert ext.get("published_at") is None
        assert saved.chunks
        chunk_meta = saved.chunks[0].chunk_metadata or {}
        assert chunk_meta.get("connector_id") == "fixture.saudi_open_data"
        assert chunk_meta.get("original_url")
        assert chunk_meta.get("verification_status") != "verified"

        with pytest.raises(ProvenanceError):
            source_document_to_ingest_payload(doc.model_copy(update={"content": "   "}))
    finally:
        db.close()


def test_h_refuses_bad_hash_and_preserves_unknown_year():
    doc = _valid_doc(content_hash="deadbeef" * 8)
    with pytest.raises(ProvenanceError):
        source_document_to_ingest_payload(doc)

    good = _valid_doc()
    payload = source_document_to_ingest_payload(good)
    assert payload["assumptions"]["external_source"]["provenance"]["connector_id"]
    assert payload["year"] is None


def test_i_mcp_boundary_smoke():
    assert MCP_AVAILABLE is True
    payload = connector_health_payload()
    assert payload["ok"] is True
    assert payload.get("mcp_boundary") is True
    assert payload["connector_id"] == "fixture.saudi_open_data"

    server = build_mcp_server()
    names = list_bound_tool_names(server)
    assert "source_connector_health" in names
    assert "source_connector_metadata" in names
