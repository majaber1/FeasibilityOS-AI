from __future__ import annotations

from typing import Annotated, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from langgraph.graph import add_messages

StudyPhase = Literal[
    "DRAFT", "UNDERSTANDING", "NEEDS_INFORMATION",
    "EVIDENCE_REVIEW", "ASSUMPTIONS_REVIEW", "READY_FOR_ANALYSIS",
    "ANALYZED", "DECISION_READY", "FUNDING_READY"
]

ProjectArchetype = Literal[
    "saas_digital", "real_estate", "data_center",
    "retail", "industrial", "services", "franchise",
    "government_contract", "unknown"
]

DecisionVerdict = Literal[
    "GO", "GO_WITH_CONDITIONS", "NEED_MORE_VALIDATION", "DEFER", "NO_GO", "INSUFFICIENT_EVIDENCE"
]

QuestionType = Literal[
    "YES_NO",
    "SINGLE_SELECT",
    "MULTI_SELECT",
    "NUMBER",
    "CURRENCY",
    "PERCENTAGE",
    "DATE",
    "FILE_UPLOAD",
    "SHORT_TEXT",
    "LONG_TEXT",
]


class DiscoveryQuestion(BaseModel):
    id: str
    prompt: str
    question_type: QuestionType = "SHORT_TEXT"
    options: List[str] = Field(default_factory=list)
    required: bool = True
    unit: Optional[str] = None
    field_key: Optional[str] = None
    answer: Optional[str | list[str] | float | int | bool] = None
    answered: bool = False

# Evidence may only use source-backed types. AI estimates are NEVER Evidence.
EvidenceSourceType = Literal["official", "user_input", "document", "unverified"]

AssumptionOrigin = Literal[
    "user",
    "evidence_derived",
    "provisional_estimate",
    "platform_derived",
]

GateChoice = Literal["manual", "research", "provisional"]

EvidenceStatus = Literal[
    "not_started",
    "empty",
    "degraded",
    "available",
]


class ProjectProfile(BaseModel):
    archetype: ProjectArchetype = "unknown"
    sector: str = ""
    stage: str = ""
    decision_goal: str = ""
    language: Literal["ar", "en"] = "ar"
    missing_information: List[str] = []
    recommended_model: str = ""
    structured_answers: dict = Field(default_factory=dict)


class Assumption(BaseModel):
    key: str
    value: str
    source: str
    confidence: Literal["confirmed", "medium", "low"]
    low: Optional[str] = None
    base: Optional[str] = None
    high: Optional[str] = None
    origin: AssumptionOrigin = "user"
    status: Literal["draft", "approved", "rejected"] = "draft"
    rationale: Optional[str] = None
    critical: bool = False
    previous_values: List[dict] = Field(default_factory=list)


class Claim(BaseModel):
    """Source-backed Evidence item. NO SOURCE → NOT EVIDENCE."""

    statement: str
    source_type: EvidenceSourceType
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    confidence: float = 0.0
    source_title: Optional[str] = None
    status: Literal["draft", "approved", "rejected"] = "draft"

    @field_validator("source_type", mode="before")
    @classmethod
    def reject_ai_assumption_as_evidence(cls, value):
        if value == "ai_assumption":
            raise ValueError(
                "NO SOURCE → NOT EVIDENCE: ai_assumption cannot be stored as Evidence"
            )
        return value


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
    gate_choice: Optional[GateChoice] = None

    claims: List[Claim] = []
    evidence_approved: bool = False
    evidence_status: EvidenceStatus = "not_started"

    assumptions: List[Assumption] = []
    assumptions_approved: bool = False

    financial_snapshot_id: Optional[str] = None
    financial_results: Optional[dict] = None

    verdict: Optional[DecisionVerdict] = None
    decision_rationale: Optional[str] = None
    decision_conditions: List[str] = []
    decision_risks: List[str] = []
    decision_version: int = 0

    workflow_meta: dict = Field(default_factory=dict)
    discovery_questions: List[DiscoveryQuestion] = Field(default_factory=list)

    next_action: Optional[str] = None
    blocking_reason: Optional[str] = None
    error: Optional[str] = None


def is_source_backed_claim(claim: Claim | dict) -> bool:
    """Return True only for Evidence-eligible claims."""
    if isinstance(claim, dict):
        source_type = claim.get("source_type")
        statement = (claim.get("statement") or "").strip()
        source_url = claim.get("source_url")
        source_title = claim.get("source_title")
    else:
        source_type = claim.source_type
        statement = (claim.statement or "").strip()
        source_url = claim.source_url
        source_title = claim.source_title

    if not statement:
        return False
    if source_type in (None, "ai_assumption"):
        return False
    if source_type not in ("official", "user_input", "document", "unverified"):
        return False
    # user_input may omit URL; official/document should carry URL or title when available
    if source_type in ("official", "document") and not (source_url or source_title):
        return False
    return True


def filter_evidence_claims(claims: list) -> list[Claim]:
    """Drop non-Evidence items (including legacy ai_assumption)."""
    out: list[Claim] = []
    for raw in claims or []:
        data = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        if data.get("source_type") == "ai_assumption":
            continue
        if not is_source_backed_claim(data):
            continue
        try:
            out.append(Claim(**{k: v for k, v in data.items() if k in Claim.model_fields}))
        except Exception:
            continue
    return out


def compute_evidence_status(claims: list[Claim], *, provider_error: str | None = None) -> EvidenceStatus:
    if provider_error:
        return "degraded" if not claims else "available"
    if not claims:
        return "empty"
    return "available"


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"UNDERSTANDING", "NEEDS_INFORMATION", "EVIDENCE_REVIEW", "DRAFT"},
    "UNDERSTANDING": {"NEEDS_INFORMATION", "EVIDENCE_REVIEW", "UNDERSTANDING"},
    "NEEDS_INFORMATION": {
        "NEEDS_INFORMATION",
        "EVIDENCE_REVIEW",
        "ASSUMPTIONS_REVIEW",
    },
    "EVIDENCE_REVIEW": {"EVIDENCE_REVIEW", "ASSUMPTIONS_REVIEW", "NEEDS_INFORMATION"},
    "ASSUMPTIONS_REVIEW": {
        "ASSUMPTIONS_REVIEW",
        "READY_FOR_ANALYSIS",
        "EVIDENCE_REVIEW",
        "NEEDS_INFORMATION",
    },
    "READY_FOR_ANALYSIS": {"READY_FOR_ANALYSIS", "ANALYZED", "ASSUMPTIONS_REVIEW"},
    "ANALYZED": {"ANALYZED", "DECISION_READY"},
    "DECISION_READY": {"DECISION_READY", "FUNDING_READY", "ANALYZED"},
    "FUNDING_READY": {"FUNDING_READY", "DECISION_READY"},
}


def assert_legal_transition(current: str, nxt: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if nxt not in allowed:
        raise ValueError(f"Illegal phase transition: {current} → {nxt}")
