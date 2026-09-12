"""Research service — Knowledge-first, then MCP/connector live fetch."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from ai_engine.research.planner import build_research_plan
from ai_engine.research.schemas import ResearchClaim, ResearchPlan, ResearchResult

logger = logging.getLogger(__name__)


def _trace(name: str, metadata: dict[str, Any] | None = None) -> None:
    """Best-effort Langfuse observation; never raises."""
    try:
        from ai_engine.config import get_langfuse

        lf = get_langfuse()
        if lf is None:
            return
        if hasattr(lf, "start_as_current_span"):
            with lf.start_as_current_span(name=name, metadata=metadata or {}):
                pass
        elif hasattr(lf, "trace"):
            lf.trace(name=name, metadata=metadata or {})
    except Exception as exc:  # noqa: BLE001
        logger.debug("langfuse research trace skipped: %s", exc)


def _knowledge_retrieve(
    *,
    owner_id: int | None,
    query: str,
    source_key: str,
    db: Any | None,
    study_id: str | None = None,
) -> list[ResearchClaim]:
    if owner_id is None or db is None:
        return []
    try:
        from backend.app.services.knowledge_service import retrieve_evidence
    except ImportError:
        try:
            from app.services.knowledge_service import retrieve_evidence  # type: ignore
        except ImportError:
            return []

    try:
        pack = retrieve_evidence(
            db,
            owner_id=int(owner_id),
            query=query,
            study_id=study_id,
            top_k=6,
            query_profile={"source_key": source_key},
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("knowledge retrieve skipped: %s", exc)
        return []

    claims: list[ResearchClaim] = []
    for cite in (pack or {}).get("citations") or []:
        if not isinstance(cite, dict):
            continue
        statement = str(
            cite.get("claim") or cite.get("content") or cite.get("snippet") or ""
        ).strip()
        if not statement:
            continue
        source = str(cite.get("source") or "")
        conf = float(cite.get("confidence") or 0.7)
        claims.append(
            ResearchClaim(
                statement=statement[:500],
                source_type=(
                    "official"
                    if "external" in source or source_key in statement.lower()
                    else "document"
                ),
                source_url=cite.get("source_url") or cite.get("url"),
                confidence=min(0.9, max(0.5, conf)),
                source_key=source_key,
                from_knowledge=True,
                document_id=(
                    str(cite.get("document_id")) if cite.get("document_id") else None
                ),
                chunk_id=str(cite.get("chunk_id")) if cite.get("chunk_id") else None,
                origin="knowledge",
            )
        )
    if not claims:
        for hit in (pack or {}).get("hits") or []:
            if not isinstance(hit, dict):
                continue
            content = str(hit.get("content") or "").strip()
            if not content:
                continue
            claims.append(
                ResearchClaim(
                    statement=content[:500],
                    source_type="document",
                    confidence=float(hit.get("score") or 0.6),
                    source_key=source_key,
                    from_knowledge=True,
                    document_id=(
                        str(hit.get("document_id")) if hit.get("document_id") else None
                    ),
                    chunk_id=str(hit.get("chunk_id")) if hit.get("chunk_id") else None,
                    origin="knowledge",
                )
            )
    return claims


def _claims_from_mcp_documents(
    source_key: str, documents: list[dict[str, Any]]
) -> list[ResearchClaim]:
    retrieved = datetime.now(timezone.utc).date().isoformat()
    claims: list[ResearchClaim] = []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        title = str(doc.get("title") or doc.get("source_name") or source_key).strip()
        preview = str(doc.get("content_preview") or "").strip()
        url = doc.get("canonical_url") or doc.get("url")
        statement = f"{title}: {preview}" if preview else title
        if not statement:
            continue
        claims.append(
            ResearchClaim(
                statement=statement[:500],
                source_type="official",
                source_url=url,
                retrieved_date=retrieved,
                confidence=0.85,
                metric_key=title,
                source_key=source_key,
                document_id=str(doc.get("source_id") or doc.get("id") or "") or None,
                origin="research",
            )
        )
    return claims


def _live_fetch(
    source_key: str, query: str | None = None
) -> tuple[list[ResearchClaim], dict[str, Any], list[Any]]:
    """Fetch via MCP boundary. Returns claims, attempt metadata, typed docs for ingest."""
    try:
        from backend.app.integrations.mcp.boundary import (
            connector_for_key,
            source_fetch_payload,
            source_status_payload,
        )
    except ImportError:
        from app.integrations.mcp.boundary import (  # type: ignore
            connector_for_key,
            source_fetch_payload,
            source_status_payload,
        )

    attempt: dict[str, Any] = {
        "source_key": source_key,
        "at": datetime.now(timezone.utc).isoformat(),
        "path": "mcp_live",
    }
    status = source_status_payload(source_key)
    attempt["status"] = {
        "ok": status.get("ok"),
        "health": status.get("status"),
        "detail": status.get("detail"),
        "connector_id": status.get("connector_id"),
    }
    health = str(status.get("status") or "").lower()
    if health in {"unavailable", "disabled", "unknown"}:
        attempt["outcome"] = "unavailable"
        return [], attempt, []

    raw = source_fetch_payload(source_key, {"query": query} if query else {})
    attempt["fetch_ok"] = bool(raw.get("ok"))
    if not raw.get("ok"):
        attempt["outcome"] = "fetch_failed"
        attempt["error"] = raw.get("error") or raw.get("detail")
        return [], attempt, []

    documents = raw.get("documents") or []
    claims = _claims_from_mcp_documents(
        source_key, documents if isinstance(documents, list) else []
    )
    attempt["outcome"] = "ok" if claims else "empty"
    attempt["claim_count"] = len(claims)
    attempt["document_count"] = len(documents) if isinstance(documents, list) else 0

    typed_docs: list[Any] = []
    try:
        conn = connector_for_key(source_key)
        typed_docs = list(conn.retrieve(query=query) or [])
    except Exception as exc:  # noqa: BLE001
        logger.info("typed retrieve for ingest skipped: %s", exc)

    return claims, attempt, typed_docs


def _maybe_ingest(
    *,
    db: Any | None,
    owner_id: int | None,
    typed_docs: list[Any],
) -> int:
    if not db or owner_id is None or not typed_docs:
        return 0
    try:
        from backend.app.integrations.sources.knowledge_adapter import (
            ingest_source_document,
        )
    except ImportError:
        try:
            from app.integrations.sources.knowledge_adapter import (  # type: ignore
                ingest_source_document,
            )
        except ImportError:
            return 0

    ingested = 0
    for doc in typed_docs:
        try:
            ingest_source_document(db, owner_id=int(owner_id), document=doc)
            ingested += 1
        except Exception as exc:  # noqa: BLE001
            logger.info("knowledge ingest skipped: %s", exc)
    return ingested


def claims_from_knowledge_context(
    knowledge_context: dict[str, Any] | None,
) -> list[ResearchClaim]:
    """Lift existing Evidence Pack citations into research claims."""
    if not knowledge_context:
        return []
    claims: list[ResearchClaim] = []
    for cite in knowledge_context.get("citations") or []:
        if not isinstance(cite, dict):
            continue
        statement = str(cite.get("claim") or cite.get("content") or "").strip()
        if not statement:
            continue
        claims.append(
            ResearchClaim(
                statement=statement[:500],
                source_type="document",
                source_url=cite.get("source_url"),
                confidence=float(cite.get("confidence") or 0.65),
                from_knowledge=True,
                source_key="knowledge_context",
            )
        )
    return claims


def execute_research(
    plan: ResearchPlan,
    *,
    owner_id: int | None = None,
    db: Any | None = None,
    knowledge_context: dict[str, Any] | None = None,
) -> ResearchResult:
    """
    Knowledge-first research execution.

    Order per source: Knowledge retrieve → if thin, MCP live fetch → ingest.
    Blocked sources are recorded but never fail the study.
    """
    _trace(
        "phase8a_research_execute",
        {"study_id": plan.study_id, "sources": [s.source_key for s in plan.sources]},
    )

    claims: list[ResearchClaim] = []
    attempts: list[dict[str, Any]] = []
    blocked: list[str] = []
    unavailable: list[str] = []
    errors: list[str] = []
    knowledge_hits = 0
    live_fetches = 0

    seed = claims_from_knowledge_context(knowledge_context)
    if seed:
        knowledge_hits += len(seed)
        claims.extend(seed)
        attempts.append(
            {
                "source_key": "knowledge_context",
                "outcome": "knowledge_context_seed",
                "claim_count": len(seed),
                "path": "knowledge",
            }
        )

    query = " | ".join(plan.queries) if plan.queries else "Saudi Arabia official statistics"

    for src in plan.sources:
        if src.blocked:
            blocked.append(src.source_key)
            attempts.append(
                {
                    "source_key": src.source_key,
                    "outcome": "blocked",
                    "reason": src.block_reason,
                    "path": "skipped",
                }
            )
            continue

        k_claims = _knowledge_retrieve(
            owner_id=owner_id,
            query=f"{query} {src.source_key}",
            source_key=src.source_key,
            db=db,
            study_id=plan.study_id,
        )
        if k_claims:
            knowledge_hits += len(k_claims)
            claims.extend(k_claims)
            attempts.append(
                {
                    "source_key": src.source_key,
                    "outcome": "knowledge_hit",
                    "claim_count": len(k_claims),
                    "path": "knowledge",
                }
            )
            continue

        try:
            live_claims, attempt, typed_docs = _live_fetch(src.source_key, query=query)
            attempts.append(attempt)
            if attempt.get("outcome") in {"unavailable", "fetch_failed"}:
                unavailable.append(src.source_key)
                if attempt.get("error"):
                    errors.append(f"{src.source_key}: {attempt['error']}")
            elif live_claims:
                live_fetches += 1
                claims.extend(live_claims)
                _maybe_ingest(db=db, owner_id=owner_id, typed_docs=typed_docs)
            elif attempt.get("outcome") == "empty":
                unavailable.append(src.source_key)
        except Exception as exc:  # noqa: BLE001
            unavailable.append(src.source_key)
            errors.append(f"{src.source_key}: {exc}")
            attempts.append(
                {
                    "source_key": src.source_key,
                    "outcome": "error",
                    "error": str(exc),
                    "path": "mcp_live",
                }
            )

    live_sources = [s for s in plan.sources if not s.blocked]
    if claims:
        status: str = "partial" if unavailable else "complete"
    elif blocked and not live_sources:
        status = "blocked"
    elif unavailable and not claims:
        status = "failed"
    else:
        status = "partial" if attempts else "failed"

    # Phase 8B — Controlled Market Research over collected official/document evidence.
    # Never invents competitors/prices; never opens arbitrary URLs.
    market_payload: dict[str, Any] | None = None
    try:
        from ai_engine.research.market.service import (
            evidence_items_from_research_claims,
            execute_market_research,
            market_result_to_research_claims,
        )

        market = execute_market_research(
            study_id=plan.study_id,
            business_idea=" | ".join(plan.gaps[:3]) if plan.gaps else "",
            sector="",
            geography="Saudi Arabia",
            gaps=list(plan.gaps),
            evidence_items=evidence_items_from_research_claims(claims),
            use_cache=True,
        )
        market_payload = market.to_public_dict()
        market_claims = market_result_to_research_claims(market)
        if market_claims:
            claims.extend(market_claims)
        attempts.append(
            {
                "source_key": "market_research",
                "outcome": str(market.status),
                "claim_count": len(market_claims),
                "path": "market_8b",
                "duration_ms": market.duration_ms,
                "cache_hits": market.cache_hits,
                "conflicts": len(market.conflicts),
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("market research skipped: %s", exc)
        errors.append(f"market_research: {exc}")
        attempts.append(
            {
                "source_key": "market_research",
                "outcome": "error",
                "error": str(exc),
                "path": "market_8b",
            }
        )

    result = ResearchResult(
        plan=plan,
        status=status,  # type: ignore[arg-type]
        claims=claims,
        knowledge_hits=knowledge_hits,
        live_fetches=live_fetches,
        blocked_sources=blocked,
        unavailable_sources=unavailable,
        errors=errors,
        attempts=attempts,
        market_research=market_payload,
    )
    _trace(
        "phase8a_research_result",
        {
            "study_id": plan.study_id,
            "status": result.status,
            "claim_count": len(claims),
            "blocked": blocked,
            "unavailable": unavailable,
            "market_status": (market_payload or {}).get("status"),
        },
    )
    return result


def research_gaps(
    *,
    study_id: str,
    gaps: list[str],
    owner_id: int | None = None,
    db: Any | None = None,
    queries: list[str] | None = None,
    knowledge_context: dict[str, Any] | None = None,
) -> ResearchResult:
    plan = build_research_plan(study_id=study_id, gaps=gaps, queries=queries)
    return execute_research(
        plan,
        owner_id=owner_id,
        db=db,
        knowledge_context=knowledge_context,
    )


def content_hash_for_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
