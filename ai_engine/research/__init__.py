"""Phase 8A Research Intelligence — Knowledge-first evidence before AI assumption."""

from ai_engine.research.planner import (
    BLOCKED_SOURCES,
    PHASE8A_LIVE_SOURCES,
    build_research_plan,
    classify_gap,
    extract_gaps_from_state,
)
from ai_engine.research.schemas import (
    ResearchClaim,
    ResearchPlan,
    ResearchResult,
    ResearchSourceRef,
    ResearchStatus,
)
from ai_engine.research.service import execute_research, research_gaps

__all__ = [
    "BLOCKED_SOURCES",
    "PHASE8A_LIVE_SOURCES",
    "ResearchClaim",
    "ResearchPlan",
    "ResearchResult",
    "ResearchSourceRef",
    "ResearchStatus",
    "build_research_plan",
    "classify_gap",
    "execute_research",
    "extract_gaps_from_state",
    "research_gaps",
]
