"""HTML → clean text extraction for governed source ingest (no summarization)."""
from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import List, Optional, Tuple


_STRIP_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "svg",
        "iframe",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        "button",
    }
)
_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "main",
        "li",
        "ul",
        "ol",
        "table",
        "tr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "br",
        "hr",
    }
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: List[str] = []
        self._skip_depth = 0
        self._prefer_depth = 0
        self.title_parts: List[str] = []
        self._in_title = False
        self._capture_preferred = False
        self._preferred: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        if tag in _STRIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        role = attr.get("role", "").lower()
        cls = f"{attr.get('class', '')} {attr.get('id', '')}".lower()
        if tag in {"article", "main"} or role == "main" or any(
            h in cls for h in ("article", "content-body", "news-body", "portlet-body")
        ):
            self._prefer_depth += 1
            self._capture_preferred = True
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")
            if self._capture_preferred:
                self._preferred.append("\n")
        if tag == "br":
            self._chunks.append("\n")
            if self._capture_preferred:
                self._preferred.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in _STRIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {"article", "main"} and self._prefer_depth:
            self._prefer_depth -= 1
            if self._prefer_depth == 0:
                self._capture_preferred = False
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")
            if self._prefer_depth or self._capture_preferred:
                self._preferred.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        self._chunks.append(text + " ")
        if self._prefer_depth > 0 or self._capture_preferred:
            self._preferred.append(text + " ")

    def text(self) -> str:
        preferred = "".join(self._preferred)
        raw = preferred if preferred.strip() else "".join(self._chunks)
        return normalize_whitespace(raw)

    def title(self) -> Optional[str]:
        t = normalize_whitespace("".join(self.title_parts))
        return t or None


def normalize_whitespace(text: str) -> str:
    text = unescape(text or "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    cleaned = []
    for ln in lines:
        low = ln.lower()
        if any(
            p in low
            for p in (
                "cookie",
                "accept all",
                "privacy policy",
                "subscribe to our newsletter",
                "all rights reserved",
            )
        ):
            continue
        cleaned.append(ln)
    return "\n".join(cleaned).strip()


_DATE_PATTERNS = [
    re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b"),
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
    re.compile(
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{4})\b",
        re.I,
    ),
]


def extract_published_date_raw(html: str, text: str) -> Optional[str]:
    """Return a date string only when explicitly present — never invent."""
    meta = re.search(
        r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|publish(?:ed)?[_-]?date|date)'
        r'["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    )
    if not meta:
        meta = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']'
            r'(?:article:published_time|publish(?:ed)?[_-]?date|date)["\']',
            html,
            flags=re.I,
        )
    if meta:
        return meta.group(1).strip()

    card = re.search(
        r'class=["\'][^"\']*card-date[^"\']*["\'][^>]*>\s*([^<]+)<',
        html,
        flags=re.I,
    )
    if card:
        return normalize_whitespace(card.group(1))

    time_tag = re.search(
        r"""<time[^>]+datetime=["']([^"']+)["']""",
        html,
        flags=re.I,
    )
    if time_tag:
        return time_tag.group(1).strip()

    for pat in _DATE_PATTERNS:
        m = pat.search(text or "")
        if m:
            return m.group(0)
    return None


def clean_html(html: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Return (clean_text, title, published_at_raw). Does not summarize."""
    parser = _TextExtractor()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        text = normalize_whitespace(re.sub(r"<[^>]+>", " ", html or ""))
        return text, None, extract_published_date_raw(html or "", text)

    text = parser.text()
    title = parser.title()
    published_raw = extract_published_date_raw(html or "", text)
    return text, title, published_raw
