"""Dependency-free request metrics and structured access logging."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import Counter

# Reuse Uvicorn's configured logger so JSON events are emitted in
# containers without requiring a second logging configuration.
logger = logging.getLogger("uvicorn")
_lock = threading.Lock()
_requests = Counter()
_latency_ms = Counter()


async def observe_request(request, call_next):
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        route = request.url.path
        bucket = f"{request.method} {route} {status_code}"
        with _lock:
            _requests[bucket] += 1
            _latency_ms[bucket] += int(elapsed)
        if "response" in locals():
            response.headers["X-Request-ID"] = request_id
        logger.info(json.dumps({
            "event": "http_request", "request_id": request_id,
            "method": request.method, "path": route,
            "status": status_code, "duration_ms": elapsed,
        }, separators=(",", ":")))


def metrics_snapshot() -> dict:
    with _lock:
        rows = []
        for key, count in _requests.items():
            rows.append({
                "request": key,
                "count": count,
                "average_duration_ms": round(_latency_ms[key] / count, 2) if count else 0,
            })
        return {"requests": rows}
