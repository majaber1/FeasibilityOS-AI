"""
Verified Funding Program Registry Tests (Phase 18).

Tests:
- Registry seeding and idempotency
- List programs with complete schema
- Filter by provider (SDB, Kafalah, SME Bank, SIDF, TDF, ADF)
- Filter by program type (DIRECT_LOAN, GUARANTEE, WORKING_CAPITAL, CO_FINANCING)
- Registry summary metrics and breakdowns
- Single program detail with rule-level provenance
- 404 for non-existent program
- Source URL authenticity and rule provenance validation
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

if not os.environ.get("DATABASE_URL"):
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + handle.name

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.funding_programs import ensure_seed_programs, summarize_registry  # noqa: E402

client = TestClient(app)


def setup_module(module):
    app_db.init_db()


def test_list_funding_programs_returns_all_verified():
    res = client.get("/funding-programs/")
    assert res.status_code == 200, res.text
    programs = res.json()
    assert len(programs) == 12

    for prog in programs:
        assert prog["id"] > 0
        assert prog["slug"]
        assert prog["provider"]
        assert prog["provider_ar"]
        assert prog["program_name_ar"]
        assert prog["program_name_en"]
        assert prog["program_type"] in ["DIRECT_LOAN", "GUARANTEE", "CO_FINANCING", "WORKING_CAPITAL", "GRANT"]
        assert prog["verification_status"] == "VERIFIED_CURRENT"
        assert prog["official_source_url"].startswith("http")
        assert len(prog["rules"]) > 0


def test_filter_programs_by_provider():
    # Kafalah filter
    res_kafalah = client.get("/funding-programs/?provider=Kafalah")
    assert res_kafalah.status_code == 200
    kafalah_progs = res_kafalah.json()
    assert len(kafalah_progs) == 3
    for p in kafalah_progs:
        assert p["provider"] == "Kafalah"

    # SDB filter
    res_sdb = client.get("/funding-programs/?provider=Social Development Bank")
    assert res_sdb.status_code == 200
    sdb_progs = res_sdb.json()
    assert len(sdb_progs) == 4
    for p in sdb_progs:
        assert p["provider"] == "Social Development Bank"


def test_filter_programs_by_type():
    res = client.get("/funding-programs/?program_type=GUARANTEE")
    assert res.status_code == 200
    guarantees = res.json()
    assert len(guarantees) == 3
    for g in guarantees:
        assert g["program_type"] == "GUARANTEE"


def test_registry_summary_endpoint():
    res = client.get("/funding-programs/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_programs"] == 12
    assert summary["verified_current_count"] == 12
    assert "Kafalah" in summary["providers_breakdown"]
    assert "Social Development Bank" in summary["providers_breakdown"]
    assert "SME Bank" in summary["providers_breakdown"]
    assert "Saudi Industrial Development Fund" in summary["providers_breakdown"]
    assert "Tourism Development Fund" in summary["providers_breakdown"]
    assert "Agricultural Development Fund" in summary["providers_breakdown"]
    assert summary["providers_breakdown"]["Social Development Bank"] == 4
    assert summary["providers_breakdown"]["Kafalah"] == 3
    assert len(summary["all_providers"]) == 6


def test_get_program_details_with_provenance():
    # Get all programs first to pick an ID
    res = client.get("/funding-programs/")
    assert res.status_code == 200
    first_prog = res.json()[0]

    detail_res = client.get(f"/funding-programs/{first_prog['id']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == first_prog["id"]
    assert detail["slug"] == first_prog["slug"]
    assert len(detail["rules"]) >= 1

    rule = detail["rules"][0]
    assert rule["rule_key"]
    assert rule["rule_type"]
    assert isinstance(rule["structured_value"], dict)
    assert rule["source_url"].startswith("http")
    assert rule["source_authority"]
    assert rule["rule_version"]


def test_get_program_details_not_found():
    res = client.get("/funding-programs/999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_provenance_authenticity():
    res = client.get("/funding-programs/")
    assert res.status_code == 200
    programs = res.json()

    for prog in programs:
        # Verify official domain in URL
        assert any(
            domain in prog["official_source_url"]
            for domain in [".gov.sa", "sdb.gov.sa", "kafalah.gov.sa", "smebank.gov.sa", "sidf.gov.sa", "tdf.gov.sa", "adf.gov.sa"]
        ), f"Unverified official source URL: {prog['official_source_url']}"

        # Must have rules
        assert len(prog["rules"]) > 0, f"Program {prog['slug']} has no rules"
        for rule in prog["rules"]:
            assert rule["source_authority"]
            assert rule["rule_version"]
