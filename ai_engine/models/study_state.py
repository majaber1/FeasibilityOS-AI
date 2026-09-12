from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from langgraph.graph import add_messages

StudyPhase = Literal[
    "DRAFT",
    "ARCHETYPE_CLASSIFICATION",
    "UNDERSTANDING",
    "NEEDS_INFORMATION",
    "EVIDENCE_REVIEW",
    "ASSUMPTIONS_REVIEW",
    "READY_FOR_ANALYSIS",
    "ANALYZED",
    "DECISION_READY",
    "FUNDING_READY",
    "REPORT_READY",
]

ProjectArchetype = Literal[
    "saas_digital",
    "real_estate",
    "data_center",
    "retail",
    "industrial",
    "services",
    "other",
    "franchise",
    "unknown",
]

DecisionVerdict = Literal[
    "GO", "GO_WITH_CONDITIONS", "DEFER", "NO_GO", "INSUFFICIENT_EVIDENCE"
]


class ProjectProfile(BaseModel):
    archetype: ProjectArchetype = "unknown"
    sector: str = ""
    stage: str = ""
    decision_goal: str = ""
    language: Literal["ar", "en"] = "ar"
    missing_information: List[str] = []
    recommended_model: str = ""
    archetype_confirmed: bool = False
    # For services only: "professional" (default) or "mobility" (Uber-like).
    services_variant: Optional[str] = None


class Assumption(BaseModel):
    key: str
    value: str
    source: str
    confidence: Literal["confirmed", "medium", "low"]
    low: Optional[str] = None
    base: Optional[str] = None
    high: Optional[str] = None
    origin: Literal["user", "ai_estimated", "document", "default", "rule_fallback", "knowledge_reference"] = "user"
    input_type: Optional[str] = None
    unit: Optional[str] = None
    label_en: Optional[str] = None
    label_ar: Optional[str] = None
    ai_estimated: bool = False
    knowledge_refs: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_confidence: Optional[float] = None
    knowledge_influence: Optional[Dict[str, Any]] = None


class Claim(BaseModel):
    statement: str
    source_type: Literal["official", "user_input", "document", "ai_assumption", "unverified"]
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    confidence: float = 0.0
    # Phase 8A provenance — optional, never required for legacy claims
    origin: Optional[str] = None  # research | knowledge | user | ai_assumption
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_key: Optional[str] = None


class StudyState(BaseModel):
    study_id: str
    project_id: str
    user_id: str
    language: Literal["ar", "en"] = "ar"

    phase: StudyPhase = "DRAFT"
    phase_history: List[str] = []

    messages: Annotated[List, add_messages] = []

    profile: Optional[ProjectProfile] = None
    profile_confirmed: bool = False

    claims: List[Claim] = []
    evidence_approved: bool = False

    assumptions: List[Assumption] = []
    assumptions_approved: bool = False
    assumptions_version: int = 0

    discovery_questions: List[Dict[str, Any]] = Field(default_factory=list)
    structured_answers: Dict[str, Any] = Field(default_factory=dict)

    financial_snapshot_id: Optional[str] = None
    financial_results: Optional[dict] = None

    verdict: Optional[DecisionVerdict] = None
    decision_rationale: Optional[str] = None
    decision_conditions: List[str] = []
    decision_risks: List[str] = []
    decision_version: int = 0

    next_action: Optional[str] = None
    blocking_reason: Optional[str] = None
    error: Optional[str] = None

    # Phase 6 — Evidence Pack from Knowledge Intelligence (never embeddings)
    knowledge_context: Optional[Dict[str, Any]] = None

    # Phase 8A — Research Intelligence (Knowledge/MCP before AI assumption)
    research_context: Optional[Dict[str, Any]] = None
    research_status: Optional[str] = None
    research_attempts: List[Dict[str, Any]] = Field(default_factory=list)

    # Phase 8B — Controlled Market Research insights (traceable; never "AI thinks")
    market_research_context: Optional[Dict[str, Any]] = None
