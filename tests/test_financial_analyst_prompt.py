"""Unit tests for financial analyst prompt safety and deterministic extraction."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

if not os.environ.get("DATABASE_URL"):
    _TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _TMP.close()
    os.environ["DATABASE_URL"] = "sqlite:///" + _TMP.name

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "backend"))

from ai_engine.agents.financial_analyst import (  # noqa: E402
    run_financial_analysis,
    _deterministic_extract,
)
from ai_engine.models.study_state import Assumption, Claim, StudyState  # noqa: E402


def _uber_state() -> StudyState:
    return StudyState(
        study_id="study_test",
        project_id="14",
        user_id="11",
        language="en",
        phase="READY_FOR_ANALYSIS",
        assumptions=[
            Assumption(key="Initial investment", value="5000000 SAR", source="user", confidence="confirmed", base="5000000"),
            Assumption(key="Average trip value (ATV)", value="40 SAR", source="user", confidence="medium", low="30", base="40", high="55"),
            Assumption(key="Take-rate", value="22%", source="user", confidence="medium", low="18%", base="22%", high="25%"),
            Assumption(key="Monthly rides Y1 average", value="12000", source="user", confidence="medium", base="12000"),
            Assumption(key="Monthly fixed opex", value="280000 SAR", source="user", confidence="medium", base="280000"),
            Assumption(key="Variable cost per ride", value="3 SAR", source="user", confidence="medium", base="3"),
            Assumption(key="Discount rate for NPV", value="12%", source="user", confidence="confirmed", base="12%"),
        ],
        claims=[
            Claim(statement="Seed budget 5,000,000 SAR", source_type="user_input", confidence=0.9),
        ],
    )


def test_deterministic_extract_from_uber_assumptions():
    extracted = _deterministic_extract(_uber_state())
    assert extracted is not None
    assert extracted["capex"] == 5000000
    assert extracted["discount_rate"] == 0.12
    assert extracted["annual_revenues"][0] > 0
    assert extracted["annual_costs"][0] > 0


def test_explain_prompt_no_longer_raises_keyerror_on_braces():
    """Regression: .format() previously KeyError'd on JSON key revenue_projections."""
    state = _uber_state()

    extract_payload = {
        "capex": 5000000,
        "annual_revenues": [1_267_200, 1_774_080, 2_306_304],
        "annual_costs": [3_796_000, 4_365_400, 4_745_000],
        "discount_rate": 0.12,
    }

    mock_extract_llm = MagicMock()
    mock_extract_llm.invoke.return_value = MagicMock(
        content="```json\n" + __import__("json").dumps(extract_payload) + "\n```"
    )
    mock_explain_llm = MagicMock()
    mock_explain_llm.invoke.return_value = MagicMock(
        content='```json\n{"analysis_complete": true, "warnings": []}\n```'
    )

    def _get_llm(task="general"):
        return mock_extract_llm if task == "extraction" else mock_explain_llm

    with patch("ai_engine.agents.financial_analyst.get_llm", side_effect=_get_llm):
        result = run_financial_analysis(state)

    assert result.error is None
    assert result.phase == "ANALYZED"
    assert result.financial_results is not None
    assert result.financial_results["capex"] == 5000000
    assert "npv" in result.financial_results
    assert "revenue_projections" in result.financial_results
