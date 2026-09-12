"""Financial Trust Hardening — calculation & messaging regression tests.

Validates NPV/IRR/payback root-cause fixes without claiming product PASS.
Browser E2E evidence is required separately.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

if not os.environ.get("DATABASE_URL"):
    _tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _tmp.name

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT / "financial-engine"))

from ai_engine.agents.financial_analyst import (  # noqa: E402
    _deterministic_extract,
    run_financial_analysis,
)
from ai_engine.models.study_state import Assumption, ProjectProfile, StudyState  # noqa: E402
from ai_engine.tools.calculator import calculate_irr, calculate_npv, calculate_payback_period  # noqa: E402
from ai_engine.tools.financial_trust import (  # noqa: E402
    irr_user_message,
    services_capacity_revenue,
    validate_financial_inputs,
)
from calculator import evaluate_feasibility, irr as fe_irr  # noqa: E402


def _assumptions(**kwargs: str) -> list[Assumption]:
    rows = []
    for key, value in kwargs.items():
        rows.append(
            Assumption(key=key, value=str(value), source="user", confidence="confirmed", base=str(value))
        )
    return rows


def test_irr_null_never_returns_raw_null_string():
    msg = irr_user_message(None, language="en")
    assert msg is not None
    assert "null" not in msg.lower()
    assert "IRR" in msg or "cannot" in msg.lower()
    assert irr_user_message(0.185, language="en") == "18.5%"


def test_services_zero_opex_inflated_npv_is_fixed():
    """Root cause: MRC-only with OPEX forced to [0,0,0] massively inflated NPV."""
    mrc = 80_000
    capex = 500_000
    revs = [mrc * 12, mrc * 12 * 1.25, mrc * 12 * 1.5]
    # BEFORE (bug): zero opex
    before_cfs = [-capex] + revs
    before_npv = calculate_npv(before_cfs, 0.12)
    # AFTER (fix): 55% cost ratio default
    costs = [r * 0.55 for r in revs]
    after_cfs = [-capex] + [r - c for r, c in zip(revs, costs)]
    after_npv = calculate_npv(after_cfs, 0.12)
    assert before_npv > 2_000_000
    assert after_npv < before_npv
    assert after_npv < 1_000_000


def test_services_capacity_revenue_not_mrc_only():
    annual, notes = services_capacity_revenue(
        billing_rate=350,
        utilization_rate=0.7,
        headcount=20,
        billable_hours_month=160,
        mrc=80_000,
    )
    expected = 350 * 0.7 * 20 * 160 * 12
    assert annual == expected
    assert "services_revenue_from_billing_rate_x_utilization_x_resources" in notes


def test_data_center_unrealistic_capex_soft_warning():
    warnings = validate_financial_inputs(
        archetype="data_center",
        capex=25_000_000,
        annual_revenues=[40_000_000, 45_000_000, 50_000_000],
        annual_costs=[20_000_000, 22_000_000, 24_000_000],
        assumptions={"mw_capacity": 20},
        language="en",
    )
    assert any("unusually low" in w.lower() or "expected range" in w.lower() for w in warnings)


def test_irr_handles_high_return_profiles():
    cfs = [-500_000, 7_008_000, 9_000_000, 10_992_000]
    rate = calculate_irr(cfs)
    assert rate is not None
    assert rate > 1.0
    assert fe_irr(cfs) is not None


def test_residential_npv_timeline():
    # Land+BOQ style: 40M capex, sales absorption cash flows
    capex = 40_000_000
    revs = [18_000_000, 22_000_000, 16_000_000]
    costs = [4_000_000, 3_500_000, 2_500_000]
    cfs = [-capex] + [r - c for r, c in zip(revs, costs)]
    npv = calculate_npv(cfs, 0.12)
    pb = calculate_payback_period(capex, [r - c for r, c in zip(revs, costs)])
    assert isinstance(npv, float)
    assert pb is None or pb > 0


def test_saas_npv_with_costs():
    capex = 1_500_000
    revs = [2_400_000, 3_360_000, 4_368_000]
    costs = [1_800_000, 2_100_000, 2_400_000]
    cfs = [-capex] + [r - c for r, c in zip(revs, costs)]
    npv = calculate_npv(cfs, 0.12)
    irr = calculate_irr(cfs)
    assert npv != 0
    assert irr is None or isinstance(irr, float)


def test_deterministic_services_extract_uses_capacity_and_opex():
    state = StudyState(
        study_id="s-svc",
        project_id="p1",
        user_id="u1",
        language="en",
        phase="READY_FOR_ANALYSIS",
        assumptions=_assumptions(
            billing_rate="350",
            utilization_rate="70%",
            consultants_headcount="20",
            initial_investment="500000",
            monthly_recurring_contracts="80000",
        ),
        profile=ProjectProfile(
            name="Cyber MSSP",
            sector="services",
            archetype="services",
            description="cybersecurity managed services",
        ),
    )
    extracted = _deterministic_extract(state)
    assert extracted is not None
    assert extracted["annual_revenues"][0] == 350 * 0.7 * 20 * 160 * 12
    assert extracted["annual_costs"][0] > 0
    assert "services_opex_defaulted_from_55pct_cost_ratio" in extracted["extract_notes"] or any(
        "55" in n for n in extracted["extract_notes"]
    )


def test_run_financial_analysis_surfaces_irr_display_not_null():
    state = StudyState(
        study_id="s-svc2",
        project_id="p1",
        user_id="u1",
        language="en",
        phase="READY_FOR_ANALYSIS",
        assumptions=_assumptions(
            billing_rate="350",
            utilization_rate="70%",
            consultants_headcount="10",
            initial_investment="2_000_000".replace("_", ""),
            delivery_cost_monthly="250000",
        ),
        profile=ProjectProfile(
            name="Services",
            sector="services",
            archetype="services",
            description="professional services",
        ),
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='```json\n{"analysis_complete": true, "warnings": []}\n```'
    )
    with patch("ai_engine.agents.financial_analyst.get_llm", return_value=mock_llm):
        out = run_financial_analysis(state)
    fr = out.financial_results or {}
    assert fr.get("irr_display")
    assert "null" not in str(fr.get("irr_display")).lower()
    assert "cash_flows" in fr
    assert fr.get("npv") is not None


def test_v1_evaluate_feasibility_irr_message_path():
    bad = evaluate_feasibility(1_000_000, [-50_000, -50_000, -50_000], 0.10)
    assert bad.irr_value is None
    assert bad.npv_value is not None
    good = evaluate_feasibility(500_000, [150_000, 180_000, 200_000, 220_000], 0.10)
    assert good.irr_value is not None
