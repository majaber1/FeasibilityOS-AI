"""Fixture/mock connector — proves the contract without live Saudi APIs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import ConnectorHealth, ConnectorStatus, SourceConnector
from .schemas import (
    AuthorityType,
    Provenance,
    SourceDocument,
    SourceType,
    VerificationEligibility,
)
from .validation import compute_content_hash


class FixtureSaudiOpenDataConnector(SourceConnector):
    """Deterministic fixture representing a future Saudi Open Data connector."""

    CONNECTOR_ID = "fixture.saudi_open_data"

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    @property
    def connector_id(self) -> str:
        return self.CONNECTOR_ID

    @property
    def source_metadata(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "registry_key": "saudi_open_data",
            "name": "Saudi Open Data (Fixture)",
            "source_type": SourceType.OPEN_DATA.value,
            "authority_type": AuthorityType.OFFICIAL_PRIMARY.value,
            "base_url": "https://data.gov.sa",
            "country": "SA",
            "live": False,
        }

    def health(self) -> ConnectorHealth:
        if not self._enabled:
            return ConnectorHealth(
                status=ConnectorStatus.DISABLED,
                checked_at=datetime.now(timezone.utc),
                detail="fixture connector disabled",
            )
        return ConnectorHealth(
            status=ConnectorStatus.HEALTHY,
            checked_at=datetime.now(timezone.utc),
            detail="fixture connector ready",
            metadata={"live": False},
        )

    def fetch(self, *, query: Optional[str] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        if not self._enabled:
            return []
        retrieved = datetime.now(timezone.utc)
        body = (
            "Fixture Saudi Open Data extract for Phase 7A contract validation. "
            "SME count indicator (synthetic): 1,200,000 SMEs nationwide. "
            f"Query echo: {query or 'none'}."
        )
        return [
            {
                "id": "fixture-saudi-open-data-sme-001",
                "title": "Fixture — SME Landscape Indicator",
                "content": body,
                "url": "https://data.gov.sa/fixture/sme-landscape",
                "retrieved_at": retrieved.isoformat(),
                # published_at intentionally omitted — UNKNOWN, must stay null
            }
        ]

    def normalize(self, raw: Dict[str, Any]) -> SourceDocument:
        retrieved_raw = raw.get("retrieved_at")
        if isinstance(retrieved_raw, datetime):
            retrieved_at = retrieved_raw
        elif isinstance(retrieved_raw, str) and retrieved_raw.strip():
            retrieved_at = datetime.fromisoformat(retrieved_raw.replace("Z", "+00:00"))
        else:
            retrieved_at = datetime.now(timezone.utc)

        content = str(raw.get("content") or "").strip()
        url = raw.get("url")
        published_at = raw.get("published_at")  # never invent
        if isinstance(published_at, str) and published_at.strip():
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            published_at = None

        return SourceDocument(
            source_id=str(raw.get("id") or "fixture-unknown"),
            source_name="Saudi Open Data (Fixture)",
            source_type=SourceType.OPEN_DATA,
            authority_type=AuthorityType.OFFICIAL_PRIMARY,
            url=url,
            canonical_url=url,
            title=raw.get("title"),
            content=content,
            published_at=published_at,
            retrieved_at=retrieved_at,
            country="SA",
            language="en",
            languages=["en"],
            document_type="open_data_extract",
            content_type="text/plain",
            source_authority_score=0.9,
            source_quality_score=0.7,
            confidence=0.7,
            content_hash=compute_content_hash(content),
            provenance=Provenance(
                connector_id=self.connector_id,
                original_url=url,
                retrieval_method="fixture",
                retrieved_at=retrieved_at,
                registry_key="saudi_open_data",
            ),
            metadata={"fixture": True, "query_echo": True},
            verification_eligibility=VerificationEligibility.ELIGIBLE,
        )
