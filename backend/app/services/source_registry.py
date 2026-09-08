"""
Saudi source authority registry.

Classifies where a piece of evidence came from so the product can distinguish
an official primary source from a regulator, a reputable institution, a
commercial source, a user-supplied document, or an AI inference -- and so AI
output can never silently present itself as official evidence.

This registry maps known *domains* of Saudi government/institutional bodies
to an authority tier. It intentionally stores no market data, fees,
regulations, or other factual content -- only "if a claim cites this domain,
here is how authoritative the publisher is." Domains are maintained here as a
plain list so entries can be corrected/extended without a migration. Treat
this list as a starting index, not a verified-current directory: confirm a
domain before relying on it for a production decision.

AUTHORITY_LEVELS is the closed set every EvidenceItem.authority_level must be
drawn from; authority_level is always computed server-side (see
classify_authority) and is never trusted from client input.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

AUTHORITY_LEVELS = (
    "OFFICIAL_PRIMARY",
    "OFFICIAL_SECONDARY",
    "REGULATOR",
    "REPUTABLE_INSTITUTION",
    "COMMERCIAL_SOURCE",
    "USER_DOCUMENT",
    "AI_INFERENCE",
    "UNVERIFIED",
)

# source_type values the evidence API accepts. "ai_inference" is special: it
# can never be marked verification_status=verified (see evidence.py).
SOURCE_TYPES = (
    "official_statistic",
    "regulation",
    "funding_program",
    "market_report",
    "news",
    "survey",
    "user_document",
    "ai_inference",
    "other",
)

VERIFICATION_STATUSES = ("verified", "user_provided", "unverified")

CONFIDENCE_LEVELS = ("low", "medium", "high")

# key -> (name_en, name_ar, domain, authority_level). Domains are matched by
# suffix against the evidence source_url's hostname.
SAUDI_AUTHORITIES: dict[str, tuple[str, str, str, str]] = {
    "gastat": ("General Authority for Statistics (GASTAT)", "الهيئة العامة للإحصاء", "stats.gov.sa", "OFFICIAL_PRIMARY"),
    "saudi_open_data": ("Saudi Open Data Portal", "منصة البيانات المفتوحة", "data.gov.sa", "OFFICIAL_PRIMARY"),
    "saudi_business_center": ("Saudi Business Center", "مركز الأعمال السعودي", "business.sa", "OFFICIAL_PRIMARY"),
    "ministry_of_commerce": ("Ministry of Commerce", "وزارة التجارة", "mc.gov.sa", "OFFICIAL_PRIMARY"),
    "zatca": ("Zakat, Tax and Customs Authority (ZATCA)", "هيئة الزكاة والضريبة والجمارك", "zatca.gov.sa", "REGULATOR"),
    "monshaat": ("Small and Medium Enterprises General Authority (Monsha'at)", "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)", "monshaat.gov.sa", "OFFICIAL_PRIMARY"),
    "hrsd": ("Ministry of Human Resources and Social Development", "وزارة الموارد البشرية والتنمية الاجتماعية", "hrsd.gov.sa", "OFFICIAL_PRIMARY"),
    "misa": ("Ministry of Investment Saudi Arabia (MISA)", "وزارة الاستثمار السعودية", "misa.gov.sa", "OFFICIAL_PRIMARY"),
    "modon": ("Saudi Authority for Industrial Cities and Technology Zones (MODON)", "الهيئة السعودية للمدن الصناعية وتقنية المعلومات (مدن)", "modon.gov.sa", "OFFICIAL_PRIMARY"),
    "balady": ("Ministry of Municipal, Rural Affairs and Housing (Balady)", "وزارة الشؤون البلدية والقروية والإسكان (بلدي)", "balady.gov.sa", "OFFICIAL_PRIMARY"),
    "sama": ("Saudi Central Bank (SAMA)", "البنك المركزي السعودي", "sama.gov.sa", "REGULATOR"),
    "cma": ("Capital Market Authority (CMA)", "هيئة السوق المالية", "cma.org.sa", "REGULATOR"),
    "sfda": ("Saudi Food and Drug Authority (SFDA)", "الهيئة العامة للغذاء والدواء", "sfda.gov.sa", "REGULATOR"),
    "vision_2030": ("Vision 2030", "رؤية 2030", "vision2030.gov.sa", "OFFICIAL_PRIMARY"),
}


def _hostname(source_url: Optional[str]) -> Optional[str]:
    if not source_url:
        return None
    try:
        host = urlparse(source_url).hostname
    except ValueError:
        return None
    return host.lower() if host else None


def registry_entries() -> list[dict]:
    return [
        {"key": key, "name_en": name_en, "name_ar": name_ar, "domain": domain, "authority_level": level}
        for key, (name_en, name_ar, domain, level) in SAUDI_AUTHORITIES.items()
    ]


def classify_authority(source_url: Optional[str], source_type: str) -> tuple[str, Optional[str]]:
    """Return (authority_level, matched_registry_key).

    AI-sourced claims are always AI_INFERENCE regardless of URL, so an AI
    inference can never masquerade as an official source. User-uploaded
    documents are USER_DOCUMENT unless their URL happens to match a known
    government domain. Everything else falls back to UNVERIFIED until it
    matches a registry domain (gov.sa domains not yet in the registry still
    resolve to OFFICIAL_SECONDARY as a conservative default) or is a
    known commercial research publisher tier.
    """
    if source_type == "ai_inference":
        return "AI_INFERENCE", None

    host = _hostname(source_url)
    if host:
        for key, (_name_en, _name_ar, domain, level) in SAUDI_AUTHORITIES.items():
            if host == domain or host.endswith("." + domain):
                return level, key
        if host.endswith(".gov.sa"):
            return "OFFICIAL_SECONDARY", None

    if source_type == "user_document":
        return "USER_DOCUMENT", None
    if source_type in {"market_report", "news"}:
        return "COMMERCIAL_SOURCE", None
    return "UNVERIFIED", None
