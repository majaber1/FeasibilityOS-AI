"""Saudi Source Connector contract + adapters into the Knowledge Layer."""

from .base import SourceConnector, ConnectorHealth, ConnectorStatus
from .schemas import (
    AuthorityType,
    Provenance,
    SourceDocument,
    SourceType,
    VerificationEligibility,
)
from .validation import validate_source_document, provenance_is_complete
from .fixture_connector import FixtureSaudiOpenDataConnector
from .gastat import GastatConnector
from .knowledge_adapter import ingest_source_document

__all__ = [
    "SourceConnector",
    "ConnectorHealth",
    "ConnectorStatus",
    "AuthorityType",
    "Provenance",
    "SourceDocument",
    "SourceType",
    "VerificationEligibility",
    "validate_source_document",
    "provenance_is_complete",
    "FixtureSaudiOpenDataConnector",
    "GastatConnector",
    "ingest_source_document",
]
