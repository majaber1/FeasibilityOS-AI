"""Pricing signals — evidence-based only; never LLM-guessed prices."""

from __future__ import annotations

import re
from typing import Any

from ai_engine.research.market.schemas import EvidenceStatus, PricingSignal

_PRICE_PATTERN = re.compile(
    r"(?:SAR|SR|ر\.س|riyal[s]?)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
    r"|([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:SAR|SR|ر\.س)",
    re.I,
)


def extract_pricing_signals(
    evidence_items: list[dict[str, Any]],
) -> list[PricingSignal]:
    """Extract prices only from official/user-sourced evidence — never invent."""
    signals: list[PricingSignal] = []
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        text = str(
            item.get("statement") or item.get("content") or item.get("claim") or ""
        )
        source_url = item.get("source_url") or item.get("url")
        document_id = item.get("document_id")
        source_key = item.get("source_key")
        origin = str(item.get("origin") or "")
        source_type = str(item.get("source_type") or "")

        if source_type == "ai_assumption" or origin == "ai_assumption":
            continue
        if not source_url and not document_id:
            continue
        if not any(
            k in text.lower()
            for k in ("price", "pricing", "fee", "tariff", "sar", "riyal", "cost")
        ):
            continue

        for m in _PRICE_PATTERN.finditer(text):
            raw = m.group(1) or m.group(2)
            if not raw:
                continue
            numeric = float(raw.replace(",", ""))
            item_label = str(
                item.get("pricing_item")
                or item.get("title")
                or text[:80].split(":")[0].strip()
                or "priced_item"
            )
            signals.append(
                PricingSignal(
                    item=item_label[:120],
                    price=numeric,
                    currency="SAR",
                    unit=item.get("unit"),
                    source_url=str(source_url) if source_url else None,
                    evidence_reference=str(
                        document_id or source_url or item.get("chunk_id") or "sourced"
                    ),
                    status="VERIFIED",
                    source_key=str(source_key) if source_key else None,
                    confidence=0.75,
                    document_id=str(document_id) if document_id else None,
                    chunk_id=str(item["chunk_id"]) if item.get("chunk_id") else None,
                )
            )
    return signals


def research_pricing_signals(
    evidence_items: list[dict[str, Any]] | None = None,
) -> tuple[list[PricingSignal], EvidenceStatus]:
    items = list(evidence_items or [])
    signals = extract_pricing_signals(items)
    if signals:
        return signals, "VERIFIED"
    return (
        [
            PricingSignal(
                item="",
                price=None,
                currency=None,
                unit=None,
                source_url=None,
                evidence_reference="no_sourced_pricing_evidence",
                status="NOT_FOUND",
                confidence=0.0,
            )
        ],
        "NOT_FOUND",
    )
