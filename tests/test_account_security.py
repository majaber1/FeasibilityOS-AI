"""Email verification and password-reset lifecycle tests."""
import os
import sys
import tempfile
import uuid
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + tmp.name
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def setup_module(module):
    app_db.init_db()


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def test_verification_is_single_use_and_unlocks_production_login(monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    monkeypatch.setenv("EXPOSE_ACCOUNT_TOKENS", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    email = _email("verify")
    password = "StrongPass1"
    created = client.post("/auth/register", json={"email": email, "password": password})
    assert created.status_code == 201
    assert created.json()["email_verified"] is False
    assert client.post("/auth/login", json={"email": email, "password": password}).status_code == 403

    issued = client.post("/auth/verification/request", json={"email": email})
    assert issued.status_code == 202
    token = issued.json()["dev_token"]
    assert token and len(token) >= 20
    assert client.post("/auth/verification/confirm", json={"token": token}).status_code == 200
    assert client.post("/auth/verification/confirm", json={"token": token}).status_code == 400
    assert client.post("/auth/login", json={"email": email, "password": password}).status_code == 200


def test_password_reset_is_non_enumerating_expiring_and_single_use(monkeypatch):
    monkeypatch.setenv("EXPOSE_ACCOUNT_TOKENS", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    email = _email("reset")
    old_password = "StrongPass1"
    new_password = "BetterPass2"
    assert client.post("/auth/register", json={"email": email, "password": old_password}).status_code == 201

    unknown = client.post("/auth/password/forgot", json={"email": _email("unknown")})
    assert unknown.status_code == 202
    assert unknown.json()["dev_token"] is None
    issued = client.post("/auth/password/forgot", json={"email": email})
    assert issued.status_code == 202
    token = issued.json()["dev_token"]
    assert token

    # Validation happens before consumption, allowing correction of a weak password.
    assert client.post("/auth/password/reset", json={"token": token, "password": "weak"}).status_code == 422
    assert client.post("/auth/password/reset", json={"token": token, "password": new_password}).status_code == 200
    assert client.post("/auth/password/reset", json={"token": token, "password": "AnotherPass3"}).status_code == 400
    assert client.post("/auth/login", json={"email": email, "password": old_password}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": new_password}).status_code == 200


def test_production_never_exposes_raw_account_token(monkeypatch):
    monkeypatch.setenv("EXPOSE_ACCOUNT_TOKENS", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")
    email = _email("hidden")
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    assert client.post("/auth/register", json={"email": email, "password": "StrongPass1"}).status_code == 201
    response = client.post("/auth/password/forgot", json={"email": email})
    assert response.status_code == 202
    assert response.json()["dev_token"] is None


def test_production_registration_fails_before_creating_an_unverifiable_account(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)

    response = client.post(
        "/auth/register",
        json={"email": _email("no_delivery"), "password": "StrongPass1"},
    )

    assert response.status_code == 503
    assert "email delivery" in response.json()["detail"].lower()


def test_production_registration_works_when_verification_is_not_enabled(monkeypatch):
    """A production demo must not silently enable an unavailable SMTP gate."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    email = _email("production_demo")
    password = "StrongPass1"

    created = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )

    assert created.status_code == 201, created.text
    signed_in = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert signed_in.status_code == 200, signed_in.text


def test_signed_in_user_can_update_safe_profile_fields_only(monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    email = _email("profile")
    password = "StrongPass1"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    updated = client.patch("/auth/me", headers=headers, json={"full_name": "  Nora Founder  ", "locale": "en"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Nora Founder"
    assert updated.json()["locale"] == "en"

    # Account privilege and identity fields are never mass-assignable.
    forbidden = client.patch("/auth/me", headers=headers, json={"role_key": "admin", "email": "admin@example.com"})
    assert forbidden.status_code == 422
    unchanged = client.get("/auth/me", headers=headers).json()
    assert unchanged["role_key"] == "entrepreneur"
    assert unchanged["email"] == email


def test_authenticated_password_change_reauthenticates_and_invalidates_reset_links(monkeypatch):
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    monkeypatch.setenv("EXPOSE_ACCOUNT_TOKENS", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    email = _email("change")
    old_password = "StrongPass1"
    new_password = "BetterPass2"
    assert client.post("/auth/register", json={"email": email, "password": old_password}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": old_password}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    reset_token = client.post("/auth/password/forgot", json={"email": email}).json()["dev_token"]
    assert reset_token

    wrong = client.post(
        "/auth/password/change", headers=headers,
        json={"current_password": "WrongPass9", "new_password": new_password},
    )
    assert wrong.status_code == 400
    changed = client.post(
        "/auth/password/change", headers=headers,
        json={"current_password": old_password, "new_password": new_password},
    )
    assert changed.status_code == 200, changed.text
    assert client.post("/auth/login", json={"email": email, "password": old_password}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": new_password}).status_code == 200
    assert client.post("/auth/password/reset", json={"token": reset_token, "password": "ThirdPass3"}).status_code == 400
