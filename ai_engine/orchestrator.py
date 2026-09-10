from __future__ import annotations

from typing import Literal

from langgraph.graph import StateGraph, END

from .models.study_state import StudyState
from .agents.discovery import run_discovery
from .agents.evidence import run_evidence
from .agents.assumption import run_assumptions
from .agents.financial_analyst import run_financial_analysis
from .agents.risk import run_risk_analysis
from .agents.decision import run_decision
from .agents.funding import run_funding

PHASE_TRANSITIONS = {
    "DRAFT": "discovery",
    "UNDERSTANDING": "discovery",
    "NEEDS_INFORMATION": "discovery",
    "EVIDENCE_REVIEW": "evidence",
    "ASSUMPTIONS_REVIEW": "assumptions",
    "READY_FOR_ANALYSIS": "financial",
    "ANALYZED": "risk",
    "DECISION_READY": "decision",
    # First entry to funding runs the funding agent; subsequent messages can re-run it.
    "FUNDING_READY": "funding",
    "REPORT_READY": "funding",
}

_CHALLENGE_MARKERS = (
    "CHALLENGE LOOP",
    "CHALLENGE ASSUMPTION",
    "REVISE ASSUMPTION",
    "CHANGE ASSUMPTION",
    "UPDATE ASSUMPTION",
    "RECALCULATE WITH",
)


def _wants_challenge(state: StudyState) -> bool:
    """User asked to revise a major assumption after the model was built."""
    msgs = state.messages or []
    if not msgs:
        return False
    last = msgs[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    text = (content or "").upper()
    return any(m in text for m in _CHALLENGE_MARKERS)


def route_by_phase(state: StudyState) -> str:
    if state.error:
        return "error_handler"
    # Explicit challenge: force assumption revision even after decision/funding.
    if _wants_challenge(state) and state.profile_confirmed and state.evidence_approved:
        return "assumptions"
    phase = state.phase
    return PHASE_TRANSITIONS.get(phase, "discovery")


def error_handler(state: StudyState) -> StudyState:
    state.next_action = "retry"
    state.blocking_reason = state.error
    return state


def build_graph() -> StateGraph:
    graph = StateGraph(StudyState)

    graph.add_node("discovery", run_discovery)
    graph.add_node("evidence", run_evidence)
    graph.add_node("assumptions", run_assumptions)
    graph.add_node("financial", run_financial_analysis)
    graph.add_node("risk", run_risk_analysis)
    graph.add_node("decision", run_decision)
    graph.add_node("funding", run_funding)
    graph.add_node("error_handler", error_handler)

    graph.set_conditional_entry_point(route_by_phase)

    graph.add_edge("discovery", END)
    graph.add_edge("evidence", END)
    graph.add_edge("assumptions", END)
    graph.add_edge("financial", END)
    graph.add_edge("risk", END)
    graph.add_edge("decision", END)
    graph.add_edge("funding", END)
    graph.add_edge("error_handler", END)

    return graph


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


async def run_study_step(state: StudyState) -> StudyState:
    graph = get_graph()
    result = await graph.ainvoke(state.model_dump())
    return StudyState(**result)


def run_study_step_sync(state: StudyState) -> StudyState:
    graph = get_graph()
    result = graph.invoke(state.model_dump())
    return StudyState(**result)
