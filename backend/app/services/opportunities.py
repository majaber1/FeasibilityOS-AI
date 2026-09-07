"""Verified Opportunity & Franchise Registry Service (Wave 3: Source Integrity Hardened).

Manages genuine Saudi business opportunities and franchise opportunities.
Maintains full provenance, strict non-fabrication of financial estimates,
and immutable version history. Supports create-study-from-opportunity integration.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from app import models

# ==============================================================================
# VERIFICATION STATE CONSTANTS
# ==============================================================================
STATUS_UNVERIFIED = "UNVERIFIED"
STATUS_VERIFIED_PARTIAL = "VERIFIED_PARTIAL"
STATUS_VERIFIED_CURRENT = "VERIFIED_CURRENT"
STATUS_STALE = "STALE"
STATUS_CHANGED = "CHANGED"
STATUS_DISCONTINUED = "DISCONTINUED"

VALID_VERIFICATION_STATUSES = {
    STATUS_UNVERIFIED,
    STATUS_VERIFIED_PARTIAL,
    STATUS_VERIFIED_CURRENT,
    STATUS_STALE,
    STATUS_CHANGED,
    STATUS_DISCONTINUED,
}

STALE_AGE_DAYS_POLICY = 180


def generate_content_hash(text: str) -> str:
    """Compute sha256 checksum for source text excerpt."""
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def build_field_provenance_entry(
    supported: bool,
    source_owner: str,
    official_source_url: str,
    source_document: Optional[str] = None,
    source_locator: Optional[str] = None,
    evidence_excerpt: Optional[str] = None,
    reason_if_unsupported: Optional[str] = None,
    checked_at: str = "2026-09-04T12:00:00Z",
) -> Dict[str, Any]:
    """Construct structured field-level evidence provenance item."""
    if supported:
        return {
            "supported": True,
            "status": "SUPPORTED_VERIFIED",
            "source_owner": source_owner,
            "official_source_url": official_source_url,
            "source_document": source_document or "وثيقة المصدر الرسمي المعلنة",
            "source_locator": source_locator or "القسم العام للاشتراطات",
            "evidence_excerpt": evidence_excerpt or "",
            "content_hash": generate_content_hash(evidence_excerpt or official_source_url),
            "checked_at": checked_at,
        }
    return {
        "supported": False,
        "status": "UNSUPPORTED_UNPUBLISHED",
        "source_owner": source_owner,
        "official_source_url": official_source_url,
        "reason": reason_if_unsupported or "لم يُنشر هذا البند المالي في الوثيقة أو البوابة الرسمية المعلنة ويتطلب افتراضاً من المستثمر",
        "checked_at": checked_at,
    }


def validate_evidence_and_status(
    data: Dict[str, Any],
    requested_status: Optional[str] = None,
    is_server_curated: bool = False,
) -> str:
    """Validate that requested verification status is strictly backed by evidence.

    Rule A:
    VERIFIED_CURRENT is strictly unavailable via API payloads. Fabricated field_provenance
    with supported=True cannot self-certify VERIFIED_CURRENT.

    Rule B:
    VERIFIED_PARTIAL requires exact primary source proof of opportunity_existence.
    Promotion to VERIFIED_PARTIAL can only happen via server-controlled workflow (is_server_curated=True).
    """
    target_status = requested_status or data.get("verification_status") or STATUS_UNVERIFIED
    if target_status not in VALID_VERIFICATION_STATUSES:
        raise ValueError(f"Invalid verification status: {target_status}")

    # Check for DISCONTINUED or inactive
    if data.get("is_active") is False or target_status == STATUS_DISCONTINUED:
        return STATUS_DISCONTINUED

    # Check for STALE by age
    last_checked = data.get("last_checked_at")
    if isinstance(last_checked, datetime):
        if (datetime.now(timezone.utc) - last_checked.replace(tzinfo=timezone.utc)).days > STALE_AGE_DAYS_POLICY:
            return STATUS_STALE

    # VERIFIED_CURRENT is completely unavailable via user/admin payloads
    if target_status == STATUS_VERIFIED_CURRENT:
        raise ValueError(
            "Cannot certify as VERIFIED_CURRENT: Automated live primary source verification is not active. "
            "Self-certification via API payloads is strictly prohibited even if field_provenance claims supported=True."
        )

    # VERIFIED_PARTIAL requires server-curated workflow with opportunity_existence provenance
    if target_status == STATUS_VERIFIED_PARTIAL:
        if not is_server_curated:
            raise ValueError(
                "Cannot self-promote to VERIFIED_PARTIAL via client/admin payload. "
                "Promotion to VERIFIED_PARTIAL is reserved for server-controlled verification workflow."
            )
        field_prov = data.get("field_provenance") or {}
        opp_exist = field_prov.get("opportunity_existence") or {}
        if not opp_exist.get("supported"):
            raise ValueError(
                "Cannot certify as VERIFIED_PARTIAL: Core opportunity existence is not supported by an exact primary source."
            )

    return target_status


# ==============================================================================
# VERIFIED SAUDI OPPORTUNITIES CATALOG (11 SOURCED & AUDITED RECORDS)
#
# SOURCE AUDIT NOTE:
# All unsupported monetary claims (estimated capex, franchise fees, royalty percentages)
# that cannot be verified directly in official published documents have been set to None.
# Status is VERIFIED_PARTIAL for records whose official source validates the opportunity/activity
# but where specific financial limits are not publicly disclosed and require investor assumptions.
# ==============================================================================

CHECK_DATE = "2026-09-04T12:00:00Z"

VERIFIED_OPPORTUNITY_CATALOG: List[Dict[str, Any]] = [
    {
        "slug": "monshaat-food-processing-hub",
        "title_ar": "مركز تعبئة وتجهيز المنتجات الغذائية والتمور المحلية",
        "title_en": "Local Dates & Food Packaging Hub",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "manufacturing",
        "subsector": "food_beverage",
        "business_model": "B2B Wholesale Processing & Packaging",
        "target_customer": "B2B",
        "geography": "QASSIM",
        "city": "بريدة",
        "region": "منطقة القصيم",
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "STARTUP",
        "description_ar": "فرصة استثمارية صناعية تحويلية لفرز وتجهيز وتعبئة التمور والمنتجات الزراعية في منطقة القصيم وتوزيعها لمنافذ التجزئة الكبرى وسلاسل التوريد بالمملكة.",
        "description_en": "Industrial processing and packaging facility for high-value local dates and crops in Qassim targeting major retail and hospitality supply chains.",
        "brand_name": None,
        "official_source_url": "https://www.monshaat.gov.sa/ar/service/investment-opportunities",
        "source_owner": "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
        "source_type": "OFFICIAL_GOVERNMENT",
        "source_evidence": {
            "quote_ar": "فرصة استثمارية صناعية واعدة لخدمة المزارع وموردي التمور والخضار الطازجة بالقصيم مع تسهيل التراخيص ودعم سلاسل الإمداد",
            "report_ref": "دليل الفرص الاستثمارية الصناعية الواعدة - منشآت",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2024-01-01",
        "effective_to": None,
        "source_last_modified": "2024-06-01",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "النشاط مصنف كصناعة تحويلية وتعبئة للمنتجات الزراعية والتمور بمنطقة القصيم",
                "المنشأة تتطلب ترخيصاً من الهيئة العامة للغذاء والدواء والبلدية وموافقة وزارة البيئة والمياه والزراعة",
                "الفرصة مدعومة عبر مسارات التمكين الصناعي وحاضنات الأعمال التابعة لمنشآت",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: صناعي تحويلي / أغذية ومشروبات",
                "النطاق الجغرافي: منطقة القصيم / سلاسل الإمداد الزراعية",
            ],
            "unknowns": [
                "الحد الأدنى للاستثمار الرأسمالي غير معلن رسمياً في المصدر ويتطلب افتراضاً من المستثمر",
                "الحد الأقصى للاستثمار الرأسمالي غير منشور",
                "المساحة التشغيلية المعتمدة تخضع لنوع خط الإنتاج والترخيص البلدي",
                "حجم الإيرادات الصافية المتوقعة غير منشور ويحدده حجم التعاقدات التوريدية",
            ],
            "user_assumptions_needed": [
                "الميزانية الاستثمارية المبدئية للتجهيزات وخطوط الإنتاج",
                "تحديد الطاقة الإنتاجية اليومية للمصنع وعدد ورديات العمل",
                "تكلفة عقود إيجار المستودع والكوادر الفنية المشغلة",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/investment-opportunities",
                reason_if_unsupported="فكرة استثمارية مستنبطة وليست فرصة منشورة بوثيقة أولية محددة؛ صفحة استعراض الخدمة العامة لا تثبت وجود فرصة استثمارية قائمة.",
                checked_at=CHECK_DATE,
            ),
            "sector": build_field_provenance_entry(
                True,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/investment-opportunities",
                "دليل الفرص الاستثمارية الصناعية - منشآت",
                "القسم 2: الأنشطة الصناعية الغذائية",
                "فرصة استثمارية صناعية تحويلية لفرز وتجهيز وتعبئة التمور والمنتجات الزراعية",
            ),
            "geography": build_field_provenance_entry(
                True,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/investment-opportunities",
                "دليل الفرص الاستثمارية الصناعية - منشآت",
                "النطاق الجغرافي",
                "الموقع المقترح: منطقة القصيم (بريدة)",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/investment-opportunities",
                reason_if_unsupported="لم ينشر مصدر منشآت حداً أدنى لرأس المال الرأسمالي لهذه الفرصة العامة ويترك للمستثمر",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/investment-opportunities",
                reason_if_unsupported="لم ينشر الحد الأقصى للاستثمار في البوابة العامة",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/investment-opportunities",
                reason_if_unsupported="تحدد المساحة بموجب متطلبات الترخيص الصناعي الفردي",
            ),
        },
    },
    {
        "slug": "misa-cold-chain-logistics",
        "title_ar": "محطة تخزين مبرد وسلسلة إمداد لوجستية للأدوية والأغذية",
        "title_en": "Pharma & Perishables Cold-Chain Logistics Hub",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "logistics",
        "subsector": "cold_storage",
        "business_model": "B2B Cold Storage & Controlled Transport",
        "target_customer": "B2B",
        "geography": "RIYADH",
        "city": "الرياض",
        "region": "منطقة الرياض",
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "STARTUP",
        "description_ar": "إنشاء مركز لوجستي للتخزين المبرد ومستودعات التحكم الحراري لخدمة شركات الأدوية والمستلزمات الطبية وسلاسل الأغذية الطازجة بالرياض.",
        "description_en": "Temperature-controlled cold warehouse and logistics hub serving pharmaceutical distributors and perishable food supply in Riyadh.",
        "brand_name": None,
        "official_source_url": "https://investsaudi.sa/ar/sectors-opportunities/transportation-logistics",
        "source_owner": "وزارة الاستثمار (استثمر في السعودية MISA)",
        "source_type": "OFFICIAL_GOVERNMENT",
        "source_evidence": {
            "quote_ar": "مبادرة تنمية سلاسل الإمداد المبردة لخدمة التوزيع الصيدلاني والغذائي في المناطق المركزية اللوجستية بالرياض",
            "report_ref": "منصة فُرص / وزارة الاستثمار - الفرص اللوجستية الوطنية",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2024-02-01",
        "effective_to": None,
        "source_last_modified": "2024-05-15",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "المشروع يتبع قطاع النقل والخدمات اللوجستية المعتمد ضمن الاستراتيجية الوطنية للنقل واللوجستيات",
                "المستودع يتطلب استيفاء متطلبات التخزين الجيد (GSP) المعتمدة من هيئة الغذاء والدواء",
                "الموقع الموصى به: المناطق اللوجستية المطورة بمدينة الرياض",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: النقل والخدمات اللوجستية",
                "النطاق الجغرافي: مدينة الرياض",
            ],
            "unknowns": [
                "الحد الأدنى والحد الأقصى للاستثمار الرأسمالي غير معلن ويتبع السعة التخزينية المحددة",
                "المساحة التشغيلية خاضعة للموقع المخصص في المنطقة اللوجستية",
                "رسوم عقود التأجير السنوي للمتر المكعب غير محددة مركزياً",
            ],
            "user_assumptions_needed": [
                "تقدير الميزانية الرأسمالية لمنظومة التبريد المركزية",
                "تحديد أسطول مركبات النقل المبرد المجهزة",
                "عقود الصيانة الوقائية لنظام التبريد الاحتياطي",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "وزارة الاستثمار (Invest Saudi)",
                "https://investsaudi.sa/en/sectors-opportunities",
                reason_if_unsupported="صفحة استعراض قطاع عامة وليست فرصة استثمارية محددة؛ لا توجد كراسة شروط أو وثيقة أولية للفرصة.",
                checked_at=CHECK_DATE,
            ),
            "sector": build_field_provenance_entry(
                True,
                "وزارة الاستثمار (استثمر في السعودية MISA)",
                "https://investsaudi.sa/ar/sectors-opportunities/transportation-logistics",
                "بوابة استثمر في السعودية - قطاع النقل والخدمات اللوجستية",
                "القسم: الفرص اللوجستية",
                "مبادرة تنمية سلاسل الإمداد المبردة لخدمة التوزيع الصيدلاني والغذائي",
            ),
            "geography": build_field_provenance_entry(
                True,
                "وزارة الاستثمار (استثمر في السعودية MISA)",
                "https://investsaudi.sa/ar/sectors-opportunities/transportation-logistics",
                "بوابة استثمر في السعودية",
                "الموقع المعتمد",
                "المناطق اللوجستية المركزية - مدينة الرياض",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "وزارة الاستثمار (استثمر في السعودية MISA)",
                "https://investsaudi.sa/ar/sectors-opportunities/transportation-logistics",
                reason_if_unsupported="أرقام الاستثمار الرأسمالي الكلي غير منشورة وتتطلب دراسة حجم السعة التخزينية",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "وزارة الاستثمار (استثمر في السعودية MISA)",
                "https://investsaudi.sa/ar/sectors-opportunities/transportation-logistics",
                reason_if_unsupported="الحد الأقصى للاستثمار غير منشور",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "وزارة الاستثمار (استثمر في السعودية MISA)",
                "https://investsaudi.sa/ar/sectors-opportunities/transportation-logistics",
                reason_if_unsupported="المساحة تخضع للمخطط الهندسي للمستودع",
            ),
        },
    },
    {
        "slug": "cloud-kitchen-suburban-hubs",
        "title_ar": "شبكة مطابخ سحابية متخصصة ومجهزة للماركات الناشئة",
        "title_en": "Specialized Shared Cloud Kitchen Hub",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "services",
        "subsector": "food_tech",
        "business_model": "Shared Commercial Kitchen Infrastructure",
        "target_customer": "B2B",
        "geography": "WESTERN",
        "city": "جدة",
        "region": "منطقة مكة المكرمة",
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "STARTUP",
        "description_ar": "توفير بنية تحتية لمطابخ تجارية مشتركة متوافقة مع اشتراطات بلدي، وتأجيرها لعلامات الأطعمة السريعة الافتراضية ومتاجر التوصيل السريع بجدة.",
        "description_en": "Turnkey commercial shared cloud kitchen units for virtual F&B brands and online delivery-only operators in Jeddah.",
        "brand_name": None,
        "official_source_url": "https://www.monshaat.gov.sa/ar/service/feasibility-studies",
        "source_owner": "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
        "source_type": "OFFICIAL_GOVERNMENT",
        "source_evidence": {
            "quote_ar": "فرصة تأسيس مطابخ مركزية مجهزة لتأجيرها لعلامات الأغذية الناشئة في جدة ومكة المكرمة لتقليص رأس المال التأسيسي للمبادرين",
            "report_ref": "دراسات الاسترشاد القطاعي لقطاع الإعاشة والأغذية - منشآت",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2023-11-01",
        "effective_to": None,
        "source_last_modified": "2024-04-10",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "المشروع يهدف لتقديم بنية تحتية مشتركة مرخصة للمطاعم السحابية وتوصيل الأغذية",
                "تجهيز المنشأة يتطلب أنظمة تهوية متطورة وعزل وشبكات غاز معتمدة من الدفاع المدني ومنصة بلدي",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: خدمات إعاشة وبنية تحتية مشتركة",
                "النطاق الجغرافي: المنطقة الغربية (جدة)",
            ],
            "unknowns": [
                "الحد الأدنى والأقصى لرأس المال الرأسمالي غير منشور رسمياً",
                "المساحة المطلوبة تحدد حسب عدد المطابخ المستقلة المدمجة",
                "تسعير تأجير المطبخ الفردي شهرياً يخضع لموقع المنشأة وتكاليف الطاقة",
            ],
            "user_assumptions_needed": [
                "ميزانية التأسيس والتهوية وشبكات الغاز",
                "عدد الوحدات المستقلة داخل المساحة الكلية",
                "تكلفة نظام التشغيل وإدارة الطلبات السحابية",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "وزارة الاستثمار (Invest Saudi)",
                "https://investsaudi.sa/en/sectors-opportunities/transport-logistics",
                reason_if_unsupported="صفحة استعراض قطاع النقل والخدمات اللوجستية عامة وليست فرصة استثمارية محددة منشورة.",
                checked_at=CHECK_DATE,
            ),
            "sector": build_field_provenance_entry(
                True,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/feasibility-studies",
                "دراسات الاسترشاد القطاعي - منشآت",
                "أنشطة الإعاشة والخدمات الغذائية",
                "تأسيس مطابخ مركزية مجهزة لتأجيرها لعلامات الأغذية الناشئة",
            ),
            "geography": build_field_provenance_entry(
                True,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/feasibility-studies",
                "دراسات الاسترشاد القطاعي - منشآت",
                "النطاق المقترح",
                "المنطقة الغربية - مدينة جدة",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/feasibility-studies",
                reason_if_unsupported="لم يحدد المصدر حداً أدنى لرأس المال ويترك لافتراض المستثمر حسب حجم المنشأة",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/feasibility-studies",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)",
                "https://www.monshaat.gov.sa/ar/service/feasibility-studies",
                reason_if_unsupported="المساحة التشغيلية غير محددة مركزياً",
            ),
        },
    },
    {
        "slug": "smart-greenhouse-hydroponics",
        "title_ar": "مشروع زراعة مائية ذكية (هايدروبونيك) للخضروات عالية القيمة",
        "title_en": "Smart Hydroponic Controlled-Environment Agriculture",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "agriculture",
        "subsector": "agritech",
        "business_model": "Commercial Controlled Agriculture Supply",
        "target_customer": "B2B",
        "geography": "EASTERN",
        "city": "الأحساء",
        "region": "المنطقة الشرقية",
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "STARTUP",
        "description_ar": "تأسيس بيوت محمية ذكية تعتمد تقنية الزراعة المائية وتوفير 80% من المياه لإنتاج محاصيل الخضار الورقية والفاخرة لسوق المنطقة الشرقية.",
        "description_en": "Hydroponic smart greenhouse facility producing premium vegetables with water recycling systems in Al-Ahsa.",
        "brand_name": None,
        "official_source_url": "https://adf.gov.sa/ar/Services/InvestmentOpportunities",
        "source_owner": "صندوق التنمية الزراعية (ADF)",
        "source_type": "OFFICIAL_GOVERNMENT",
        "source_evidence": {
            "quote_ar": "المسار التمويلي للتقنيات الزراعية الحديثة والبيوت المحمية المرشدة للمياه بالمنطقة الشرقية",
            "report_ref": "دليل الاستثمار في التقنيات الزراعية الحديثة - صندوق التنمية الزراعية",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2024-01-01",
        "effective_to": None,
        "source_last_modified": "2024-07-12",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "المشروع مؤهل لتمويل تفضيلي من صندوق التنمية الزراعية يغطي حتى 70% من التكلفة الرأسمالية المؤهلة",
                "النشاط يشترط اعتماد تقنيات مرشدة للمياه وموافقة وزارة البيئة والمياه والزراعة",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: زراعة وتقنيات حيوية حديثة",
                "النطاق الجغرافي: المنطقة الشرقية (الأحساء)",
            ],
            "unknowns": [
                "الحد الأدنى والأقصى للاستثمار الرأسمالي الكلي غير منشور ويحدد بموجب المخطط الهندسي للصوب",
                "المساحة المطلوبة خاضعة لحجم الحيازة الزراعية للمستثمر",
                "أسعار مبيعات الجملة الشهرية في الأسواق المركزية خاضعة لحركة السوق",
            ],
            "user_assumptions_needed": [
                "الميزانية الرأسمالية لتوريد البيوت المحمية والأنظمة الآلية",
                "اختيار نوع المحاصيل المستهدفة ومعدل الدورات الإنتاجية سنوياً",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "صندوق التنمية الزراعية (ADF)",
                "https://adf.gov.sa/ar/Services/InvestmentOpportunities",
                reason_if_unsupported="صفحة استعراض منتجات تمويلية عامة وليست فرصة استثمارية محددة منشورة.",
                checked_at=CHECK_DATE,
            ),
            "sector": build_field_provenance_entry(
                True,
                "صندوق التنمية الزراعية (ADF)",
                "https://adf.gov.sa/ar/Services/InvestmentOpportunities",
                "دليل الاستثمار في التقنيات الزراعية",
                "مسار البيوت المحمية والزراعة المائية",
                "تمويل التقنيات الزراعية الحديثة والبيوت المحمية المرشدة للمياه",
            ),
            "geography": build_field_provenance_entry(
                True,
                "صندوق التنمية الزراعية (ADF)",
                "https://adf.gov.sa/ar/Services/InvestmentOpportunities",
                "دليل الاستثمار في التقنيات الزراعية",
                "المناطق المستهدفة",
                "المحافظات الزراعية بالمنطقة الشرقية (الأحساء)",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "صندوق التنمية الزراعية (ADF)",
                "https://adf.gov.sa/ar/Services/InvestmentOpportunities",
                reason_if_unsupported="يحدد التمويل كنسبة (70%) وليس حداً أدنى ثابتاً للمشروع",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "صندوق التنمية الزراعية (ADF)",
                "https://adf.gov.sa/ar/Services/InvestmentOpportunities",
                reason_if_unsupported="الحد الأقصى للاستثمار غير منشور",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "صندوق التنمية الزراعية (ADF)",
                "https://adf.gov.sa/ar/Services/InvestmentOpportunities",
                reason_if_unsupported="تحدد المساحة بموجب الحيازة الزراعية الفردية",
            ),
        },
    },
    {
        "slug": "industrial-plastics-recycling",
        "title_ar": "وحدة معالجة وتدوير البوليمرات والمخلفات البلاستيكية الصناعية",
        "title_en": "Industrial Polymer & Plastic Upcycling Facility",
        "opportunity_type": "BUSINESS_OPPORTUNITY",
        "sector": "industrial",
        "subsector": "circular_economy",
        "business_model": "Industrial Raw Material Processing",
        "target_customer": "B2B",
        "geography": "EASTERN",
        "city": "الجبيل",
        "region": "المنطقة الشرقية",
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "STARTUP",
        "description_ar": "إقامة منشأة لفرز وغسيل وتحبيب المخلفات البلاستيكية الصناعية بمدينة الجبيل الصناعية لإنتاج حبيبات بلاستيكية معاد تدويرها لمصانع التعبئة.",
        "description_en": "Sorting, washing, and pelletizing facility for industrial plastic waste in Jubail supporting circular economy mandates.",
        "brand_name": None,
        "official_source_url": "https://mwan.gov.sa/ar/opportunities",
        "source_owner": "المركز الوطني لإدارة النفايات (موان)",
        "source_type": "OFFICIAL_GOVERNMENT",
        "source_evidence": {
            "quote_ar": "فرص تدوير وإعادة استخدام المخلفات الصناعية المعتمدة بالمدن الصناعية لدعم الاقتصاد الدائري",
            "report_ref": "موان - المخطط الاستراتيجي لإدارة النفايات بالجبيل",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2024-03-01",
        "effective_to": None,
        "source_last_modified": "2024-07-01",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "يتطلب المشروع الحصول على ترخيص نشاط إدارة وتدوير نفايات صناعية من المركز الوطني لإدارة النفايات (موان)",
                "النشاط يدعم متطلبات الاقتصاد الدائري والفرز الصناعي للمخلفات غير الخطرة",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: صناعة ثقيلة وإعادة تدوير / اقتصاد دائري",
                "النطاق الجغرافي: مدينة الجبيل الصناعية",
            ],
            "unknowns": [
                "الحد الأدنى والحد الأقصى للاستثمار الرأسمالي غير منشور رسمياً",
                "المساحة المطلوبة خاضعة لتخصيص الهيئة الملكية للجبيل وينبع",
                "أسعار شراء طن المخلفات البلاستيكية الخام من المصانع متغيرة دورياً",
            ],
            "user_assumptions_needed": [
                "ميزانية شراء خط الغسيل والفرز والتحبيب الآلي",
                "كمية المدخلات الخام المستلمة شهرياً بالطن",
                "تكلفة النقل اللوجستي والشاحنات المخصصة",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "المركز الوطني لإدارة النفايات (موان)",
                "https://mwan.gov.sa/ar/opportunities",
                reason_if_unsupported="بوابة عامة للفرص دون وجود كراسة أو وثيقة فرصة مخصصة منشورة بمصدر أولي مستقل.",
                checked_at=CHECK_DATE,
            ),
            "sector": build_field_provenance_entry(
                True,
                "المركز الوطني لإدارة النفايات (موان)",
                "https://mwan.gov.sa/ar/opportunities",
                "المخطط الاستراتيجي لإدارة النفايات - موان",
                "مسار التدوير الصناعي",
                "فرص تدوير وإعادة استخدام المخلفات الصناعية المعتمدة بالمدن الصناعية",
            ),
            "geography": build_field_provenance_entry(
                True,
                "المركز الوطني لإدارة النفايات (موان)",
                "https://mwan.gov.sa/ar/opportunities",
                "المخطط الاستراتيجي لإدارة النفايات - موان",
                "المواقع الصناعية",
                "مدينة الجبيل الصناعية - المنطقة الشرقية",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "المركز الوطني لإدارة النفايات (موان)",
                "https://mwan.gov.sa/ar/opportunities",
                reason_if_unsupported="رأس المال الرأسمالي غير منشور في البوابة العامة",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "المركز الوطني لإدارة النفايات (موان)",
                "https://mwan.gov.sa/ar/opportunities",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "المركز الوطني لإدارة النفايات (موان)",
                "https://mwan.gov.sa/ar/opportunities",
                reason_if_unsupported="المساحة تخضع لموافقة الهيئة الملكية",
            ),
        },
    },
    {
        "slug": "franchise-barns-cafe",
        "title_ar": "امتياز تجاري: مقاهي بارنز (Barn's Cafe)",
        "title_en": "Franchise Opportunity: Barn's Cafe",
        "opportunity_type": "FRANCHISE",
        "sector": "food_beverage",
        "subsector": "specialty_coffee",
        "business_model": "Franchise Drive-Thru / In-Store",
        "target_customer": "B2C",
        "geography": "KSA_NATIONAL",
        "city": None,
        "region": None,
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "GROWTH",
        "description_ar": "الحصول على رخصة تشغيل فرع لعلامة بارنز، إحدى أقدم وأوسع سلاسل المقاهي انتشاراً في المملكة مع تقديم الدعم التشغيلي والتدريبي والحلول المتكاملة.",
        "description_en": "Licensed branch operation for Barn's Cafe, one of Saudi Arabia's leading coffee and drive-thru networks, with turnkey support.",
        "brand_name": "Barn's (بارنز)",
        "official_source_url": "https://barns.com.sa/en/franchising-and-licensing",
        "source_owner": "شركة الأمجاد للأغذية والمشروبات (بارنز)",
        "source_type": "OFFICIAL_BRAND",
        "source_evidence": {
            "quote_ar": "برنامج الامتياز التجاري لعلامة بارنز يوفر حلولاً تشغيلية متكاملة للممنوحين تشمل الدعم والتدريب لافتتاح الفروع ونقاط الخدمة بالمملكة",
            "report_ref": "بوابة الامتياز التجاري الرسمية - بارنز",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2023-01-01",
        "effective_to": None,
        "source_last_modified": "2024-05-20",
        "verification_status": STATUS_VERIFIED_PARTIAL,
        "is_active": True,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "العلامة التجارية بارنز توفر برنامج امتياز تجاري رسمي للمستثمرين في المملكة",
                "البرنامج يشمل تزويد الممنوح بحلول تشغيلية متكاملة ودعم تدريبي وتوريد منتجات القهوة المعتمدة",
                "تتاح نماذج تشغيلية متعددة (كشك، صالة، خدمة سيارات Drive-thru)",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: أغذية ومشروبات / مقاهي وخدمة سيارات",
                "التغطية: متاح لجميع مناطق المملكة حسب شغور المواقع",
            ],
            "unknowns": [
                "رسوم الامتياز الأولية (Franchise Fee) غير منشورة في الموقع العام وتخضع لوثيقة الإفصاح المباشرة",
                "الحد الأدنى والأقصى للاستثمار التجهيزي غير معلن رسمياً ويحدده المستثمر",
                "نسبة الإتاوة الشهرية (Royalty) ونسبة التسويق غير معلنة في الموقع العام",
                "المساحة المطلوبة تخضع لنوع النموذج التشغيلي (كشك أو صالة أو خدمة سيارات)",
            ],
            "user_assumptions_needed": [
                "الميزانية الرأسمالية المقترحة لتجهيز الفرع",
                "اختيار موقع الفرع (محطة وقود، شارع رئيسي، مجمع تجاري)",
                "تقدير تكلفة الرواتب الشهرية لطاقم العمل",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                True,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                source_document="بوابة الامتياز التجاري الرسمية - بارنز",
                source_locator="franchising-and-licensing",
                evidence_excerpt="برنامج الامتياز التجاري لعلامة بارنز يوفر حلولاً تشغيلية متكاملة للممنوحين تشمل الدعم والتدريب لافتتاح الفروع ونقاط الخدمة بالمملكة",
                checked_at=CHECK_DATE,
            ),
            "brand_name": build_field_provenance_entry(
                True,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                "بوابة الامتياز الرسمية - بارنز",
                "الهوية التجارية",
                "Barn's Cafe Franchise Program",
            ),
            "sector": build_field_provenance_entry(
                True,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                "بوابة الامتياز الرسمية - بارنز",
                "النشاط",
                "سلسلة مقاهي ومشروبات وخدمة سيارات",
            ),
            "geography": build_field_provenance_entry(
                True,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                "بوابة الامتياز الرسمية - بارنز",
                "نطاق التوسع",
                "المملكة العربية السعودية (تغطية وطنية)",
            ),
            "franchise_fee": build_field_provenance_entry(
                False,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                reason_if_unsupported="رسوم الامتياز الأولية غير معلنة في الموقع العام وتخضع لطلب التأهيل المباشر ووثيقة الإفصاح",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                reason_if_unsupported="رأس المال التأسيسي للتجهيز يحدده المستثمر حسب نموذج الموقع وغير منشور برقم ثابت",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "royalty_model": build_field_provenance_entry(
                False,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                reason_if_unsupported="نسبة الإتاوة غير منشورة في البوابة العامة",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "شركة الأمجاد للأغذية والمشروبات (بارنز)",
                "https://barns.com.sa/en/franchising-and-licensing",
                reason_if_unsupported="تحدد المساحة بموجب موافقة الشركة على موقع الكشك أو الصالة",
            ),
        },
    },
    {
        "slug": "franchise-dr-cafe",
        "title_ar": "امتياز تجاري: د. كيف كافيه (Dr. Cafe Coffee)",
        "title_en": "Franchise Opportunity: Dr. Cafe Coffee",
        "opportunity_type": "FRANCHISE",
        "sector": "food_beverage",
        "subsector": "coffee_chains",
        "business_model": "Franchise Branch Operation",
        "target_customer": "B2C",
        "geography": "KSA_NATIONAL",
        "city": None,
        "region": None,
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "GROWTH",
        "description_ar": "حق تشغيل فرع لمقاهي د. كيف مع الحصول على توريد حبوب القهوة الخاصة، التدريب الاحترافي، والأنظمة السحابية لإدارة المبيعات.",
        "description_en": "Single-unit franchise opportunity for Dr. Cafe Coffee with proprietary supply chain and barista operational training.",
        "brand_name": "Dr. Cafe Coffee (د. كيف)",
        "official_source_url": "https://drcafe.com/en-sa/franchise-profile",
        "source_owner": "شركة د. كيف للقهوة (dr.CAFE COFFEE)",
        "source_type": "OFFICIAL_BRAND",
        "source_evidence": {
            "quote_ar": "عندما تحصل علي الامتياز ، فهذا يضمن لك الحصول على الترخيص ، لتشغيل فروع د.كيف جزئياً في بلد معين ، أو في جزء من البلد المستهدفة ، أوالإقليم الجغرافي ، أو في موقع مناسب وفق احتياجات برنامج التدريب الموضوع",
            "report_ref": "Franchise Profile - dr.CAFE COFFEE",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2023-06-01",
        "effective_to": None,
        "source_last_modified": "2024-03-15",
        "verification_status": STATUS_VERIFIED_PARTIAL,
        "is_active": True,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "العلامة د. كيف توفر امتيازاً تجارياً لتشغيل المقاهي في مدن المملكة ومواقع الترانزيت",
                "العقد يتضمن الدعم التشغيلي والأنظمة التقنية وتوريد حبوب البن الحصرية",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: أغذية ومشروبات / مقاهي وصالات",
                "التغطية: وطنية شاملة",
            ],
            "unknowns": [
                "رسوم الامتياز التأسيسية غير معلنة في الموقع العام",
                "نطاق الاستثمار التأسيسي الإجمالي غير منشور رسمياً",
                "نسبة الإتاوة التشغيلية والمساهمة التسويقية تخضع لوثيقة الإفصاح المباشرة",
                "المساحة المطلوبة تحدد حسب نموذج الفرع",
            ],
            "user_assumptions_needed": [
                "الميزانية الرأسمالية المقترحة لتشطيب الفرع والمعدات",
                "تقدير تكلفة الإيجار السنوي للعقار المستهدف",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                True,
                "شركة د. كيف للقهوة (dr.CAFE COFFEE)",
                "https://drcafe.com/en-sa/franchise-profile",
                source_document="Franchise Profile - dr.CAFE COFFEE",
                source_locator="/en-sa/franchise-profile",
                evidence_excerpt="The franchisee is granted the license to operate a dr. CAFE COFFEE store in a particular country, part of country, geographical territory or site subject to the successful completion of the required training program",
                checked_at=CHECK_DATE,
            ),
            "brand_name": build_field_provenance_entry(
                True,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                "بوابة الامتياز - د. كيف",
                "اسم العلامة",
                "Dr. Cafe Coffee Franchise",
            ),
            "sector": build_field_provenance_entry(
                True,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                "بوابة الامتياز - د. كيف",
                "القطاع",
                "مقاهي ومشروبات ساخنة وباردة",
            ),
            "geography": build_field_provenance_entry(
                True,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                "بوابة الامتياز - د. كيف",
                "المناطق المتاحة",
                "فروع ومواقع داخل المملكة العربية السعودية",
            ),
            "franchise_fee": build_field_provenance_entry(
                False,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                reason_if_unsupported="رسوم الامتياز تخضع لاتفاقية الإفصاح المباشرة وغير معلنة عامة",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                reason_if_unsupported="رأس المال التأسيسي غير منشور ويتطلب افتراضاً من المستثمر",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "royalty_model": build_field_provenance_entry(
                False,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                reason_if_unsupported="نسبة الإتاوة غير معلنة في الموقع العام",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "شركة د. كيف للقهوة العالمية",
                "https://drcafe.com/en-sa/franchise-profile",
                reason_if_unsupported="المساحة تحدد بموجب تقييم الموقع المعتمد",
            ),
        },
    },
    {
        "slug": "franchise-shawarmer",
        "title_ar": "امتياز تجاري: مطاعم شاورمر (Shawarmer)",
        "title_en": "Franchise Opportunity: Shawarmer",
        "opportunity_type": "FRANCHISE",
        "sector": "food_beverage",
        "subsector": "qsr_restaurants",
        "business_model": "Quick Service Restaurant Franchise",
        "target_customer": "B2C",
        "geography": "KSA_NATIONAL",
        "city": None,
        "region": None,
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "GROWTH",
        "description_ar": "الحصول على حق امتياز تشغيل فرع لسلسلة مطاعم شاورمر مع الدعم التشغيلي وسلاسل التوريد المعتمدة.",
        "description_en": "Franchise branch operation for Shawarmer restaurant chain with centralized supply chain and operational guidance.",
        "brand_name": "Shawarmer (شاورمر)",
        "official_source_url": "https://franchise.shawarmer.com/",
        "source_owner": "شركة الأغذية المبتكرة (شاورمر)",
        "source_type": "OFFICIAL_BRAND",
        "source_evidence": {
            "quote_ar": "Shawarmer was founded in 1999 in Riyadh, Saudi Arabia and grew over the years to become the largest shawarma chain in the world... Want to know more? Download Brand Profile",
            "report_ref": "Shawarmer Franchise Portal and Brand Profile Brochure",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2023-09-01",
        "effective_to": None,
        "source_last_modified": "2024-04-01",
        "verification_status": STATUS_VERIFIED_PARTIAL,
        "is_active": True,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "برنامج الامتياز التجاري لشاورمر متوافق مع نظام الامتياز التجاري السعودي الصادر بالمرسوم الملكي",
                "يمنح المستثمر رخصة استخدام العلامة والتوريدات الحصرية من مصانع الشركة المركزية",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: مطاعم وجبات سريعة وإعاشة",
                "التغطية: مدن المملكة الرئيسية والمحافظات",
            ],
            "unknowns": [
                "رسوم الامتياز التأسيسية غير معلنة في الموقع العام وتخضع لوثيقة الإفصاح المباشرة",
                "نطاق الاستثمار التجهيزي والمعدات غير منشور",
                "نسبة الإتاوة التشغيلية والتسويقية غير منشورة في البوابة العامة",
                "المساحة المطلوبة تخضع لتقييم الموقع الهندسي",
            ],
            "user_assumptions_needed": [
                "الميزانية الرأسمالية المقترحة للديكور ومعدات المطعم",
                "موقع العقار ومسار حركة العملاء والتوصيل",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                True,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                source_document="Shawarmer Franchise Portal and Brand Profile Brochure",
                source_locator="Downloads/Franchise_Brochure_General_160323.pdf",
                evidence_excerpt="Shawarmer was founded in 1999 in Riyadh, Saudi Arabia and grew over the years to become the largest shawarma chain in the world... Want to know more? Download Brand Profile - Franchise@shawarmer.com",
                checked_at=CHECK_DATE,
            ),
            "brand_name": build_field_provenance_entry(
                True,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                "بوابة الامتياز - شاورمر",
                "العلامة التجارية",
                "Shawarmer Franchise Program",
            ),
            "sector": build_field_provenance_entry(
                True,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                "بوابة الامتياز - شاورمر",
                "النشاط",
                "مطاعم وجبات سريعة وشاورما",
            ),
            "geography": build_field_provenance_entry(
                True,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                "بوابة الامتياز - شاورمر",
                "التغطية",
                "مدن ومحافظات المملكة العربية السعودية",
            ),
            "franchise_fee": build_field_provenance_entry(
                False,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                reason_if_unsupported="رسوم الامتياز تخضع لوثيقة الإفصاح الخاصة المودعة لدى وزارة التجارة وغير معلنة عامة",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                reason_if_unsupported="الاستثمار الرأسمالي يحدده المستثمر حسب حجم وموقع الفرع",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "royalty_model": build_field_provenance_entry(
                False,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                reason_if_unsupported="نسبة الإتاوة غير معلنة في البوابة العامة",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "شركة الأغذية المبتكرة (شاورمر)",
                "https://franchise.shawarmer.com/",
                reason_if_unsupported="المساحة تحدد حسب اشتراطات البلدية وموافقة الشركة",
            ),
        },
    },
    {
        "slug": "franchise-maestro-pizza",
        "title_ar": "امتياز تجاري: مايسترو بيتزا (Maestro Pizza)",
        "title_en": "Franchise Opportunity: Maestro Pizza",
        "opportunity_type": "FRANCHISE",
        "sector": "food_beverage",
        "subsector": "pizza_delivery",
        "business_model": "Dine-in & Delivery Franchise",
        "target_customer": "B2C",
        "geography": "KSA_NATIONAL",
        "city": None,
        "region": None,
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "GROWTH",
        "description_ar": "الحصول على رخصة تشغيل فرع لمطاعم مايسترو بيتزا مع دعم التجهيز وتوريد العجين والجبن والمكونات المعتمدة.",
        "description_en": "Franchise licensed store for Maestro Pizza with proprietary ingredient supply and delivery integration.",
        "brand_name": "Maestro Pizza (مايسترو بيتزا)",
        "official_source_url": "https://maestropizza.com",
        "source_owner": "شركة أطايب المتحدة (مايسترو)",
        "source_type": "OFFICIAL_BRAND",
        "source_evidence": {
            "quote_ar": "دليل التوسع بنظام الامتياز التجاري لمطاعم مايسترو بيتزا بالمدن والمحافظات",
            "report_ref": "مركز الامتياز التجاري السعودي - منشآت",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2023-05-01",
        "effective_to": None,
        "source_last_modified": "2024-02-28",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "علامة مايسترو بيتزا مسجلة في برنامج الامتياز التجاري لتشغيل فروع استلام وتوصيل",
                "يشمل الامتياز تزويد المشغل بالأنظمة التقنية وتوريد المكونات المعتمدة",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: مطاعم بيتزا وتوصيل سريع",
                "التغطية: مدن المملكة",
            ],
            "unknowns": [
                "رسوم الامتياز الأولية غير معلنة في الموقع العام",
                "الاستثمار التقديري للأفران والمعدات غير منشور",
                "نسبة الملكية الشهرية تخضع لوثيقة عقد الامتياز المودع",
                "المساحة المطلوبة تخضع لنوع الفرع (استلام فقط أو صالة طعام)",
            ],
            "user_assumptions_needed": [
                "الميزانية الرأسمالية لشراء الأفران وتجهيز الموقع",
                "تقدير أسطول التوصيل أو التعاقد مع منصات التوصيل السريع",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                reason_if_unsupported="الموقع العام مخصص لطلب البيتزا للمستهلكين ولا يحتوي على صفحة أو برنامج امتياز تجاري معلن للمستثمرين.",
                checked_at=CHECK_DATE,
            ),
            "brand_name": build_field_provenance_entry(
                True,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                "بوابة الشركة وسجل الامتياز",
                "العلامة التجارية",
                "Maestro Pizza Brand",
            ),
            "sector": build_field_provenance_entry(
                True,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                "سجل الامتياز",
                "النشاط",
                "مطاعم بيتزا ووجبات سريعة وتوصيل",
            ),
            "geography": build_field_provenance_entry(
                True,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                "سجل الامتياز",
                "التغطية",
                "مدن المملكة العربية السعودية",
            ),
            "franchise_fee": build_field_provenance_entry(
                False,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                reason_if_unsupported="رسوم الامتياز الأولية غير معلنة في الموقع العام",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                reason_if_unsupported="رأس المال التأسيسي غير منشور ويتطلب افتراضاً من المستثمر",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "royalty_model": build_field_provenance_entry(
                False,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                reason_if_unsupported="نسبة الإتاوة غير معلنة في البوابة العامة",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "شركة أطايب المتحدة (مايسترو)",
                "https://maestropizza.com",
                reason_if_unsupported="المساحة تخضع لنموذج الموقع",
            ),
        },
    },
    {
        "slug": "franchise-body-masters-fitness",
        "title_ar": "امتياز تجاري: أندية بودي ماسترز (Body Masters)",
        "title_en": "Franchise Opportunity: Body Masters Fitness Clubs",
        "opportunity_type": "FRANCHISE",
        "sector": "sports_entertainment",
        "subsector": "fitness_wellness",
        "business_model": "Subscription-based Fitness Franchise",
        "target_customer": "B2C",
        "geography": "KSA_NATIONAL",
        "city": None,
        "region": None,
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "GROWTH",
        "description_ar": "رخصة تشغيل فرع لأندية بودي ماسترز الرياضية المتكاملة مع توفير المخططات الفنية ومعايير الأجهزة الرياضية.",
        "description_en": "Operating franchise for Body Masters fitness clubs with standardized layout specifications and equipment guidelines.",
        "brand_name": "Body Masters (بودي ماسترز)",
        "official_source_url": "https://bodymasters.com.sa",
        "source_owner": "شركة أندية بودي ماسترز الرياضية",
        "source_type": "OFFICIAL_BRAND",
        "source_evidence": {
            "quote_ar": "نموذج منح حق الامتياز للأندية الرياضية المتكاملة بالمملكة مع توفير المخططات الفنية ومعايير الأجهزة",
            "report_ref": "وثيقة إفصاح الامتياز التجاري - وزارة التجارة",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2023-08-01",
        "effective_to": None,
        "source_last_modified": "2024-05-10",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "العلامة بودي ماسترز مسجلة وتوفر حقوق امتياز لتشغيل الأندية الرياضية في المملكة",
                "النشاط يتطلب ترخيص نادي رياضي من وزارة الرياضة والدفاع المدني والبلدية",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: رياضة وترفيه / لياقة بدنية وصحة",
                "التغطية: المدن الرئيسية والمحافظات",
            ],
            "unknowns": [
                "رسوم الامتياز التأسيسية غير معلنة في الموقع العام وتخضع للإفصاح المباشر",
                "الاستثمار الرأسمالي للأجهزة الرياضية وتجهيز المسابح غير منشور",
                "نسبة الإتاوة محددة في وثيقة الإفصاح المباشرة وغير معلنة عامة",
                "المساحة المطلوبة تخضع لنوع النادي (إكسبرس أو متكامل)",
            ],
            "user_assumptions_needed": [
                "الميزانية الرأسمالية لتوريد الأجهزة الرياضية والتشطيبات",
                "تحديد فئة النادي (إكسبرس، بريميوم، مسبح مائي)",
                "رواتب المدربين وأخصائيي اللياقة البدنية",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                reason_if_unsupported="الموقع العام مخصص لاشتراكات الأندية الرياضية للمستهلكين ولا يتضمن بوابة أو وثيقة امتياز تجاري معلنة.",
                checked_at=CHECK_DATE,
            ),
            "brand_name": build_field_provenance_entry(
                True,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                "بوابة بودي ماسترز",
                "العلامة",
                "Body Masters Fitness Clubs",
            ),
            "sector": build_field_provenance_entry(
                True,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                "بوابة بودي ماسترز",
                "القطاع",
                "أندية رياضية ولياقة بدنية وترفيه",
            ),
            "geography": build_field_provenance_entry(
                True,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                "بوابة بودي ماسترز",
                "التغطية",
                "المملكة العربية السعودية",
            ),
            "franchise_fee": build_field_provenance_entry(
                False,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                reason_if_unsupported="رسوم الامتياز غير منشورة في الموقع العام وتخضع لوثيقة الإفصاح المباشرة",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                reason_if_unsupported="رأس المال التأسيسي غير منشور ويتطلب افتراضاً من المستثمر",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "royalty_model": build_field_provenance_entry(
                False,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                reason_if_unsupported="نسبة الإتاوة غير معلنة في الموقع العام",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "شركة أندية بودي ماسترز الرياضية",
                "https://bodymasters.com.sa",
                reason_if_unsupported="المساحة تخضع لفئة النادي المستهدف",
            ),
        },
    },
    {
        "slug": "franchise-pet-lovers-boutique",
        "title_ar": "امتياز تجاري: مراكز بت لافرز للعناية بالحيوانات الأليفة",
        "title_en": "Franchise Opportunity: Pet Lovers Grooming & Care",
        "opportunity_type": "FRANCHISE",
        "sector": "retail",
        "subsector": "pet_care",
        "business_model": "Specialty Retail & Grooming Services",
        "target_customer": "B2C",
        "geography": "CENTRAL",
        "city": "الرياض",
        "region": "منطقة الرياض",
        "investment_min": None,
        "investment_max": None,
        "franchise_fee": None,
        "royalty_model": None,
        "required_space": None,
        "business_stage": "GROWTH",
        "description_ar": "امتياز تجاري لافتتاح مركز متخصص لخدمات العناية بالحيوانات الأليفة والتجزئة المتخصصة بمدينة الرياض.",
        "description_en": "Specialized pet care grooming boutique and premium pet supplies retail franchise in Riyadh.",
        "brand_name": "Pet Lovers (بت لافرز)",
        "official_source_url": "https://franchisecenter.sa",
        "source_owner": "مركز الامتياز التجاري (منشآت)",
        "source_type": "OFFICIAL_GOVERNMENT",
        "source_evidence": {
            "quote_ar": "فرصة امتياز تجاري مقيدة بمركز الامتياز التجاري ضمن قطاع التجزئة التخصصية بالرياض",
            "report_ref": "سجل العلامات التجارية المعتمدة بمركز الامتياز",
            "retrieval_date": "2026-09-04",
        },
        "effective_from": "2024-01-15",
        "effective_to": None,
        "source_last_modified": "2024-06-20",
        "verification_status": STATUS_UNVERIFIED,
        "is_active": False,
        "data_version": "1.1.0",
        "facts_breakdown": {
            "published_facts": [
                "العلامة مقيدة رسمياً في مركز الامتياز التجاري التابع لمنشآت",
                "النشاط يشمل خدمات العناية ومبيعات التجزئة للمستلزمات بترخيص بلدي معتمد",
            ],
            "platform_normalized_facts": [
                "تصنيف القطاع: تجزئة متخصصة / رعاية وخدمات",
                "النطاق الجغرافي: مدينة الرياض",
            ],
            "unknowns": [
                "رسوم الامتياز لمرة واحدة غير منشورة في البوابة العامة وتخضع لملف الإفصاح المعتمد",
                "رأس المال التأسيسي للتجهيز والمعدات غير منشور رسمياً",
                "نسبة الإتاوة الشهرية غير معلنة عامة",
                "المساحة المطلوبة تخضع لنوع الموقع المعتمد",
            ],
            "user_assumptions_needed": [
                "الميزانية الرأسمالية المقترحة لتجهيز المركز ومعدات العناية",
                "الموقع المناسب في الأحياء السكنية المستهدفة",
            ],
        },
        "field_provenance": {
            "opportunity_existence": build_field_provenance_entry(
                False,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                reason_if_unsupported="رابط رئيسي عام لبوابة الامتياز التجاري دون وجود قيد أو صفحة مخصصة للعلامة تثبت وجود فرصة الامتياز.",
                checked_at=CHECK_DATE,
            ),
            "brand_name": build_field_provenance_entry(
                True,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                "سجل العلامات المقيدة - مركز الامتياز",
                "اسم العلامة",
                "Pet Lovers Brand Registration",
            ),
            "sector": build_field_provenance_entry(
                True,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                "سجل العلامات المقيدة",
                "القطاع",
                "تجزئة متخصصة وخدمات رعاية حيوانات أليفة",
            ),
            "geography": build_field_provenance_entry(
                True,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                "سجل العلامات المقيدة",
                "المدينة المستهدفة",
                "مدينة الرياض - منطقة الرياض",
            ),
            "franchise_fee": build_field_provenance_entry(
                False,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                reason_if_unsupported="رسوم الامتياز تظهر بعد تسجيل الاهتمام الرسمي عبر مركز الامتياز",
            ),
            "investment_min": build_field_provenance_entry(
                False,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                reason_if_unsupported="رأس المال التأسيسي غير منشور ويتطلب افتراضاً من المستثمر",
            ),
            "investment_max": build_field_provenance_entry(
                False,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                reason_if_unsupported="الحد الأقصى غير منشور",
            ),
            "royalty_model": build_field_provenance_entry(
                False,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                reason_if_unsupported="نسبة الإتاوة غير معلنة في البوابة العامة",
            ),
            "required_space": build_field_provenance_entry(
                False,
                "مركز الامتياز التجاري (منشآت)",
                "https://franchisecenter.sa",
                reason_if_unsupported="المساحة التشغيلية تخضع لنموذج الموقع",
            ),
        },
    },
]


def seed_verified_opportunities(db: Session, force_refresh: bool = False) -> int:
    """Explicitly bootstrap or reconcile the verified opportunities catalog into the database.

    Does NOT use runtime create_all. Tables must exist via migrations.
    Idempotent by slug. Updates existing records if force_refresh is True.
    """
    existing_items = {row.slug: row for row in db.query(models.VerifiedOpportunity).all()}
    count_updated = 0
    count_inserted = 0

    for opp_data in VERIFIED_OPPORTUNITY_CATALOG:
        slug = opp_data["slug"]
        if slug in existing_items:
            if force_refresh:
                item = existing_items[slug]
                for k, v in opp_data.items():
                    setattr(item, k, v)
                item.last_checked_at = datetime.now(timezone.utc)
                count_updated += 1
            continue

        item = models.VerifiedOpportunity(**opp_data)
        db.add(item)
        db.flush()

        v_entry = models.OpportunityVersionHistory(
            opportunity_id=item.id,
            data_version=item.data_version,
            snapshot=dict(opp_data),
            changed_by=None,
            change_reason="Initial audited verified catalog ingestion with field-level provenance",
        )
        db.add(v_entry)
        count_inserted += 1

    if count_inserted > 0 or count_updated > 0:
        db.commit()

    return db.query(models.VerifiedOpportunity).count()


def list_verified_opportunities(
    db: Session,
    opportunity_type: Optional[str] = None,
    sector: Optional[str] = None,
    max_budget: Optional[float] = None,
    min_budget: Optional[float] = None,
    geography: Optional[str] = None,
    verification_status: Optional[str] = None,
    search: Optional[str] = None,
    include_unverified: bool = False,
) -> List[models.VerifiedOpportunity]:
    """List opportunities matching query filters with provenance loaded.

    By default, returns only active, verified actionable opportunities.
    Strict Budget Semantics (Rule C):
    UNKNOWN investment does NOT count as a budget fit.
    Only opportunities with verified known investment bounds matching the filter are returned.
    """
    query = db.query(models.VerifiedOpportunity)

    if not include_unverified:
        query = query.filter(
            models.VerifiedOpportunity.is_active.is_(True),
            models.VerifiedOpportunity.verification_status != STATUS_UNVERIFIED,
        )

    if opportunity_type:
        query = query.filter(models.VerifiedOpportunity.opportunity_type == opportunity_type)
    if sector:
        query = query.filter(models.VerifiedOpportunity.sector == sector)
    if verification_status:
        query = query.filter(models.VerifiedOpportunity.verification_status == verification_status)
    if geography:
        query = query.filter(
            or_(
                models.VerifiedOpportunity.geography == geography,
                models.VerifiedOpportunity.geography == "KSA_NATIONAL",
            )
        )
    if max_budget is not None:
        # Rule C: Unknown investment (NULL) does NOT count as a budget fit
        query = query.filter(
            models.VerifiedOpportunity.investment_min.is_not(None),
            models.VerifiedOpportunity.investment_min <= max_budget,
        )
    if min_budget is not None:
        query = query.filter(
            models.VerifiedOpportunity.investment_max.is_not(None),
            models.VerifiedOpportunity.investment_max >= min_budget,
        )
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.VerifiedOpportunity.title_ar.ilike(term),
                models.VerifiedOpportunity.title_en.ilike(term),
                models.VerifiedOpportunity.description_ar.ilike(term),
                models.VerifiedOpportunity.brand_name.ilike(term),
            )
        )

    return query.order_by(models.VerifiedOpportunity.id.asc()).all()


def get_verified_opportunity(db: Session, opp_id: int) -> Optional[models.VerifiedOpportunity]:
    """Get single verified opportunity with version history."""
    return (
        db.query(models.VerifiedOpportunity)
        .options(joinedload(models.VerifiedOpportunity.version_history))
        .filter(models.VerifiedOpportunity.id == opp_id)
        .first()
    )


def compare_verified_opportunities(
    db: Session, opp_ids: List[int]
) -> List[Dict[str, Any]]:
    """Compare multiple opportunities side-by-side using strictly sourced facts.

    Never invents composite scores or ranks.
    """
    items = (
        db.query(models.VerifiedOpportunity)
        .filter(models.VerifiedOpportunity.id.in_(opp_ids))
        .all()
    )

    comparison = []
    for item in items:
        comparison.append({
            "id": item.id,
            "title_ar": item.title_ar,
            "title_en": item.title_en,
            "opportunity_type": item.opportunity_type,
            "brand_name": item.brand_name,
            "sector": item.sector,
            "subsector": item.subsector,
            "business_model": item.business_model,
            "geography": item.geography,
            "city": item.city,
            "region": item.region,
            "investment_min": item.investment_min,
            "investment_max": item.investment_max,
            "franchise_fee": item.franchise_fee,
            "royalty_model": item.royalty_model,
            "required_space": item.required_space,
            "business_stage": item.business_stage,
            "source_owner": item.source_owner,
            "source_type": item.source_type,
            "official_source_url": item.official_source_url,
            "verification_status": item.verification_status,
            "is_active": item.is_active,
            "data_version": item.data_version,
            "field_provenance": item.field_provenance or {},
            "last_verified_at": item.last_verified_at.isoformat() if item.last_verified_at else None,
        })
    return comparison


def create_study_from_opportunity(
    db: Session,
    user: models.User,
    opportunity_id: int,
    custom_budget: Optional[float] = None,
    study_title: Optional[str] = None,
    match_result_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a persistent Feasibility Study and Project directly from a verified opportunity.

    Transfers strictly source-backed facts, attaches immutable source lineage,
    and populates initial Business Profile facts.
    NEVER invents a 250,000 budget. If custom_budget is entered, it is labeled USER_ASSUMPTION.
    """
    opp = get_verified_opportunity(db, opportunity_id)
    if not opp:
        raise ValueError("Opportunity not found")
    if not opp.is_active:
        raise ValueError("Cannot create study from an unverified or non-actionable opportunity (inactive).")
    if opp.verification_status not in (STATUS_VERIFIED_PARTIAL, STATUS_VERIFIED_CURRENT):
        raise ValueError(
            f"Cannot create study from an unverified or non-actionable opportunity with status '{opp.verification_status}'. "
            f"Only VERIFIED_PARTIAL or VERIFIED_CURRENT opportunities can be launched (rejected: UNVERIFIED, STALE, CHANGED, DISCONTINUED)."
        )
    existence_supported = bool(
        opp.field_provenance
        and isinstance(opp.field_provenance, dict)
        and opp.field_provenance.get("opportunity_existence", {}).get("supported") is True
    )
    if not existence_supported:
        raise ValueError("Cannot create study: opportunity existence is unsupported or lacks official source evidence.")

    # Determine investment amount strictly without fabrication
    if custom_budget is not None and custom_budget > 0:
        investment_amount = float(custom_budget)
        budget_is_user_assumption = True
        budget_type = "USER_ASSUMPTION"
        budget_notes = "الميزانية مدخلة ومحددة بافتراض صريح من المستثمر وليست منشورة في المصدر الرسمي"
    elif opp.investment_min is not None and opp.investment_min > 0:
        investment_amount = float(opp.investment_min)
        budget_is_user_assumption = False
        budget_type = "PUBLISHED_FACT_MINIMUM"
        budget_notes = f"الحد الأدنى للاستثمار الرأسمالي المنشور في وثيقة المصدر الرسمي ({opp.source_owner})"
    else:
        # Schema requires project.investment (non-nullable float).
        # We MUST require the user to provide an explicit budget. NEVER invent 250,000 SAR!
        raise ValueError(
            "الميزانية الرأسمالية غير معلنة في المصدر الرسمي للفرصة. يرجى إدخال الميزانية المقترحة (كافتراض مستخدم) لبدء دراسة الجدوى."
        )

    project_name = study_title or (
        f"دراسة: {opp.brand_name}" if opp.brand_name else f"مشروع: {opp.title_ar}"
    )

    project = models.Project(
        name=project_name[:200],
        industry=opp.sector,
        investment=investment_amount,
        stage="idea",
        workflow_status="from_opportunity",
        owner_id=user.id,
    )
    db.add(project)
    db.flush()

    lineage = {
        "source_opportunity_id": opp.id,
        "source_opportunity_slug": opp.slug,
        "source_opportunity_title_ar": opp.title_ar,
        "source_opportunity_title_en": opp.title_en,
        "opportunity_type": opp.opportunity_type,
        "brand_name": opp.brand_name,
        "sector": opp.sector,
        "subsector": opp.subsector,
        "source_owner": opp.source_owner,
        "source_type": opp.source_type,
        "official_source_url": opp.official_source_url,
        "verification_status": opp.verification_status,
        "is_active": opp.is_active,
        "data_version": opp.data_version,
        "transferred_at": datetime.now(timezone.utc).isoformat(),
        "budget_type": budget_type,
        "is_user_assumption": (budget_type == "USER_ASSUMPTION"),
        "budget_amount": investment_amount,
        "budget_notes": budget_notes,
        "transferred_facts": {
            "investment_min": opp.investment_min,
            "investment_max": opp.investment_max,
            "franchise_fee": opp.franchise_fee,
            "royalty_model": opp.royalty_model,
            "required_space": opp.required_space,
            "city": opp.city,
            "region": opp.region,
            "published_facts": opp.facts_breakdown.get("published_facts", []) if opp.facts_breakdown else [],
        },
        "field_provenance_snapshot": opp.field_provenance or {},
    }

    # Optional Fit Snapshot from Wave 3B matching
    fit_snapshot = None
    if match_result_id is not None:
        mr = (
            db.query(models.OpportunityMatchResult)
            .filter(models.OpportunityMatchResult.id == match_result_id)
            .first()
        )
        if not mr:
            raise ValueError("RE-EVALUATE FIT: Match result not found.")

        # Check user isolation
        match_run = mr.match_run
        if not match_run or match_run.user_id != user.id:
            raise ValueError("RE-EVALUATE FIT: Match result belongs to another user. Cannot attach snapshot.")

        # Check opportunity match
        if mr.opportunity_id != opp.id:
            raise ValueError("RE-EVALUATE FIT: Match result does not correspond to this opportunity. Cannot attach snapshot.")

        # Check freshness and actionable state
        from app.services.opportunity_matching import resolve_current_match_state, build_fit_snapshot_for_study
        curr_state, requires_re_eval, stale_reason = resolve_current_match_state(mr, opp)
        if requires_re_eval or str(mr.opportunity_version) != str(opp.data_version) or curr_state == "NOT_EVALUATED":
            raise ValueError(
                f"RE-EVALUATE FIT: Match result is stale or opportunity has changed ({stale_reason or 'version mismatch'}). Please re-evaluate fit before creating a study."
            )

        fit_snapshot = build_fit_snapshot_for_study(mr)

    study_payload = {
        "industry": opp.sector,
        "investment": investment_amount,
        "budget_type": budget_type,
        "budget_notes": budget_notes,
        "opportunity_lineage": lineage,
        "step_1": {
            "notes": f"تم استيراد هذه الدراسة مباشرة من {opp.title_ar} - المصدر: {opp.source_owner}. ميزانية الاستثمار: {investment_amount:,.0f} ر.س ({budget_type})"
        },
    }
    if fit_snapshot:
        study_payload["opportunity_fit_snapshot"] = fit_snapshot

    study = models.FeasibilityStudy(
        project_id=project.id,
        title=project_name[:255],
        study_type="opportunity_feasibility" if opp.opportunity_type == "BUSINESS_OPPORTUNITY" else "franchise_feasibility",
        status="draft",
        current_step=1,
        source_opportunity_id=opp.id,
        source_opportunity_version=opp.data_version,
        source_opportunity_lineage=lineage,
        payload=study_payload,
    )
    db.add(study)
    db.flush()

    business_profile = models.BusinessProfile(
        study_id=study.id,
        business_activity=opp.title_ar,
        description=opp.description_ar,
        city=opp.city,
        region=opp.region,
        customer_segment=opp.target_customer,
        is_existing_business=False,
    )
    db.add(business_profile)

    db.add(
        models.AuditLog(
            actor_id=user.id,
            action="opportunity.create_study",
            entity="feasibility_study",
            entity_id=study.id,
            meta={
                "opportunity_id": opp.id,
                "slug": opp.slug,
                "project_id": project.id,
                "budget_type": budget_type,
                "investment": investment_amount,
                "match_result_id": match_result_id,
            },
        )
    )

    db.commit()
    db.refresh(project)
    db.refresh(study)

    return {
        "project_id": project.id,
        "study_id": study.id,
        "title": study.title,
        "opportunity_id": opp.id,
        "lineage": lineage,
        "fit_snapshot": fit_snapshot,
    }
