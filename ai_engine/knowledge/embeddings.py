"""Deterministic local embeddings for MVP (no external embedding API).

Upgrade path: swap embed_text() for a provider embedding while keeping the
same float[] storage and cosine retrieval.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import List

EMBED_DIM = 256
_TOKEN_RE = re.compile(r"[a-zA-Z0-9\u0600-\u06FF]+")


def _ngrams(token: str) -> List[str]:
    t = token.lower()
    if len(t) < 3:
        return [t]
    return [t[i : i + 3] for i in range(len(t) - 2)]


def embed_text(text: str, dim: int = EMBED_DIM) -> List[float]:
    vec = [0.0] * dim
    if not text or not str(text).strip():
        return vec
    tokens = _TOKEN_RE.findall(str(text).lower())
    if not tokens:
        return vec
    for tok in tokens:
        for gram in _ngrams(tok):
            h = hashlib.sha256(gram.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % dim
            sign = 1.0 if h[4] % 2 == 0 else -1.0
            weight = 1.0 + (h[5] / 255.0)
            vec[idx] += sign * weight
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return float(sum(a[i] * b[i] for i in range(n)))
