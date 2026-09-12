"""Canonical SourceDocument + provenance contracts for Phase 7A.

Every external source (API, MCP tool, browser research, upload, future
connector) must normalize into SourceDocument before Knowledge Layer ingest.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    OFFICIAL_STATISTIC = "official_statistic"
    REGULATION = "regulation"
    OPEN_DATA = "open_data"
    FUNDING_PROGRAM = "funding_program"
    MARKET_REPORT = "market_report"
    NEWS = "news"
    USER_DOCUMENT = "user_document"
    WEB_PAGE = "web_page"
    API_PAYLOAD = "api_payload"
    FIXTURE = "fixture"
    OTHER = "other"
    UNKNOWN = "UNKNOWN"


class AuthorityType(str, Enum):
    OFFICIAL_PRIMARY = "OFFICIAL_PRIMARY"
    OFFICIAL_SECONDARY = "OFFICIAL_SECONDARY"
    REGULATOR = "REGULATOR"
    REPUTABLE_INSTITUTION = "REPUTABLE_INSTITUTION"
    COMMERCIAL_SOURCE = "COMMERCIAL_SOURCE"
    USER_DOCUMENT = "USER_DOCUMENT"
    AI_INFERENCE = "AI_INFERENCE"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"


class VerificationEligibility(str, Enum):
    """Whether a document may ever become VERIFIED_EXTERNAL_FACT."""

    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNKNOWN = "UNKNOWN"


class Provenance(BaseModel):
    connector_id: str = Field(..., min_length=1)
    original_url: Optional[str] = None
    retrieval_method: str = Field(..., min_length=1)
    retrieved_at: datetime
    registry_key: Optional[str] = None
    raw_payload_ref: Optional[str] = None

    @field_validator("connector_id", "retrieval_method")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("required provenance field is empty")
        return v


class SourceDocument(BaseModel):
    """Normalized contract for every external source payload."""

    source_id: str = Field(..., min_length=1)
    source_name: str = Field(..., min_length=1)
    source_type: SourceType = SourceType.UNKNOWN
    authority_type: AuthorityType = AuthorityType.UNKNOWN

    url: Optional[str] = None
    canonical_url: Optional[str] = None

    title: Optional[str] = None
    content: str = Field(..., min_length=1)

    published_at: Optional[datetime] = None
    retrieved_at: datetime
    effective_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    country: Optional[str] = "SA"
    geography: Optional[str] = None
    sector: Optional[str] = None
    language: Optional[str] = None
    sectors: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)

    document_type: Optional[str] = None
    content_type: Optional[str] = "text/plain"

    source_authority_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    content_hash: Optional[str] = None

    provenance: Provenance
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_payload_ref: Optional[str] = None

    verification_eligibility: VerificationEligibility = VerificationEligibility.UNKNOWN

    model_config = {"extra": "forbid"}

    @field_validator("source_id", "source_name", "content")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("field must be non-empty")
        return v
