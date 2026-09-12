"""Regulation framework — placeholders only; no new connectors in Phase 8B."""

from __future__ import annotations

from typing import Any

from ai_engine.research.market.schemas import EvidenceStatus, RegulationSignal

REGULATION_PLACEHOLDERS: dict[str, dict[str, str]] = {
    "sama": {
        "authority": "Saudi Central Bank (SAMA)",
        "requirement": (
            "Financial / payment regulatory requirements may apply "
            "(connector not live in Phase 8B)."
        ),
        "sector_hint": "financial_services",
    },
    "zatca": {
        "authority": "ZATCA",
        "requirement": (
            "Tax / e-invoicing obligations may apply (connector not live in Phase 8B)."
        ),
        "sector_hint": "all",
    },
    "nca": {
        "authority": "National Cybersecurity Authority (NCA)",
        "requirement": (
            "Cybersecurity controls may apply for digital services "
            "(connector not live in Phase 8B)."
        ),
        "sector_hint": "digital",
    },
}


def build_regulation_framework(
    *,
    sector: str = "",
    include_placeholders: bool = True,
    evidence_items: list[dict[str, Any]] | None = None,
) -> tuple[list[RegulationSignal], EvidenceStatus]:
    """
    Return regulation framework signals.

    Phase 8B: placeholders + any already-sourced authority citations.
    Does not implement new connectors or unrestricted web fetch.
    """
    signals: list[RegulationSignal] = []
    sector_l = (sector or "").lower()

    for item in evidence_items or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("statement") or item.get("content") or "")
        source_url = item.get("source_url")
        if not source_url and not item.get("document_id"):
            continue
        lower = text.lower()
        for key, meta in REGULATION_PLACEHOLDERS.items():
            auth_token = meta["authority"].split("(")[0].strip().lower()
            if key in lower or auth_token in lower:
                signals.append(
                    RegulationSignal(
                        authority=meta["authority"],
                        requirement=text[:240],
                        sector=sector or meta["sector_hint"],
                        source_reference=str(
                            item.get("document_id") or source_url or "sourced"
                        ),
                        status="VERIFIED",
                        source_key=str(item.get("source_key") or key),
                        source_url=str(source_url) if source_url else None,
                        confidence=0.7,
                    )
                )

    if include_placeholders:
        for key, meta in REGULATION_PLACEHOLDERS.items():
            _ = sector_l
            if any(
                s.authority == meta["authority"] and s.status == "VERIFIED"
                for s in signals
            ):
                continue
            signals.append(
                RegulationSignal(
                    authority=meta["authority"],
                    requirement=meta["requirement"],
                    sector=sector or meta["sector_hint"],
                    source_reference=f"placeholder:{key}",
                    status="PARTIAL",
                    source_key=key,
                    source_url=None,
                    confidence=0.2,
                )
            )

    if signals:
        return signals, "PARTIAL"
    return signals, "NOT_FOUND"
