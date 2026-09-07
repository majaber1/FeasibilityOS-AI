"""Company financial health engine: deterministic ratios, no invented data."""
import os
import sys
import tempfile
import uuid
from pathlib import Path

if not os.environ.get("DATABASE_URL"):
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + handle.name

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app import db as app_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.financial_health import (  # noqa: E402
    STATUS_CALCULATED,
    STATUS_MISSING,
    STATUS_NOT_APPLICABLE,
    compute_metrics,
    summarize,
)

client = TestClient(app)


def setup_module(module):
    app_db.init_db()


def _headers(prefix: str):
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    password = "Sup3rSecret!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _study(headers):
    project = client.post(
        "/projects/", headers=headers, json={"name": "شركة قائمة", "industry": "retail", "investment": 3000000}
    ).json()
    return client.post(
        "/feasibility/",
        headers=headers,
        json={"project_id": project["id"], "title": "توسع الشركة", "industry": "retail", "investment": 3000000},
    ).json()


def _set_period(headers, study_id, period, **metrics):
    resp = client.put(f"/studies/{study_id}/financial-periods/{period}", headers=headers, json=metrics)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Pure function unit tests -------------------------------------------------

def test_healthy_profitable_company():
    period = {
        "revenue": 12500000, "gross_profit": 6000000, "ebitda": 2500000, "operating_profit": 2200000,
        "net_profit": 1800000, "current_assets": 3000000, "current_liabilities": 1500000, "inventory": 500000,
        "existing_debt": 1200000, "equity": 4000000, "annual_debt_service": 420000, "interest_expense": 150000,
    }
    metrics = compute_metrics(period)
    assert metrics["net_margin"].status == STATUS_CALCULATED
    assert round(metrics["net_margin"].value, 4) == round(1800000 / 12500000, 4)
    assert metrics["current_ratio"].value == 2.0
    assert metrics["dscr"].value == 2500000 / 420000
    summary = summarize(metrics)
    assert summary["profitability"] == "STRONG"
    assert summary["liquidity"] == "STRONG"
    assert summary["debt_service_capacity"] == "STRONG"
    # revenue_growth needs a prior period, which this single-period snapshot
    # doesn't have -- MISSING_DATA there is correct, not a bug, so coverage
    # is PARTIAL rather than FULL.
    assert summary["data_coverage"] == "PARTIAL"
    assert metrics["revenue_growth"].status == STATUS_MISSING


def test_loss_making_company():
    period = {"revenue": 1000000, "net_profit": -200000}
    metrics = compute_metrics(period)
    assert metrics["net_margin"].status == STATUS_CALCULATED
    assert metrics["net_margin"].value == -0.2
    summary = summarize(metrics)
    assert summary["profitability"] == "WEAK"


def test_high_leverage_company():
    period = {"existing_debt": 10000000, "ebitda": 1000000}
    metrics = compute_metrics(period)
    assert metrics["debt_to_ebitda"].value == 10.0
    summary = summarize(metrics)
    assert summary["leverage"] == "HIGH"


def test_weak_liquidity():
    period = {"current_assets": 500000, "current_liabilities": 1000000}
    metrics = compute_metrics(period)
    assert metrics["current_ratio"].value == 0.5
    summary = summarize(metrics)
    assert summary["liquidity"] == "WEAK"


def test_zero_ebitda_makes_debt_to_ebitda_not_applicable_not_zero():
    period = {"existing_debt": 500000, "ebitda": 0}
    metrics = compute_metrics(period)
    assert metrics["debt_to_ebitda"].status == STATUS_NOT_APPLICABLE
    assert metrics["debt_to_ebitda"].value is None


def test_zero_equity_makes_debt_to_equity_not_applicable():
    period = {"existing_debt": 500000, "equity": 0}
    metrics = compute_metrics(period)
    assert metrics["debt_to_equity"].status == STATUS_NOT_APPLICABLE


def test_zero_debt_is_a_real_calculated_zero_not_missing():
    period = {"existing_debt": 0, "equity": 1000000, "ebitda": 500000}
    metrics = compute_metrics(period)
    assert metrics["debt_to_equity"].status == STATUS_CALCULATED
    assert metrics["debt_to_equity"].value == 0.0
    assert metrics["debt_to_ebitda"].status == STATUS_CALCULATED
    assert metrics["debt_to_ebitda"].value == 0.0


def test_missing_current_liabilities_is_missing_not_zero():
    period = {"current_assets": 500000}
    metrics = compute_metrics(period)
    assert metrics["current_ratio"].status == STATUS_MISSING
    assert metrics["working_capital"].status == STATUS_MISSING


def test_missing_annual_debt_service_is_missing_not_zero():
    period = {"ebitda": 1000000}
    metrics = compute_metrics(period)
    assert metrics["dscr"].status == STATUS_MISSING


def test_missing_inventory_is_missing_not_zero_in_quick_ratio():
    period = {"current_assets": 500000, "current_liabilities": 250000}
    metrics = compute_metrics(period)
    assert metrics["quick_ratio"].status == STATUS_MISSING
    # current_ratio doesn't need inventory, so it's still calculable.
    assert metrics["current_ratio"].status == STATUS_CALCULATED


def test_revenue_growth_requires_prior_period():
    metrics_no_prior = compute_metrics({"revenue": 1000000})
    assert metrics_no_prior["revenue_growth"].status == STATUS_MISSING

    metrics_with_prior = compute_metrics({"revenue": 1100000}, prior_period={"revenue": 1000000})
    assert metrics_with_prior["revenue_growth"].status == STATUS_CALCULATED
    assert round(metrics_with_prior["revenue_growth"].value, 4) == 0.10


def test_deterministic_same_input_same_output():
    period = {"revenue": 5000000, "net_profit": 400000, "existing_debt": 1000000, "ebitda": 900000}
    first = compute_metrics(period)
    second = compute_metrics(period)
    assert {k: v.value for k, v in first.items()} == {k: v.value for k, v in second.items()}
    assert summarize(first) == summarize(second)


def test_data_coverage_partial_when_some_metrics_missing():
    metrics = compute_metrics({"revenue": 1000000, "net_profit": 100000})
    summary = summarize(metrics)
    assert summary["data_coverage"] == "PARTIAL"


# --- API-level tests -----------------------------------------------------------

def test_api_computes_from_recorded_period_and_distinguishes_prior_period():
    headers = _headers("health_api")
    study = _study(headers)
    _set_period(headers, study["id"], "FY2024", revenue=10000000, net_profit=500000)
    _set_period(headers, study["id"], "FY2025", revenue=12500000, net_profit=1800000)

    resp = client.get(f"/studies/{study['id']}/financial-health/", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["period"] == "FY2025"  # latest by default
    assert body["prior_period"] == "FY2024"
    assert body["metrics"]["revenue_growth"]["status"] == "CALCULATED"
    assert round(body["metrics"]["revenue_growth"]["value"], 4) == 0.25


def test_api_explicit_period_query_param():
    headers = _headers("health_api_period")
    study = _study(headers)
    _set_period(headers, study["id"], "FY2024", revenue=10000000)
    _set_period(headers, study["id"], "FY2025", revenue=12500000)

    resp = client.get(f"/studies/{study['id']}/financial-health/?period=FY2024", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "FY2024"
    assert body["prior_period"] is None
    assert body["metrics"]["revenue_growth"]["status"] == "MISSING_DATA"


def test_api_unavailable_when_no_periods_recorded():
    headers = _headers("health_api_empty")
    study = _study(headers)
    resp = client.get(f"/studies/{study['id']}/financial-health/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_status"] == "NO_PERIODS_RECORDED"
    assert body["metrics"]
    assert all(metric["value"] is None for metric in body["metrics"].values())
    assert all(metric["status"] == "MISSING_DATA" for metric in body["metrics"].values())
    assert body["summary"] == summarize(compute_metrics({}))
    assert body["period"] == "NO_DATA"
    assert body["prior_period"] is None


def test_api_unknown_explicit_period_remains_not_found():
    headers = _headers("health_missing_period")
    study = _study(headers)
    _set_period(headers, study["id"], "FY2025", revenue=1000000)
    assert client.get(f"/studies/{study['id']}/financial-health/?period=FY2099", headers=headers).status_code == 404


def test_financial_health_ownership_isolation():
    owner = _headers("health_owner")
    other = _headers("health_other")
    study = _study(owner)
    _set_period(owner, study["id"], "FY2025", revenue=1000000)
    assert client.get(f"/studies/{study['id']}/financial-health/", headers=other).status_code == 403
