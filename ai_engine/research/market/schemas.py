"""Phase 8B Controlled Market Research — structured, traceable schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ResearchType = Literal[
    "COMPETITOR",
    "MARKET_SIZE",
    "PRICING",
    "REGULATION",
    "SECTOR_SIGNAL",
]

EvidenceStatus = Literal[
    "VERIFIED",
    "NOT_VERIFIED",
    "NOT_FOUND",
    "PARTIAL",
    "CONFLICT",
]

# Governed sources for Phase 8B (live + future placeholders only).
LIVE_MARKET_SOURCES: tuple[str, ...] = ("gastat", "misa")
PLACEHOLDER_MARKET_SOURCES: tuple[str, ...] = ("sama", "zatca", "nca")
ALL_MARKET_SOURCES: tuple[str, ...] = LIVE_MARKET_SOURCES + PLACEHOLDER_MARKET_SOURCES


@dataclass
class CompetitorEvidence:
    name: str
    source_url: str | None
    evidence_type: str
    geography: str
    confidence: float
    evidence_reference: str
    status: EvidenceStatus = "NOT_VERIFIED"
    source_key: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MarketSignal:
    metric: str
    value: Any
    period: str | None
    source: str
    evidence_reference: str
    source_url: str | None = None
    status: EvidenceStatus = "VERIFIED"
    source_key: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
    confidence: float = 0.8

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PricingSignal:
    item: str
    price: Any | None
    currency: str | None
    unit: str | None
    source_url: str | None
    evidence_reference: str
    status: EvidenceStatus = "NOT_FOUND"
    source_key: str | None = None
    confidence: float = 0.0
    document_id: str | None = None
    chunk_id: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegulationSignal:
    authority: str
    requirement: str
    sector: str
    source_reference: str
    status: EvidenceStatus = "PARTIAL"
    source_key: str | None = None
    source_url: str | None = None
    confidence: float = 0.4

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MarketInsight:
    """User-facing insight with mandatory provenance (never 'AI thinks')."""

    insight: str
    research_type: ResearchType
    source: str
    official_url: str | None
    evidence_reference: str
    confidence: float
    status: EvidenceStatus
    source_key: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MarketResearchPlan:
    study_id: str
    business_idea: str
    sector: str
    geography: str
    research_types: list[ResearchType]
    selected_sources: list[str]
    placeholder_sources: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MarketResearchResult:
    plan: MarketResearchPlan
    status: EvidenceStatus
    competitors: list[CompetitorEvidence] = field(default_factory=list)
    market_signals: list[MarketSignal] = field(default_factory=list)
    pricing_signals: list[PricingSignal] = field(default_factory=list)
    regulation_signals: list[RegulationSignal] = field(default_factory=list)
    insights: list[MarketInsight] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    attempts: list[dict[str, Any]] = field(default_factory=list)
    knowledge_hits: int = 0
    live_fetches: int = 0
    cache_hits: int = 0
    duration_ms: float = 0.0
    completed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_public_dict(),
            "status": self.status,
            "competitors": [c.to_public_dict() for c in self.competitors],
            "market_signals": [m.to_public_dict() for m in self.market_signals],
            "pricing_signals": [p.to_public_dict() for p in self.pricing_signals],
            "regulation_signals": [r.to_public_dict() for r in self.regulation_signals],
            "insights": [i.to_public_dict() for i in self.insights],
            "conflicts": list(self.conflicts),
            "attempts": list(self.attempts),
            "knowledge_hits": self.knowledge_hits,
            "live_fetches": self.live_fetches,
            "cache_hits": self.cache_hits,
            "duration_ms": self.duration_ms,
            "completed_at": self.completed_at,
        }
