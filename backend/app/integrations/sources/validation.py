"""Validation rules for SourceDocument + provenance integrity."""
from __future__ import annotations

import hashlib
from typing import List, Tuple

from .schemas import (
    AuthorityType,
    Provenance,
    SourceDocument,
    SourceType,
    VerificationEligibility,
)


def compute_content_hash(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def provenance_is_complete(prov: Provenance | None) -> bool:
    if prov is None:
        return False
    if not (prov.connector_id or "").strip():
        return False
    if not (prov.retrieval_method or "").strip():
        return False
    if prov.retrieved_at is None:
        return False
    return True


def validate_source_document(doc: SourceDocument) -> Tuple[bool, List[str]]:
    """Return (ok, errors). Does not invent dates, authority, or URLs."""
    errors: List[str] = []

    if not (doc.source_id or "").strip():
        errors.append("source_id required")
    if not (doc.source_name or "").strip():
        errors.append("source_name required")
    if not (doc.content or "").strip():
        errors.append("content required")

    if not provenance_is_complete(doc.provenance):
        errors.append("provenance incomplete")

    # Never invent: if URL missing it must stay null — callers must not fabricate.
    if doc.url is not None and not str(doc.url).strip():
        errors.append("url must be null or non-empty")
    if doc.canonical_url is not None and not str(doc.canonical_url).strip():
        errors.append("canonical_url must be null or non-empty")

    if doc.published_at is not None and doc.retrieved_at is not None:
        # Allow published_at after retrieved_at only as warning elsewhere; not an error.
        pass

    if doc.content_hash:
        expected = compute_content_hash(doc.content)
        if doc.content_hash != expected:
            errors.append("content_hash mismatch")

    # AI inference / missing provenance can never be verification-eligible.
    if doc.authority_type == AuthorityType.AI_INFERENCE:
        if doc.verification_eligibility == VerificationEligibility.ELIGIBLE:
            errors.append("AI_INFERENCE cannot be verification-eligible")

    if not provenance_is_complete(doc.provenance):
        if doc.verification_eligibility == VerificationEligibility.ELIGIBLE:
            errors.append("incomplete provenance cannot be verification-eligible")

    if doc.source_type == SourceType.UNKNOWN and doc.authority_type == AuthorityType.OFFICIAL_PRIMARY:
        errors.append("UNKNOWN source_type cannot claim OFFICIAL_PRIMARY authority")

    return (len(errors) == 0, errors)


def verification_status_for(doc: SourceDocument) -> str:
    """Map to evidence verification vocabulary.

    External claims without complete provenance cannot become verified.
    """
    ok, _ = validate_source_document(doc)
    if not ok or not provenance_is_complete(doc.provenance):
        return "unverified"
    if doc.authority_type in {
        AuthorityType.AI_INFERENCE,
        AuthorityType.UNKNOWN,
        AuthorityType.UNVERIFIED,
    }:
        return "unverified"
    if doc.verification_eligibility != VerificationEligibility.ELIGIBLE:
        return "unverified"
    # Phase 7A never auto-marks VERIFIED_EXTERNAL_FACT — eligibility only.
    return "user_provided"
