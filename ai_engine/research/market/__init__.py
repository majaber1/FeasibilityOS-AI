"""Phase 8B Controlled Market Research Intelligence."""

from ai_engine.research.market.competitor import research_competitors
from ai_engine.research.market.market_signal import research_market_signals
from ai_engine.research.market.planner import build_market_plan, classify_research_types
from ai_engine.research.market.pricing_signal import research_pricing_signals
from ai_engine.research.market.regulation import build_regulation_framework
from ai_engine.research.market.schemas import (
    CompetitorEvidence,
    MarketInsight,
    MarketResearchPlan,
    MarketResearchResult,
    MarketSignal,
    PricingSignal,
    RegulationSignal,
)
from ai_engine.research.market.service import (
    execute_market_research,
    execute_market_research_from_state,
    market_result_to_research_claims,
)

__all__ = [
    "CompetitorEvidence",
    "MarketInsight",
    "MarketResearchPlan",
    "MarketResearchResult",
    "MarketSignal",
    "PricingSignal",
    "RegulationSignal",
    "build_market_plan",
    "build_regulation_framework",
    "classify_research_types",
    "execute_market_research",
    "execute_market_research_from_state",
    "market_result_to_research_claims",
    "research_competitors",
    "research_market_signals",
    "research_pricing_signals",
]
