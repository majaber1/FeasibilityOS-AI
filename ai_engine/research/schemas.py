"""Phase 8A research intelligence schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ResearchStatus = Literal[
    "not_started",
    "planned",
    "searching",
    "partial",
    "complete",
    "blocked",
    "failed",
]

ClaimSourceType = Literal[
    "official",
    "user_input",
    "document",
    "ai_assumption",
    "unverified",
]


@dataclass
class ResearchSourceRef:
    source_key: str
    connector_id: str
    reason: str
    status: str = "planned"
    blocked: bool = False
    block_reason: str | None = None


@dataclass
class ResearchClaim:
    """Claim produced by research (maps into StudyState Claim shape)."""

    statement: str
    source_type: ClaimSourceType = "official"
    source_url: str | None = None
    retrieved_date: str | None = None
    confidence: float = 0.7
    metric_key: str | None = None
    value: Any = None
    unit: str | None = None
    period: str | None = None
    source_key: str | None = None
    from_knowledge: bool = False
    document_id: str | None = None
    chunk_id: str | None = None
    origin: str | None = None

    def to_claim_dict(self) -> dict[str, Any]:
        origin = self.origin
        if origin is None:
            origin = "knowledge" if self.from_knowledge else "research"
        return {
            "statement": self.statement,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "retrieved_date": self.retrieved_date
            or datetime.now(timezone.utc).date().isoformat(),
            "confidence": float(self.confidence),
            "origin": origin,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "source_key": self.source_key,
        }


@dataclass
class ResearchPlan:
    study_id: str
    gaps: list[str]
    sources: list[ResearchSourceRef]
    queries: list[str]
    status: ResearchStatus = "planned"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "gaps": list(self.gaps),
            "sources": [asdict(s) for s in self.sources],
            "queries": list(self.queries),
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class ResearchResult:
    plan: ResearchPlan
    status: ResearchStatus
    claims: list[ResearchClaim] = field(default_factory=list)
    knowledge_hits: int = 0
    live_fetches: int = 0
    blocked_sources: list[str] = field(default_factory=list)
    unavailable_sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    attempts: list[dict[str, Any]] = field(default_factory=list)
    # Phase 8B — Controlled Market Research public payload (optional)
    market_research: dict[str, Any] | None = None
    completed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_public_dict(),
            "status": self.status,
            "claims": [
                c.to_claim_dict()
                | {
                    "metric_key": c.metric_key,
                    "value": c.value,
                    "unit": c.unit,
                    "period": c.period,
                    "source_key": c.source_key,
                    "from_knowledge": c.from_knowledge,
                }
                for c in self.claims
            ],
            "knowledge_hits": self.knowledge_hits,
            "live_fetches": self.live_fetches,
            "blocked_sources": list(self.blocked_sources),
            "unavailable_sources": list(self.unavailable_sources),
            "errors": list(self.errors),
            "attempts": list(self.attempts),
            "market_research": self.market_research,
            "completed_at": self.completed_at,
        }
