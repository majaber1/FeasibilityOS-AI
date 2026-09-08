"""
FeasibilityOS AI - Funding Engine
Matches a project to Saudi government / quasi-government funding
programs based on industry, company stage, and project attributes.

This replaces the V1 stub (which returned every program for every
industry) with a simple, transparent scoring model. It is intentionally
rule-based rather than an ML model so the reasoning is explainable,
per the platform's "Explainable AI" development principle.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class FundingProgram:
    code: str
    name: str
    focus_industries: List[str]
    stages: List[str]  # e.g. idea, mvp, early_revenue, growth
    description: str
    name_ar: str
    source_url: str
    eligibility_sample_ar: List[str]
    provider_role_ar: str


PROGRAMS: List[FundingProgram] = [
    FundingProgram(
        code="NTDP",
        name="National Technology Development Program",
        focus_industries=["technology", "ai", "software", "fintech", "saas"],
        stages=["idea", "mvp", "early_revenue"],
        description="Supports tech-driven ventures with grants and acceleration.",
        name_ar="البرنامج الوطني لتنمية تقنية المعلومات — Connect",
        source_url="https://ntdp.gov.sa/connect",
        eligibility_sample_ar=["منشأة تقنية متناهية الصغر أو صغيرة أو متوسطة", "القدرة على تقديم خدمات تقنية وإثبات جدوى التنفيذ", "الخضوع لتقييم البرنامج ومتطلباته عند التقديم"],
        provider_role_ar="برنامج دعم ومنح للمنشآت التقنية المؤهلة",
    ),
    FundingProgram(
        code="MONSHAAT",
        name="Monsha'at (SME General Authority)",
        focus_industries=["general", "retail", "services", "manufacturing"],
        stages=["idea", "mvp", "early_revenue", "growth"],
        description="Broad SME support: licensing, funding facilitation, advisory.",
        name_ar="الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
        source_url="https://www.monshaat.gov.sa/ar",
        eligibility_sample_ar=["منشأة متناهية الصغر أو صغيرة أو متوسطة وفق تعريف منشآت", "استكمال بيانات المنشأة والإيرادات لإصدار شهادة حجم المنشأة", "شروط كل خدمة أو مبادرة تطبق بصورة مستقلة"],
        provider_role_ar="جهة تمكين وتسهيل؛ ليست موافقة تمويل مباشرة",
    ),
    FundingProgram(
        code="SVC",
        name="Saudi Venture Capital Company",
        focus_industries=["technology", "ai", "fintech", "healthcare", "logistics"],
        stages=["early_revenue", "growth"],
        description="Equity co-investment through VC funds for high-growth startups.",
        name_ar="الشركة السعودية للاستثمار الجريء",
        source_url="https://svc.com.sa/en/programs/",
        eligibility_sample_ar=["شركة مقرها السعودية أو تتوسع إلى السعودية للاستثمار المباشر", "مرحلة مبكرة إلى متأخرة ونمو مرتفع أو أثر في قطاع استراتيجي", "الحد الأدنى المنشور لتذكرة الاستثمار المباشر مليون ريال"],
        provider_role_ar="استثمار عبر صناديق واستثمار مباشر؛ ليس قرضًا",
    ),
    FundingProgram(
        code="KAFALAH",
        name="Kafalah Program (SME Loan Guarantee)",
        focus_industries=["general", "manufacturing", "retail", "industrial"],
        stages=["early_revenue", "growth"],
        description="Government-backed loan guarantees to reduce bank lending risk.",
        name_ar="برنامج كفالة لضمان التمويل",
        source_url="https://www.kafalah.gov.sa/ar/Help/Pages/HowTo.aspx",
        eligibility_sample_ar=["التقدم أولًا إلى جهة تمويل متعاونة مع كفالة", "استكمال طلب التمويل والمستندات المتعلقة بالنشاط", "موافقة جهة التمويل المبدئية ثم تقييم كفالة لطلب الضمان"],
        provider_role_ar="ضمان تمويل عبر الجهات التمويلية المشاركة؛ ليس تمويلًا مباشرًا",
    ),
    FundingProgram(
        code="RDIA",
        name="Research, Development and Innovation Authority",
        focus_industries=["ai", "technology", "industrial", "healthcare", "education"],
        stages=["idea", "mvp"],
        description="R&D grants for innovation-heavy, IP-generating projects.",
        name_ar="هيئة تنمية البحث والتطوير والابتكار — حوافز تسويق الملكية الفكرية",
        source_url="https://www.rdia.gov.sa/en/programs/infrastructure/ip-commercialization-incentives-initiative/",
        eligibility_sample_ar=["امتلاك ملكية فكرية مرتبطة بالأولويات الوطنية للبحث والتطوير والابتكار", "متاح للباحثين والمبتكرين والجامعات والمراكز والمستشفيات والأفراد والقطاع الخاص", "يخضع الاختيار لتقييم المبادرة ولا تمثل المطابقة قبولًا"],
        provider_role_ar="حوافز وخدمات لتطوير وحماية وتسويق الملكية الفكرية",
    ),
]


@dataclass
class MatchResult:
    program: str
    name: str
    score_percent: float
    reasons: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    name_ar: str = ""
    source_url: str = ""
    eligibility_sample_ar: List[str] = field(default_factory=list)
    provider_role_ar: str = ""
    verified_at: str = "2026-08-25"


def match(industry: str, stage: str = "idea", has_mvp: bool = False, has_technical_team: bool = True) -> List[Dict]:
    """
    Score every program against the project's profile.
    Returns results sorted by score (highest first), each with the
    reasons that drove the score and what's missing to improve it.
    """
    industry_norm = industry.strip().lower()
    results: List[MatchResult] = []

    for program in PROGRAMS:
        score = 0.0
        reasons = []
        missing = []

        if industry_norm in program.focus_industries:
            score += 60
            reasons.append(f"Industry '{industry}' matches {program.code} focus areas")
        elif "general" in program.focus_industries:
            score += 25
            reasons.append(f"{program.code} supports general/cross-sector SMEs")
        else:
            missing.append(f"Industry '{industry}' is outside {program.code}'s typical focus")

        if stage in program.stages:
            score += 25
            reasons.append(f"Project stage '{stage}' is within {program.code}'s supported range")
        else:
            missing.append(f"Stage '{stage}' is not typically funded by {program.code}")

        if has_mvp:
            score += 10
            reasons.append("MVP validation strengthens the application")
        else:
            missing.append("MVP validation not yet available")

        if has_technical_team:
            score += 5
            reasons.append("Technical team in place")
        else:
            missing.append("Technical team requirements not yet met")

        results.append(MatchResult(
            program=program.code,
            name=program.name,
            score_percent=min(round(score, 1), 100.0),
            reasons=reasons,
            missing=missing,
            name_ar=program.name_ar,
            source_url=program.source_url,
            eligibility_sample_ar=program.eligibility_sample_ar,
            provider_role_ar=program.provider_role_ar,
        ))

    results.sort(key=lambda r: r.score_percent, reverse=True)
    return [r.__dict__ for r in results]
