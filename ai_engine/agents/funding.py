"""Archetype-specific intelligent funding recommendations (V2 study engine)."""
from __future__ import annotations

from ..models.study_state import StudyState

# Deterministic catalogs — funding logic MUST differ by project type.
FUNDING_PLAYBOOKS: dict[str, dict] = {
    "saas_digital": {
        "readiness_focus": ["unit_economics", "retention", "runway_months", "cap_table"],
        "instruments": [
            {"name": "Angel / pre-seed", "fit": "idea-MVP SaaS", "notes": "SAFE or equity; avoid debt until MRR stability"},
            {"name": "Venture capital (seed/Series A)", "fit": "proven traction", "notes": "Requires clear CAC payback and growth"},
            {"name": "Government innovation funds", "fit": "KSA Vision 2030 tech", "notes": "Non-dilutive or hybrid programs"},
        ],
        "avoid": ["construction loans", "project finance", "mortgage take-out"],
    },
    "services": {
        "readiness_focus": ["take_rate", "contribution_margin", "cash_burn", "regulatory_license"],
        "instruments": [
            {"name": "Angel / venture seed", "fit": "marketplace / mobility startup", "notes": "Equity for growth and driver supply incentives"},
            {"name": "Venture debt (later)", "fit": "post-product-market fit", "notes": "Only after stable unit economics"},
            {"name": "Corporate strategic investment", "fit": "fleet / payments partners", "notes": "Commercial + capital partnership"},
            {"name": "Govtech / mobility innovation grants", "fit": "Saudi localization", "notes": "Non-dilutive where eligible"},
        ],
        "avoid": ["real-estate development finance", "Wafi off-plan escrow", "infra project finance"],
    },
    "real_estate": {
        "readiness_focus": ["land_title", "permits_wafi", "presales", "loan_to_cost"],
        "instruments": [
            {"name": "Development / construction facility", "fit": "gated compound build", "notes": "Bank LTC against land + BOQ; drawdown by milestones"},
            {"name": "Off-plan escrow / Wafi-aligned collections", "fit": "presales", "notes": "Buyer deposits reduce peak funding gap"},
            {"name": "Mezzanine / preferred equity", "fit": "equity gap", "notes": "Bridge between senior debt and sponsor equity"},
            {"name": "Mortgage take-out facilitation", "fit": "end-user sales", "notes": "Supports absorption and cash conversion"},
        ],
        "avoid": ["SaaS venture rounds", "angel SAFE for software", "hyperscaler colo prepay structures"],
    },
    "data_center": {
        "readiness_focus": ["mw_interconnection", "pue", "anchor_tenants", "power_contract"],
        "instruments": [
            {"name": "Infrastructure / project finance", "fit": "40MW+ campus", "notes": "Long-tenor debt sized to contracted capacity"},
            {"name": "Strategic hyperscaler / colo pre-leases", "fit": "offtake certainty", "notes": "Improves DSCR and bankability"},
            {"name": "Infrastructure equity funds", "fit": "core+ infra", "notes": "Patient capital for build-stabilize"},
            {"name": "Green / energy-efficiency facilities", "fit": "PUE and cooling", "notes": "Tied to efficiency KPIs"},
        ],
        "avoid": ["consumer mortgage products", "early-stage SaaS seed", "short-term working-capital only"],
    },
    "retail": {
        "readiness_focus": ["lease", "inventory_turns", "gross_margin"],
        "instruments": [
            {"name": "Working capital / inventory finance", "fit": "stock cycle", "notes": "Short tenor revolving"},
            {"name": "Fit-out lease finance", "fit": "store build", "notes": "Asset-backed where possible"},
        ],
        "avoid": ["hyperscale project finance"],
    },
    "industrial": {
        "readiness_focus": ["utilization", "capex_machinery", "offtake"],
        "instruments": [
            {"name": "Equipment finance / leasing", "fit": "machinery CAPEX", "notes": "Asset-backed"},
            {"name": "SIDF / industrial programs", "fit": "KSA manufacturing", "notes": "Development fund eligibility"},
        ],
        "avoid": ["consumer VC seed"],
    },
    "franchise": {
        "readiness_focus": ["franchise_fee", "unit_economics", "territory"],
        "instruments": [
            {"name": "Franchisee bank facility", "fit": "fit-out + working capital", "notes": "Often requires franchisor comfort letter"},
        ],
        "avoid": ["data-center project finance"],
    },
}


def _playbook(archetype: str) -> dict:
    return FUNDING_PLAYBOOKS.get(archetype) or FUNDING_PLAYBOOKS["services"]


def run_funding(state: StudyState) -> StudyState:
    """Produce readiness + intelligent funding package; remain on FUNDING_READY."""
    archetype = state.profile.archetype if state.profile else "unknown"
    book = _playbook(archetype)
    verdict = state.verdict or "INSUFFICIENT_EVIDENCE"
    npv = None
    if state.financial_results:
        npv = state.financial_results.get("npv")

    readiness_status = "NOT_READY"
    if verdict in {"GO", "GO_WITH_CONDITIONS"} and npv is not None and float(npv) >= 0:
        readiness_status = "READY"
    elif verdict in {"GO", "GO_WITH_CONDITIONS", "DEFER"}:
        readiness_status = "CONDITIONALLY_READY"
    elif verdict == "NO_GO":
        readiness_status = "NOT_READY"

    from datetime import datetime, timezone

    funding_package = {
        "archetype": archetype,
        "readiness_status": readiness_status,
        "readiness_focus": book["readiness_focus"],
        "recommended_instruments": book["instruments"],
        "avoid_instruments": book["avoid"],
        "verdict_context": verdict,
        "npv": npv,
        "decision_version": state.decision_version,
        "assumptions_version": int(getattr(state, "assumptions_version", 0) or 0),
    }

    report_outline = {
        "title": f"Feasibility Report — {archetype}",
        "sections": [
            "Executive summary & verdict",
            "Project profile & archetype",
            "Evidence basis",
            "Assumptions (versioned)",
            "Financial model (NPV / IRR / payback)",
            "Risk register & mitigations",
            "Decision rationale",
            "Funding readiness & recommended instruments",
            "Next diligence checklist",
        ],
        "verdict": verdict,
        "assumptions_version": funding_package["assumptions_version"],
        "decision_version": state.decision_version,
        "archetype": archetype,
        "readiness_status": readiness_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if state.financial_results is None:
        state.financial_results = {}
    state.financial_results = {
        **dict(state.financial_results),
        "funding_package": funding_package,
        "report_outline": report_outline,
    }

    lines = [
        f"## Intelligent Funding ({archetype})",
        f"Readiness: **{readiness_status}** (verdict={verdict}, NPV={npv})",
        "### Focus areas",
        *[f"- {x}" for x in book["readiness_focus"]],
        "### Recommended instruments",
        *[f"- {i['name']}: {i['fit']} — {i['notes']}" for i in book["instruments"]],
        "### Do not use for this archetype",
        *[f"- {x}" for x in book["avoid"]],
        "",
        "## Report outline",
        *[f"- {s}" for s in report_outline["sections"]],
    ]
    from langchain_core.messages import AIMessage

    state.messages.append(AIMessage(content="\n".join(lines)))
    state.phase = "REPORT_READY"
    state.next_action = "review_report"
    state.error = None
    return state
