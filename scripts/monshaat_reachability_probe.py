#!/usr/bin/env python3
"""Independent Monsha'at official Open Data API reachability probe.

Exercises DNS → TCP:443 → TLS → HTTP GET against the documented EnterprisesStatistics
API. Does not use mirrors, caches, proxies, or browser scraping services.
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx

HOST = "pservices.monshaat.gov.sa"
API_URLS = [
    (
        "https://pservices.monshaat.gov.sa/BI/TaskService/OpenData/"
        "EnterprisesStatistics/2023/4?paginationIndex=1&recordsPerPage=5"
    ),
    (
        "https://pservices.monshaat.gov.sa/BI/TaskService/OpenData/"
        "EnterprisesStatistics/2024/1?paginationIndex=1&recordsPerPage=5"
    ),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe_dns(host: str) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addrs = sorted({i[4][0] for i in infos})
        return {
            "status": "PASS",
            "addresses": addrs,
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }


def probe_tcp(host: str, timeout: float = 10.0) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            peer = sock.getpeername()
        return {
            "status": "PASS",
            "peer": list(peer),
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }


def probe_tls(host: str, timeout: float = 15.0) -> Dict[str, Any]:
    t0 = time.monotonic()
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                return {
                    "status": "PASS",
                    "version": ssock.version(),
                    "cipher": list(ssock.cipher()) if ssock.cipher() else None,
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }


def probe_http(url: str, timeout: float = 20.0) -> Dict[str, Any]:
    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            resp = client.get(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": (
                        "SaudiBusinessBot/7C1-reachability-gate "
                        "(+https://github.com/majaber1/saudi-business; "
                        "diagnostic only)"
                    ),
                },
            )
            ctype = (resp.headers.get("content-type") or "").split(";", 1)[0].strip()
            body_preview = resp.text[:500] if resp.text else ""
            return {
                "status": "PASS" if resp.status_code < 400 else "FAIL",
                "http_status": resp.status_code,
                "content_type": ctype or None,
                "bytes": len(resp.content),
                "body_preview": body_preview,
                "final_url": str(resp.url),
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
                "error": None
                if resp.status_code < 400
                else f"HTTP {resp.status_code}",
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAIL",
            "http_status": None,
            "content_type": None,
            "bytes": 0,
            "body_preview": None,
            "final_url": url,
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--environment",
        required=True,
        help="Human-readable second-environment name",
    )
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    dns = probe_dns(HOST)
    tcp = probe_tcp(HOST)
    tls = probe_tls(HOST)
    http_results: List[Dict[str, Any]] = []
    for url in API_URLS:
        result = probe_http(url)
        result["url"] = url
        result["host"] = urlparse(url).hostname
        http_results.append(result)

    http_pass = any(r["status"] == "PASS" for r in http_results)
    summary = {
        "environment": args.environment,
        "host": HOST,
        "dns": dns["status"],
        "tcp_443": tcp["status"],
        "tls": tls["status"],
        "http": "PASS" if http_pass else "FAIL",
        "any_official_api_success": http_pass,
    }

    payload = {
        "captured_at": _now(),
        "environment": args.environment,
        "host": HOST,
        "summary": summary,
        "dns": dns,
        "tcp_443": tcp,
        "tls": tls,
        "http": http_results,
        "policy": {
            "no_mirrors": True,
            "no_search_cache": True,
            "no_third_party_proxy": True,
            "official_host_only": HOST,
        },
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
