"""Simple overlapping chunker for knowledge text."""
from __future__ import annotations

from typing import Dict, List


def chunk_text(
    text: str,
    *,
    max_chars: int = 900,
    overlap: int = 120,
) -> List[Dict]:
    cleaned = "\n".join(line.strip() for line in (text or "").splitlines() if line.strip())
    if not cleaned:
        return []

    # Prefer paragraph boundaries
    paragraphs = [p.strip() for p in cleaned.split("\n") if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in paragraphs:
        if not buf:
            buf = p
        elif len(buf) + 1 + len(p) <= max_chars:
            buf = f"{buf}\n{p}"
        else:
            chunks.append(buf)
            # overlap tail
            tail = buf[-overlap:] if overlap and len(buf) > overlap else ""
            buf = f"{tail}\n{p}".strip() if tail else p
    if buf:
        chunks.append(buf)

    # Hard-split any oversized chunk
    final: List[Dict] = []
    idx = 0
    for c in chunks:
        if len(c) <= max_chars * 1.5:
            final.append({"index": idx, "content": c})
            idx += 1
            continue
        start = 0
        while start < len(c):
            piece = c[start : start + max_chars]
            final.append({"index": idx, "content": piece})
            idx += 1
            start += max(max_chars - overlap, 1)
    return final
