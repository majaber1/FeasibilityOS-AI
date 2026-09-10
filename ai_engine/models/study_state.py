from __future__ import annotations

from typing import Annotated, List, Optional, Literal
from pydantic import BaseModel
from langgraph.graph import add_messages

StudyPhase = Literal[
    "DRAFT", "UNDERSTANDING", "NEEDS_INFORMATION",
    "EVIDENCE_REVIEW", "ASSUMPTIONS_REVIEW", "READY_FOR_ANALYSIS",
    "ANALYZED", "DECISION_READY", "FUNDING_READY", "REPORT_READY",
]

ProjectArchetype = Literal[
    "saas_digital", "real_estate", "data_center",
    "retail", "industrial", "services", "franchise", "unknown"
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


class Assumption(BaseModel):
    key: str
    value: str
    source: str
    confidence: Literal["confirmed", "medium", "low"]
    low: Optional[str] = None
    base: Optional[str] = None
    high: Optional[str] = None


class Claim(BaseModel):
    statement: str
    source_type: Literal["official", "user_input", "document", "ai_assumption", "unverified"]
    source_url: Optional[str] = None
    retrieved_date: Optional[str] = None
    confidence: float = 0.0


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
    # Snapshots of prior assumption sets so NPV changes can be explained.
    assumptions_history: List[dict] = []

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
