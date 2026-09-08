"""
Collateral domain rules (Phase 16): validation and a deterministic summary.

Never converts a reported/verified value into an assumed lendable amount --
market value is not lendable value, and no lender haircut is applied here.
This module only stores, validates, and totals what was actually entered;
Phase 17 (Funding Readiness) and later phases decide what to do with it.

validate_consistency operates on a full record dict (not a partial patch)
so the same rule applies identically whether a record is being created or
updated -- the caller is responsible for merging a PATCH onto the existing
row before calling this.
"""
from __future__ import annotations

COLLATERAL_TYPES = ("PROPERTY", "EQUIPMENT", "CASH", "RECEIVABLES", "GUARANTEE", "OTHER")
VERIFICATION_STATUSES = ("UNVERIFIED", "USER_REPORTED", "DOCUMENT_SUPPORTED", "VERIFIED")
ENCUMBRANCE_STATUSES = ("UNENCUMBERED", "PARTIALLY_ENCUMBERED", "FULLY_ENCUMBERED", "UNKNOWN")
ENCUMBRANCE_STATUSES_REQUIRING_AMOUNT = ("PARTIALLY_ENCUMBERED", "FULLY_ENCUMBERED")
VERIFICATION_STATUSES_ALLOWING_VERIFIED_VALUE = ("DOCUMENT_SUPPORTED", "VERIFIED")


def validate_consistency(data: dict) -> None:
    """Raises ValueError with a human-readable message on the first violation found."""
    if data["collateral_type"] not in COLLATERAL_TYPES:
        raise ValueError(f"collateral_type must be one of {COLLATERAL_TYPES}")

    if data["reported_value"] < 0:
        raise ValueError("reported_value must be >= 0")

    verified_value = data.get("verified_value")
    if verified_value is not None and verified_value < 0:
        raise ValueError("verified_value must be >= 0")

    verification_status = data["verification_status"]
    if verification_status not in VERIFICATION_STATUSES:
        raise ValueError(f"verification_status must be one of {VERIFICATION_STATUSES}")
    if verified_value is not None and verification_status not in VERIFICATION_STATUSES_ALLOWING_VERIFIED_VALUE:
        raise ValueError(
            "verified_value can only be set when verification_status is DOCUMENT_SUPPORTED or VERIFIED "
            "-- typing a value never itself verifies it"
        )

    encumbrance_status = data["encumbrance_status"]
    if encumbrance_status not in ENCUMBRANCE_STATUSES:
        raise ValueError(f"encumbrance_status must be one of {ENCUMBRANCE_STATUSES}")

    encumbrance_amount = data.get("encumbrance_amount")
    if encumbrance_amount is not None and encumbrance_amount < 0:
        raise ValueError("encumbrance_amount must be >= 0")

    if encumbrance_status in ENCUMBRANCE_STATUSES_REQUIRING_AMOUNT:
        if encumbrance_amount is None:
            raise ValueError(f"encumbrance_amount is required when encumbrance_status is {encumbrance_status}")
    elif encumbrance_amount is not None:
        raise ValueError("encumbrance_amount must be empty unless encumbrance_status is PARTIALLY_ENCUMBERED or FULLY_ENCUMBERED")

    if encumbrance_amount is not None:
        ceiling = data["reported_value"]
        if verified_value is not None:
            ceiling = max(ceiling, verified_value)
        if encumbrance_amount > ceiling:
            raise ValueError("encumbrance_amount cannot exceed the collateral's reported/verified value")


def summarize_collateral(records: list[dict]) -> dict:
    """records: dicts with reported_value/verified_value/verification_status/
    encumbrance_status/encumbrance_amount keys (matching CollateralItem)."""
    total_reported = sum(r["reported_value"] for r in records)
    total_verified = sum(
        r["verified_value"]
        for r in records
        if r["verification_status"] == "VERIFIED" and r.get("verified_value") is not None
    )
    total_encumbered = sum(
        r["encumbrance_amount"]
        for r in records
        if r["encumbrance_status"] in ENCUMBRANCE_STATUSES_REQUIRING_AMOUNT and r.get("encumbrance_amount") is not None
    )

    return {
        "record_count": len(records),
        "total_reported_value": total_reported,
        "total_verified_value": total_verified,
        "total_encumbered_value": total_encumbered,
        "total_unencumbered_reported_value": total_reported - total_encumbered,
        "verified_record_count": sum(1 for r in records if r["verification_status"] == "VERIFIED"),
        "unverified_record_count": sum(1 for r in records if r["verification_status"] == "UNVERIFIED"),
        "unknown_encumbrance_count": sum(1 for r in records if r["encumbrance_status"] == "UNKNOWN"),
    }
