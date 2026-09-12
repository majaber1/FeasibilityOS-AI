"""MCP integration boundary for Phase 7A.

Proves that future MCP tools can invoke SourceConnector interfaces.
Does NOT create a second agent runtime or connect MCP to Financial/Risk/Decision.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.integrations.sources.base import SourceConnector
from app.integrations.sources.fixture_connector import FixtureSaudiOpenDataConnector
from app.integrations.sources.gastat import GastatConnector

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - dependency missing in some envs
    FastMCP = None  # type: ignore[misc, assignment]


SERVER_NAME = "saudi-business-sources"
MCP_AVAILABLE = FastMCP is not None


def default_fixture_connector() -> SourceConnector:
    return FixtureSaudiOpenDataConnector(enabled=True)


def connector_health_payload(connector: Optional[SourceConnector] = None) -> Dict[str, Any]:
    """Tool-facing health payload used by MCP and tests."""
    conn = connector or default_fixture_connector()
    health = conn.health()
    meta = conn.source_metadata
    return {
        "ok": health.status.value == "healthy",
        "connector_id": conn.connector_id,
        "status": health.status.value,
        "detail": health.detail,
        "checked_at": health.checked_at.isoformat(),
        "source_metadata": meta,
        "mcp_boundary": True,
    }



def connector_for_key(source_key: str) -> SourceConnector:
    """Resolve an approved SourceConnector by registry key. MCP → connector only."""
    key = (source_key or "").strip().lower()
    if key == "gastat":
        return GastatConnector(enabled=True)
    if key in {"saudi_open_data", "fixture"}:
        return FixtureSaudiOpenDataConnector(enabled=True)
    raise ValueError(f"unsupported source_key for MCP boundary: {source_key}")


def source_status_payload(source_key: str) -> Dict[str, Any]:
    """MCP tool: source_status(source_key) — connector health only."""
    conn = connector_for_key(source_key)
    health = conn.health()
    return {
        "ok": health.status.value == "healthy",
        "source_key": source_key,
        "connector_id": conn.connector_id,
        "status": health.status.value,
        "detail": health.detail,
        "checked_at": health.checked_at.isoformat(),
        "source_metadata": conn.source_metadata,
        "mcp_boundary": True,
        "allowed_side_effects": ["source_connector_read"],
        "forbidden": ["financial", "risk", "decision", "assumption_write"],
    }


def source_fetch_payload(source_key: str, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """MCP tool: source_fetch(source_key, request) — SourceConnector.retrieve only.

    Does not call Financial/Risk/Decision and does not write assumptions.
    """
    conn = connector_for_key(source_key)
    req = request or {}
    kwargs: Dict[str, Any] = {}
    if req.get("url"):
        kwargs["url"] = req["url"]
    if req.get("urls"):
        kwargs["urls"] = req["urls"]
    query = req.get("query")
    docs = conn.retrieve(query=query, **kwargs)
    return {
        "ok": True,
        "source_key": source_key,
        "connector_id": conn.connector_id,
        "count": len(docs),
        "documents": [
            {
                "source_id": d.source_id,
                "source_name": d.source_name,
                "title": d.title,
                "url": d.url,
                "canonical_url": d.canonical_url,
                "content_hash": d.content_hash,
                "retrieved_at": d.retrieved_at.isoformat() if d.retrieved_at else None,
                "published_at": d.published_at.isoformat() if d.published_at else None,
                "language": d.language,
                "sector": d.sector,
                "provenance": d.provenance.model_dump(mode="json"),
                "content_preview": (d.content or "")[:500],
            }
            for d in docs
        ],
        "mcp_boundary": True,
        "allowed_side_effects": ["source_connector_read"],
        "forbidden": ["financial", "risk", "decision", "assumption_write"],
    }



def build_mcp_server(*, connector: Optional[SourceConnector] = None) -> Any:
    """Build a FastMCP server exposing SourceConnector health/list tools only."""
    if FastMCP is None:
        raise RuntimeError("mcp package not installed — add modelcontextprotocol/python-sdk")

    conn = connector or default_fixture_connector()
    mcp = FastMCP(
        SERVER_NAME,
        instructions=(
            "Saudi Business Phase 7B source boundary. "
            "Tools call SourceConnector only — never Financial/Risk/Decision engines."
        ),
    )

    @mcp.tool(name="source_connector_health")
    def source_connector_health() -> Dict[str, Any]:
        """Return health of the bound SourceConnector (fixture in Phase 7A)."""
        return connector_health_payload(conn)

    @mcp.tool(name="source_connector_metadata")
    def source_connector_metadata() -> Dict[str, Any]:
        """Return static metadata for the bound SourceConnector."""
        return {
            "connector_id": conn.connector_id,
            "metadata": conn.source_metadata,
            "mcp_boundary": True,
        }

    @mcp.tool(name="source_status")
    def source_status(source_key: str) -> Dict[str, Any]:
        """Return health/status for an approved live or fixture source connector."""
        return source_status_payload(source_key)

    @mcp.tool(name="source_fetch")
    def source_fetch(source_key: str, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch/normalize official source documents via SourceConnector only."""
        return source_fetch_payload(source_key, request)


    return mcp


def list_bound_tool_names(server: Any) -> list[str]:
    """Sync helper for smoke tests — inspect registered tool names."""
    tools = getattr(server, "_tool_manager", None)
    if tools is None:
        return []
    # FastMCP ToolManager exposes list_tools / _tools depending on version
    if hasattr(tools, "list_tools"):
        listed = tools.list_tools()
        return sorted(t.name for t in listed)
    raw = getattr(tools, "_tools", {}) or {}
    return sorted(raw.keys())
