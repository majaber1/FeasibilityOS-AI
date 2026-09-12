"""SourceConnector abstract contract — no source-specific business logic."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .schemas import SourceDocument
from .validation import validate_source_document


class ConnectorStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNKNOWN = "UNKNOWN"


@dataclass
class ConnectorHealth:
    status: ConnectorStatus
    checked_at: datetime
    detail: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SourceConnector(ABC):
    """Canonical interface every Saudi source / MCP-backed tool must implement."""

    @property
    @abstractmethod
    def connector_id(self) -> str:
        ...

    @property
    @abstractmethod
    def source_metadata(self) -> Dict[str, Any]:
        """Static metadata: name, source_type, authority_type, registry_key, etc."""

    @abstractmethod
    def health(self) -> ConnectorHealth:
        ...

    @abstractmethod
    def fetch(self, *, query: Optional[str] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        """Retrieve raw payloads from the remote/fixture source."""

    @abstractmethod
    def normalize(self, raw: Dict[str, Any]) -> SourceDocument:
        """Map a raw payload into SourceDocument. Must not invent dates/URLs/authority."""

    def validate_provenance(self, document: SourceDocument) -> tuple[bool, List[str]]:
        return validate_source_document(document)

    def retrieve(self, *, query: Optional[str] = None, **kwargs: Any) -> List[SourceDocument]:
        """fetch → normalize → validate. Invalid docs are dropped (not silently verified)."""
        docs: List[SourceDocument] = []
        for raw in self.fetch(query=query, **kwargs):
            doc = self.normalize(raw)
            ok, _errors = self.validate_provenance(doc)
            if ok:
                docs.append(doc)
        return docs


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
