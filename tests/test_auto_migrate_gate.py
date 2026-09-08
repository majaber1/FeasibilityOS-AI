"""
Tests for app.db.ensure_migrations_applied's safety gates (C: off by default,
dialect-restricted, and never-raises). Runs in subprocess isolation like
tests/test_db_config.py, since app.db resolves its engine at import time.

Deliberately does NOT test against a real Postgres (no such service is
available here) -- these tests prove the *gates* are correct: the function
must be a true no-op unless explicitly opted into, and must never propagate
an exception even when the configured database is unreachable.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"

_PROBE_SCRIPT = r"""
import json, os, sys
sys.path.insert(0, {backend_dir!r})
from app import db

called = {{"attempted_connect": False}}

class _SentinelEngine:
    def connect(self):
        called["attempted_connect"] = True
        raise RuntimeError("connect() should not have been called")

# Force a truthy engine/URL regardless of what's actually configured, so we
# can isolate "did the AUTO_MIGRATE_DB / dialect gate short-circuit before
# ever touching a connection" from "is a real Postgres reachable."
db.engine = _SentinelEngine()
db.DB_ENABLED = True
db._ENGINE_URL = os.environ.get("PROBE_ENGINE_URL", "postgresql://u:p@unreachable-host/db")
db.DATABASE_URL = db._ENGINE_URL

raised = False
try:
    db.ensure_migrations_applied()
except Exception:
    raised = True

print("PROBE_RESULT=" + json.dumps({{"attempted_connect": called["attempted_connect"], "raised": raised}}))
"""


def _run_probe(env_overrides: dict) -> dict:
    # Preserve the host environment so Windows can initialize Winsock and the
    # asyncio overlapped-I/O provider. The probe still controls every setting
    # relevant to the migration gate through explicit overrides below.
    env = os.environ.copy()
    env.update(env_overrides)
    script = _PROBE_SCRIPT.format(backend_dir=str(BACKEND_DIR))
    proc = subprocess.run(
        [sys.executable, "-c", script], env=env, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0, "probe failed exit=" + str(proc.returncode) + " stderr_tail=" + proc.stderr[-1000:]
    for line in proc.stdout.splitlines():
        if line.startswith("PROBE_RESULT="):
            return json.loads(line[len("PROBE_RESULT="):])
    raise AssertionError("probe produced no PROBE_RESULT line; stdout=" + proc.stdout)


def test_default_off_never_attempts_a_connection():
    # AUTO_MIGRATE_DB unset -> must short-circuit before touching the engine.
    result = _run_probe({})
    assert result["attempted_connect"] is False
    assert result["raised"] is False


def test_explicitly_disabled_never_attempts_a_connection():
    for value in ("false", "0", "no", ""):
        result = _run_probe({"AUTO_MIGRATE_DB": value})
        assert result["attempted_connect"] is False, f"value={value!r}"


def test_opted_in_but_sqlite_dialect_never_attempts_a_connection():
    # Even with AUTO_MIGRATE_DB=true, a non-Postgres engine URL must be a no-op.
    result = _run_probe({"AUTO_MIGRATE_DB": "true", "PROBE_ENGINE_URL": "sqlite:///./demo.db"})
    assert result["attempted_connect"] is False
    assert result["raised"] is False


def test_opted_in_postgres_attempts_a_connection_but_never_raises():
    # Opted in + Postgres dialect -> it DOES try to connect (proving the gate
    # opens), but any failure downstream (unreachable host, bad creds, missing
    # alembic config in this probe's cwd) must be swallowed, never raised.
    result = _run_probe({"AUTO_MIGRATE_DB": "true"})
    assert result["attempted_connect"] is True
    assert result["raised"] is False
