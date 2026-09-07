"""
Deterministic funding gap calculation (Phase 14).

Reuses data the study already has rather than asking the user to re-enter
it: the total project requirement prefers the study's "capex" assumption
(the same canonical key the Phase 10 financial engine uses) and falls back
to the project's stated investment amount. Owner contribution and existing
available facilities are read from the study's assumptions under two more
canonical keys (owner_contribution, existing_available_facilities) --
reusing the existing, versioned, provenance-tracked Assumptions system
(Phase 8) instead of inventing a parallel input mechanism.

Missing inputs are never silently treated as zero without being flagged:
funding_gap is still computed (using 0 for a missing contribution/facility,
the only sensible number to subtract), but missing_inputs lists exactly
which figures were assumed absent so the caller can tell "$0 confirmed"
apart from "not yet provided".
"""
from __future__ import annotations

from typing import Optional

REQUIREMENT_ASSUMPTION_KEY = "capex"
OWNER_CONTRIBUTION_KEY = "owner_contribution"
EXISTING_FACILITIES_KEY = "existing_available_facilities"


def compute_funding_gap(
    *,
    capex_assumption: Optional[float],
    project_investment: float,
    owner_contribution: Optional[float],
    existing_facilities: Optional[float],
) -> dict:
    if capex_assumption is not None:
        total_requirement = capex_assumption
        requirement_source = "capex_assumption"
    else:
        total_requirement = project_investment
        requirement_source = "project_investment"

    missing_inputs = []
    owner = owner_contribution
    if owner is None:
        missing_inputs.append(OWNER_CONTRIBUTION_KEY)
        owner = 0.0

    facilities = existing_facilities
    if facilities is None:
        missing_inputs.append(EXISTING_FACILITIES_KEY)
        facilities = 0.0

    funding_gap = total_requirement - owner - facilities

    return {
        "total_project_requirement": total_requirement,
        "requirement_source": requirement_source,
        "owner_available_capital": owner,
        "owner_available_capital_status": "MISSING_DATA" if OWNER_CONTRIBUTION_KEY in missing_inputs else "CALCULATED",
        "existing_available_facilities": facilities,
        "existing_available_facilities_status": "MISSING_DATA" if EXISTING_FACILITIES_KEY in missing_inputs else "CALCULATED",
        "funding_gap": funding_gap,
        "missing_inputs": missing_inputs,
    }
