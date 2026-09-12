"""Bounded in-process page cache (Phase 7B). No Redis."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class CacheEntry:
    url: str
    content_hash: str
    retrieved_at: datetime
    status_code: int
    content_type: str
    final_url: str
    title: Optional[str]
    text: str
    html: str
    published_at_raw: Optional[str]
    expires_at_monotonic: float


class BoundedTTLCache:
    """Simple TTL cache keyed by canonical URL. Evicts oldest on overflow."""

    def __init__(self, *, max_entries: int = 128, ttl_seconds: int = 3600) -> None:
        self.max_entries = max(1, max_entries)
        self.ttl_seconds = max(1, ttl_seconds)
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[CacheEntry]:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.expires_at_monotonic <= now:
                self._store.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return entry

    def set(self, key: str, entry: CacheEntry) -> None:
        with self._lock:
            if key not in self._store and len(self._store) >= self.max_entries:
                oldest_key = min(
                    self._store.keys(),
                    key=lambda k: self._store[k].retrieved_at.timestamp(),
                )
                self._store.pop(oldest_key, None)
            self._store[key] = entry

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self.hits,
                "misses": self.misses,
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
            }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
