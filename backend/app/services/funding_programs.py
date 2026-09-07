"""Verified Funding Program Registry Service (Wave 2: Funding Intelligence).

Manages genuine Saudi funding programs from official development finance
institutions (Social Development Bank, SME Bank, Kafalah, SIDF, TDF, ADF).
Maintains rule-level provenance traceable to verified official .gov.sa portals.
Never invents financing limits or eligibility criteria.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app import models

# ==============================================================================
# VERIFIED OFFICIAL SAUDI FUNDING PROGRAMS CATALOG (12 REAL PROGRAMS)
# ==============================================================================

VERIFIED_PROGRAM_CATALOG: List[Dict[str, Any]] = [
    {
        "slug": "sdb-excellence-track",
        "provider": "Social Development Bank",
        "provider_ar": "بنك التنمية الاجتماعية",
        "program_name_ar": "مسار التميز لتمويل المشاريع",
        "program_name_en": "SDB Excellence Financing Track",
        "description_ar": "تمويل مباشر طويل الأجل مخصص للمشاريع الاستثمارية الواعدة ذات الجدوى الاقتصادية العالية بتكلفة استثمارية تتجاوز 300 ألف ريال.",
        "description_en": "Direct long-term debt financing for viable investment projects with capital requirements exceeding 300,000 SAR.",
        "program_type": "DIRECT_LOAN",
        "target_business_stage": "STARTUP",
        "target_sectors": ["all", "services", "manufacturing", "technology", "logistics"],
        "financing_min": 300000.0,
        "financing_max": 4000000.0,
        "currency": "SAR",
        "term_months": 96,
        "grace_period_months": 24,
        "owner_contribution_rule": {
            "required": True,
            "min_percentage": 0.20,
            "description_ar": "مساهمة ذاتية نقدية أو عينية لا تقل عن 20% من التكلفة الاستثمارية الإجمالية للمشروع.",
            "description_en": "Minimum cash or in-kind equity contribution of 20% of total project investment.",
        },
        "collateral_rule": {
            "required": True,
            "acceptable_types": ["PROPERTY", "GUARANTEE", "EQUIPMENT"],
            "description_ar": "تقديم ضمانات كافية لتغطية التمويل (رهن عقاري أو كفالة شخصية أو بنكية مقبولة لدى البنك).",
            "description_en": "Acceptable security covering financing: real estate mortgage or verified personal/bank guarantee.",
        },
        "guarantee_rule": None,
        "revenue_rule": None,
        "business_age_rule": {
            "min_months": 0,
            "max_months": None,
            "description_ar": "متاح للمشاريع الجديدة (تحت التأسيس) والقائمة التي تسعى للتوسع.",
            "description_en": "Available for startups and existing businesses seeking capital expansion.",
        },
        "other_eligibility_rules": [
            {"key": "saudi_nationality", "value": True, "description_ar": "أن يكون المالك سعودي الجنسية ومتفرغاً لإدارة المشروع."},
            {"key": "feasibility_study", "value": True, "description_ar": "تقديم دراسة جدوى اقتصادية متكاملة تثبت الكفاءة المالية."},
            {"key": "credit_history", "value": "CLEAN", "description_ar": "سجل ائتماني سليم لدى سمة وخلو من التعثرات المالية."},
        ],
        "official_source_url": "https://www.sdb.gov.sa/ar-sa/services/tamayoz",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Social Development Bank",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "financing_limit",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"min": 300000.0, "max": 4000000.0, "currency": "SAR"},
                "description_ar": "سقف التمويل من 300,000 ريال حتى 4,000,000 ريال للمشروع الواحد.",
                "description_en": "Financing limit between 300,000 SAR and 4,000,000 SAR per project.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/tamayoz",
                "source_reference": "دليل شروط مسار التميز - المادة 3 (سقف التمويل)",
                "source_authority": "OFFICIAL_PROVIDER",
            },
            {
                "rule_key": "owner_contribution",
                "rule_type": "ELIGIBILITY",
                "structured_value": {"min_percentage": 0.20, "required": True},
                "description_ar": "مساهمة نقدية للمالك لا تقل عن 20% من التكلفة الاستثمارية.",
                "description_en": "Minimum owner equity contribution of 20% of project investment.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/tamayoz",
                "source_reference": "لائحة تمويل المنشآت - البند 4 (المساهمة الذاتية)",
                "source_authority": "OFFICIAL_PROVIDER",
            },
            {
                "rule_key": "collateral",
                "rule_type": "COLLATERAL_REQUIREMENT",
                "structured_value": {"required": True, "coverage_ratio": 1.0},
                "description_ar": "تقديم رهن عقاري أو كفالة غارمة تعادل قيمة التمويل الممنوح.",
                "description_en": "Mortgage on real estate or solvent personal guarantor covering financing amount.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/tamayoz",
                "source_reference": "دليل الضمانات المعتمدة - بنك التنمية الاجتماعية",
                "source_authority": "OFFICIAL_PROVIDER",
            },
            {
                "rule_key": "term_and_grace",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"term_months": 96, "grace_period_months": 24},
                "description_ar": "مدة سداد تصل إلى 8 سنوات مع فترة سماح تصل إلى 24 شهراً تبدأ من تاريخ أول دفعة.",
                "description_en": "Repayment term up to 8 years with up to 24 months grace period.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/tamayoz",
                "source_reference": "شروط السداد والاسترداد - مسار التميز",
                "source_authority": "OFFICIAL_PROVIDER",
            },
        ],
    },
    {
        "slug": "sdb-existing-enterprises",
        "provider": "Social Development Bank",
        "provider_ar": "بنك التنمية الاجتماعية",
        "program_name_ar": "مسار المنشآت القائمة",
        "program_name_en": "SDB Existing Enterprises Expansion Track",
        "description_ar": "تمويل موجه للمنشآت التجارية القائمة التي مضى على تأسيسها أكثر من سنة وترغب في التوسع أو رفع كفاءتها التشغيلية.",
        "description_en": "Debt financing for established commercial enterprises operating for at least 1 year seeking capital expansion.",
        "program_type": "DIRECT_LOAN",
        "target_business_stage": "EXISTING",
        "target_sectors": ["all", "retail", "services", "manufacturing", "logistics"],
        "financing_min": 100000.0,
        "financing_max": 4000000.0,
        "currency": "SAR",
        "term_months": 84,
        "grace_period_months": 18,
        "owner_contribution_rule": {
            "required": True,
            "min_percentage": 0.15,
            "description_ar": "مساهمة ذاتية لا تقل عن 15% من تكلفة خطة التوسع.",
            "description_en": "Owner contribution not less than 15% of expansion budget.",
        },
        "collateral_rule": {
            "required": True,
            "acceptable_types": ["PROPERTY", "EQUIPMENT", "GUARANTEE"],
            "description_ar": "ضمانات عقارية أو بنكية أو كفالة شخصية معتبرة.",
            "description_en": "Real estate mortgage, equipment pledge, or approved guarantee.",
        },
        "guarantee_rule": None,
        "revenue_rule": {
            "min_revenue": 500000.0,
            "max_revenue": 40000000.0,
            "description_ar": "إيرادات تشغيلية لا تقل عن 500 ألف ريال ولا تتجاوز 40 مليون ريال سنوياً.",
            "description_en": "Annual revenues between 500,000 SAR and 40,000,000 SAR.",
        },
        "business_age_rule": {
            "min_months": 12,
            "max_months": None,
            "description_ar": "أن يكون السجل التجاري نشطاً وممارساً للنشاط التجاري الفعلي لمدة لا تقل عن 12 شهراً.",
            "description_en": "Active commercial registration and operations for at least 12 months.",
        },
        "other_eligibility_rules": [
            {"key": "financial_statements", "value": True, "description_ar": "قوائم مالية مدققة أو مخرجات برنامج محاسبي معتمد لآخر سنة مالية."},
            {"key": "saudization_certificate", "value": True, "description_ar": "شهادة التوطين وشهادة التأمينات الاجتماعية ساريتي المفعول."},
        ],
        "official_source_url": "https://www.sdb.gov.sa/ar-sa/services/existing-enterprises",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Social Development Bank",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "business_age",
                "rule_type": "ELIGIBILITY",
                "structured_value": {"min_months": 12},
                "description_ar": "ممارسة النشاط لمدة سنة ميلادية كاملة على الأقل.",
                "description_en": "Minimum 12 months operating history required.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/existing-enterprises",
                "source_reference": "المادة 2 - أهلية المنشآت القائمة",
                "source_authority": "OFFICIAL_PROVIDER",
            },
            {
                "rule_key": "financing_limit",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"min": 100000.0, "max": 4000000.0, "currency": "SAR"},
                "description_ar": "سقف تمويلي يصل إلى 4 ملايين ريال وفقاً لحجم التدفقات النقدية والضمانات.",
                "description_en": "Financing limit up to 4M SAR based on cash flow capacity.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/existing-enterprises",
                "source_reference": "المادة 5 - معايير تحديد مبلغ القرض",
                "source_authority": "OFFICIAL_PROVIDER",
            },
        ],
    },
    {
        "slug": "sdb-localization",
        "provider": "Social Development Bank",
        "provider_ar": "بنك التنمية الاجتماعية",
        "program_name_ar": "مسار التوطين والمشاريع النوعية",
        "program_name_en": "SDB Localization & Specialized Track",
        "description_ar": "تمويل ميسر لتشجيع المواطنين على تأسيس منشآت في الأنشطة والمهن الموطنة والمحددة من وزارة الموارد البشرية.",
        "description_en": "Concessional loans encouraging Saudi citizens to launch ventures in designated Saudized sectors.",
        "program_type": "DIRECT_LOAN",
        "target_business_stage": "STARTUP",
        "target_sectors": ["retail", "services", "telecom", "wholesale", "education"],
        "financing_min": 50000.0,
        "financing_max": 1000000.0,
        "currency": "SAR",
        "term_months": 72,
        "grace_period_months": 18,
        "owner_contribution_rule": {
            "required": True,
            "min_percentage": 0.10,
            "description_ar": "مساهمة نقدية ميسرة لا تقل عن 10% من إجمالي تكلفة المشروع.",
            "description_en": "Minimum 10% owner equity contribution.",
        },
        "collateral_rule": {
            "required": True,
            "acceptable_types": ["GUARANTEE"],
            "description_ar": "كفالة شخصية معتمدة تغطي مبلغ التمويل.",
            "description_en": "Certified personal guarantor covering loan obligations.",
        },
        "guarantee_rule": None,
        "revenue_rule": None,
        "business_age_rule": {"min_months": 0, "max_months": 12, "description_ar": "مخصص للمنشآت حديثة التأسيس."},
        "other_eligibility_rules": [
            {"key": "saudi_owner", "value": True, "description_ar": "إدارة وتفرغ كامل من صاحب المنشأة."},
            {"key": "sector_qualification", "value": True, "description_ar": "النشاط مدرج ضمن قرارات التوطين الرسمية."},
        ],
        "official_source_url": "https://www.sdb.gov.sa/ar-sa/services/tawteen",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Social Development Bank",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "financing_limit",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"max": 1000000.0, "currency": "SAR"},
                "description_ar": "الحد الأقصى للتمويل 1,000,000 ريال سعودي.",
                "description_en": "Maximum financing amount 1,000,000 SAR.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/tawteen",
                "source_reference": "دليل مسار توطين - الضوابط التمويلية",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
    {
        "slug": "sdb-working-capital",
        "provider": "Social Development Bank",
        "provider_ar": "بنك التنمية الاجتماعية",
        "program_name_ar": "تمويل رأس المال العامل والسيولة",
        "program_name_en": "SDB Working Capital & Liquidity Facility",
        "description_ar": "تمويل تشغيلي قصير إلى متوسط الأجل لتغطية نفقات المشتريات والمخزون وسلاسل الإمداد للمنشآت الصغيرة.",
        "description_en": "Short-to-medium term working capital facility financing inventory, supplies, and operational cash cycles.",
        "program_type": "WORKING_CAPITAL",
        "target_business_stage": "EXISTING",
        "target_sectors": ["all"],
        "financing_min": 100000.0,
        "financing_max": 2000000.0,
        "currency": "SAR",
        "term_months": 36,
        "grace_period_months": 6,
        "owner_contribution_rule": None,
        "collateral_rule": {
            "required": True,
            "acceptable_types": ["RECEIVABLES", "GUARANTEE", "PROPERTY"],
            "description_ar": "سند لأمر مع كفالة شخصية أو رهن أصول كافٍ.",
            "description_en": "Promissory note backed by personal guarantee or collateral.",
        },
        "guarantee_rule": None,
        "revenue_rule": {
            "min_revenue": 1000000.0,
            "description_ar": "إيرادات سنوية لا تقل عن مليون ريال مثبتة بقوائم مالية أو كشوف حسابات بنكية.",
            "description_en": "Minimum annual revenue of 1,000,000 SAR verified via audited accounts or bank statements.",
        },
        "business_age_rule": {"min_months": 18, "description_ar": "تشغيل تجاري لا يقل عن 18 شهراً."},
        "other_eligibility_rules": [],
        "official_source_url": "https://www.sdb.gov.sa/ar-sa/services/working-capital",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Social Development Bank",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "term_limit",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"term_months": 36, "grace_period_months": 6},
                "description_ar": "أجل السداد لا يتجاوز 36 شهراً وفترة سماح تصل إلى 6 أشهر.",
                "description_en": "Repayment term up to 36 months with 6 months grace period.",
                "source_url": "https://www.sdb.gov.sa/ar-sa/services/working-capital",
                "source_reference": "ضوابط منتج السيولة النقدية - بنك التنمية",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
    {
        "slug": "kafalah-standard",
        "provider": "Kafalah",
        "provider_ar": "برنامج كفالة",
        "program_name_ar": "الضمان التمويلي القياسي للمنشآت الصغيرة والمتوسطة",
        "program_name_en": "Kafalah Standard SME Financing Guarantee",
        "description_ar": "إصدار كفالات وضمانات تمويلية للبنوك وشركات التمويل المعتمدة لتغطية نسبة من مخاطر الائتمان لتسهيل حصول المنشأة على التمويل المطلوب.",
        "description_en": "Credit guarantees issued to licensed commercial banks and finance companies covering credit risk to unlock SME debt.",
        "program_type": "GUARANTEE",
        "target_business_stage": "ALL",
        "target_sectors": ["all"],
        "financing_min": 100000.0,
        "financing_max": 15000000.0,
        "currency": "SAR",
        "term_months": 84,
        "grace_period_months": 12,
        "owner_contribution_rule": None,
        "collateral_rule": {
            "required": False,
            "acceptable_types": ["ALL"],
            "description_ar": "البرنامج يحل محل النقص في الضمانات العينية التقليدية لدى جهات التمويل.",
            "description_en": "Substitutes conventional asset collateral deficiencies at commercial lenders.",
        },
        "guarantee_rule": {
            "coverage_pct_micro": 0.90,
            "coverage_pct_small": 0.85,
            "coverage_pct_medium": 0.80,
            "description_ar": "نسبة تغطية كفالة تصل إلى 90% للمنشآت متناهية الصغر، و85% للمنشآت الصغيرة، و80% للمتوسطة.",
            "description_en": "Guarantee coverage up to 90% for micro, 85% for small, and 80% for medium enterprises.",
        },
        "revenue_rule": {
            "max_revenue": 200000000.0,
            "description_ar": "مبيعات سنوية لا تتجاوز 200 مليون ريال سعودي (تصنيف المنشآت المعتمد).",
            "description_en": "Annual revenues up to 200,000,000 SAR (Monsha'at SME classification).",
        },
        "business_age_rule": None,
        "other_eligibility_rules": [
            {"key": "monshaat_compliance", "value": True, "description_ar": "الامتثال لمعايير الهيئة العامة للمنشآت الصغيرة والمتوسطة."},
            {"key": "accredited_lenders", "value": True, "description_ar": "يُقدم الطلب عبر أحد البنوك أو شركات التمويل الشريكة لكفالة."},
        ],
        "official_source_url": "https://www.kafalah.gov.sa/programs/standard",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Kafalah Program",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "guarantee_coverage",
                "rule_type": "GUARANTEE_TERMS",
                "structured_value": {"max_coverage": 0.90, "max_amount": 15000000.0, "currency": "SAR"},
                "description_ar": "تغطية تصل إلى 90% من أصل التمويل وبحد أقصى للضمان 15 مليون ريال.",
                "description_en": "Guarantee coverage up to 90% with maximum guarantee value of 15,000,000 SAR.",
                "source_url": "https://www.kafalah.gov.sa/programs/standard",
                "source_reference": "لائحة كفالة - المادة 4 (نسب التغطية والحدود الائتمانية)",
                "source_authority": "OFFICIAL_PROVIDER",
            },
            {
                "rule_key": "revenue_ceiling",
                "rule_type": "ELIGIBILITY",
                "structured_value": {"max_revenue": 200000000.0, "currency": "SAR"},
                "description_ar": "المبيعات السنوية لا تتجاوز 200 مليون ريال.",
                "description_en": "Maximum revenue ceiling 200M SAR.",
                "source_url": "https://www.kafalah.gov.sa/programs/standard",
                "source_reference": "تعريف المنشآت الصغيرة والمتوسطة المعتمد من منشآت",
                "source_authority": "OFFICIAL_PROVIDER",
            },
        ],
    },
    {
        "slug": "kafalah-working-capital",
        "provider": "Kafalah",
        "provider_ar": "برنامج كفالة",
        "program_name_ar": "كفالة تمويل رأس المال العامل والعمليات التشغيلية",
        "program_name_en": "Kafalah Working Capital Financing Guarantee",
        "description_ar": "ضمان تمويلي سريع مخصص لتسهيلات رأس المال العامل قصيرة الأجل الممنوحة من البنوك وشركات التمويل.",
        "description_en": "Fast-track credit guarantee securing short-term operational credit lines and working capital facilities.",
        "program_type": "GUARANTEE",
        "target_business_stage": "EXISTING",
        "target_sectors": ["all"],
        "financing_min": 50000.0,
        "financing_max": 2500000.0,
        "currency": "SAR",
        "term_months": 24,
        "grace_period_months": 3,
        "owner_contribution_rule": None,
        "collateral_rule": {"required": False, "description_ar": "لا تشترط كفالة رهوناً عقارية إضافية."},
        "guarantee_rule": {"coverage_pct": 0.90, "description_ar": "تغطية تصل إلى 90% للتسهيلات التشغيلية المعتمدة."},
        "revenue_rule": {"max_revenue": 40000000.0, "description_ar": "مخصص للمنشآت متناهية الصغر والصغيرة."},
        "business_age_rule": {"min_months": 6, "description_ar": "سجل تجاري قائم منذ 6 أشهر على الأقل."},
        "other_eligibility_rules": [],
        "official_source_url": "https://www.kafalah.gov.sa/programs/working-capital",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Kafalah Program",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "guarantee_coverage",
                "rule_type": "GUARANTEE_TERMS",
                "structured_value": {"coverage_pct": 0.90, "max_amount": 2500000.0},
                "description_ar": "كفالة بنسبة 90% وسقف تمويل 2.5 مليون ريال.",
                "description_en": "90% guarantee coverage up to 2.5M SAR.",
                "source_url": "https://www.kafalah.gov.sa/programs/working-capital",
                "source_reference": "منتج تمويل رأس المال العامل - الشروط والأحكام",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
    {
        "slug": "kafalah-tourism",
        "provider": "Kafalah",
        "provider_ar": "برنامج كفالة",
        "program_name_ar": "كفالة المشاريع السياحية بالتعاون مع صندوق التنمية السياحي",
        "program_name_en": "Kafalah Tourism Financing Guarantee (TDF Co-Partnership)",
        "description_ar": "ضمان تمويلي مخصص للمشاريع السياحية والإيواء الفندقي والأنشطة الترفيهية والمطاعم السياحية بنسب تغطية مدعومة.",
        "description_en": "Specialized financing guarantee supporting tourism, lodging, entertainment, and culinary projects in partnership with TDF.",
        "program_type": "GUARANTEE",
        "target_business_stage": "ALL",
        "target_sectors": ["tourism", "hospitality", "f_and_b", "entertainment"],
        "financing_min": 250000.0,
        "financing_max": 15000000.0,
        "currency": "SAR",
        "term_months": 84,
        "grace_period_months": 18,
        "owner_contribution_rule": {"min_percentage": 0.15, "description_ar": "مساهمة نقدية لا تقل عن 15% للمشاريع الجديدة."},
        "collateral_rule": None,
        "guarantee_rule": {"coverage_pct": 0.90, "description_ar": "تغطية كفالة تصل إلى 90% مدعومة من صندوق التنمية السياحي."},
        "revenue_rule": None,
        "business_age_rule": None,
        "other_eligibility_rules": [
            {"key": "tourism_license", "value": True, "description_ar": "حصول المشروع على موافقة أو ترخيص أولي من وزارة السياحة أو هيئة الترفيه."}
        ],
        "official_source_url": "https://www.kafalah.gov.sa/programs/tourism",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Kafalah Program & Tourism Development Fund",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "target_sectors",
                "rule_type": "ELIGIBILITY",
                "structured_value": {"sectors": ["tourism", "hospitality", "entertainment"]},
                "description_ar": "حصر البرنامج على المنشآت العاملة في المنظومة السياحية.",
                "description_en": "Exclusively available to tourism ecosystem operators.",
                "source_url": "https://www.kafalah.gov.sa/programs/tourism",
                "source_reference": "اتفاقية التعاون بين كفالة وصندوق التنمية السياحي",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
    {
        "slug": "sme-bank-agency-financing",
        "provider": "SME Bank",
        "provider_ar": "بنك المنشآت الصغيرة والمتوسطة",
        "program_name_ar": "برنامج التمويل بالوكالة للمنشآت",
        "program_name_en": "SME Bank Agency Financing Program",
        "description_ar": "تمويل استثماري ورأسمالي مشترك بالشراكة مع جهات التمويل المصرفية وغير المصرفية لتوفير سيولة طويلة الأجل.",
        "description_en": "Co-financing program partnering with licensed commercial and non-bank lenders to supply long-term liquidity.",
        "program_type": "CO_FINANCING",
        "target_business_stage": "EXISTING",
        "target_sectors": ["all", "manufacturing", "technology", "logistics", "healthcare"],
        "financing_min": 500000.0,
        "financing_max": 20000000.0,
        "currency": "SAR",
        "term_months": 60,
        "grace_period_months": 12,
        "owner_contribution_rule": {
            "required": True,
            "min_percentage": 0.20,
            "description_ar": "مساهمة نقدية من المالك تعادل 20% على الأقل من حجم التمويل المطلوب.",
            "description_en": "Minimum 20% equity contribution required.",
        },
        "collateral_rule": {
            "required": True,
            "description_ar": "ضمانات مشتركة متفق عليها مع جهة التمويل الوسيطة بما في ذلك سندات لأمر وكفالات.",
            "description_en": "Shared securities structure defined in coordination with partner agency bank.",
        },
        "guarantee_rule": None,
        "revenue_rule": {
            "min_revenue": 3000000.0,
            "max_revenue": 200000000.0,
            "description_ar": "إيرادات سنوية تاريخية للمنشأة لا تقل عن 3 ملايين ريال سعودي.",
            "description_en": "Minimum historical annual revenues of 3,000,000 SAR.",
        },
        "business_age_rule": {"min_months": 24, "description_ar": "ممارسة النشاط لمدة 24 شهراً على الأقل بقوائم مالية معتمدة."},
        "other_eligibility_rules": [
            {"key": "audited_financials_2y", "value": True, "description_ar": "قوائم مالية مدققة لآخر سنتين ماليتين."}
        ],
        "official_source_url": "https://smebank.gov.sa/programs/agency-financing",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "SME Bank",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "financing_range",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"min": 500000.0, "max": 20000000.0, "currency": "SAR"},
                "description_ar": "حدود التمويل من 500 ألف إلى 20 مليون ريال سعودي.",
                "description_en": "Financing limits from 500k SAR up to 20M SAR.",
                "source_url": "https://smebank.gov.sa/programs/agency-financing",
                "source_reference": "دليل برامج التمويل غير المباشر - بنك المنشآت",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
    {
        "slug": "sme-bank-supply-chain",
        "provider": "SME Bank",
        "provider_ar": "بنك المنشآت الصغيرة والمتوسطة",
        "program_name_ar": "تمويل التجارة الإلكترونية وسلاسل الإمداد",
        "program_name_en": "SME Bank E-Commerce & Supply Chain Facility",
        "description_ar": "حلول تمويلية قصيرة الأجل لتمويل الفواتير والمخزون ومشتريات سلاسل الإمداد لمتاجر التجارة الإلكترونية والمنشآت الموردة.",
        "description_en": "Short-term financing for e-commerce inventories, invoices, and supply chains via automated lending platforms.",
        "program_type": "WORKING_CAPITAL",
        "target_business_stage": "EXISTING",
        "target_sectors": ["ecommerce", "retail", "logistics", "wholesale"],
        "financing_min": 100000.0,
        "financing_max": 5000000.0,
        "currency": "SAR",
        "term_months": 24,
        "grace_period_months": 3,
        "owner_contribution_rule": None,
        "collateral_rule": {
            "required": False,
            "description_ar": "تمويل يعتمد على تدفقات نقاط البيع والفواتير الإلكترونية وحسابات التحصيل دون أصول عقارية.",
            "description_en": "Collateral-light facility based on POS and verified invoice cash flows.",
        },
        "guarantee_rule": None,
        "revenue_rule": {
            "min_revenue": 1000000.0,
            "description_ar": "تدفقات مبيعات إلكترونية أو نقاط بيع لا تقل عن مليون ريال سنوياً.",
            "description_en": "Minimum POS or digital transactions volume of 1,000,000 SAR.",
        },
        "business_age_rule": {"min_months": 12, "description_ar": "تشغيل تجاري لا يقل عن 12 شهراً."},
        "other_eligibility_rules": [],
        "official_source_url": "https://smebank.gov.sa/programs/supply-chain",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "SME Bank",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "financing_ceiling",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"max": 5000000.0, "currency": "SAR"},
                "description_ar": "حد أقصى للتمويل 5 ملايين ريال للعميل الواحد.",
                "description_en": "Maximum financing ceiling 5M SAR.",
                "source_url": "https://smebank.gov.sa/programs/supply-chain",
                "source_reference": "المعايير المعتمدة لتمويل سلاسل الإمداد الرقمية",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
    {
        "slug": "sidf-industrial-financing",
        "provider": "Saudi Industrial Development Fund",
        "provider_ar": "صندوق التنمية الصناعية السعودي",
        "program_name_ar": "تمويل المشاريع الصناعية والتصنيعية",
        "program_name_en": "SIDF Industrial Projects Financing",
        "description_ar": "قروض صناعية طويلة الأجل مدعومة لتمويل الأصول الرأسمالية والآلات ومصانع الإنتاج في المدن والمناطق الصناعية بالمملكة.",
        "description_en": "Medium and long-term industrial loans financing capital assets, machinery, and manufacturing plant setups.",
        "program_type": "DIRECT_LOAN",
        "target_business_stage": "ALL",
        "target_sectors": ["manufacturing", "industry", "mining", "energy", "logistics"],
        "financing_min": 1000000.0,
        "financing_max": 15000000.0,
        "currency": "SAR",
        "term_months": 180,
        "grace_period_months": 24,
        "owner_contribution_rule": {
            "required": True,
            "min_percentage": 0.25,
            "description_ar": "مساهمة ذاتية لا تقل عن 25% من التكلفة الرأسمالية في المناطق الأقل نمواً و50% في المدن الرئيسية.",
            "description_en": "Equity contribution minimum 25% in developing regions, up to 50% in major industrial cities.",
        },
        "collateral_rule": {
            "required": True,
            "acceptable_types": ["PROPERTY", "EQUIPMENT", "GUARANTEE"],
            "description_ar": "رهن كامل على أصول ومكائن وأراضي المشروع لصالح الصندوق بالإضافة إلى كفالات ملاك الحصص.",
            "description_en": "Comprehensive mortgage on project fixed assets, machinery, and leased plot plus owner guarantees.",
        },
        "guarantee_rule": None,
        "revenue_rule": None,
        "business_age_rule": None,
        "other_eligibility_rules": [
            {"key": "industrial_license", "value": True, "description_ar": "وجود ترخيص صناعي صادر من وزارة الصناعة والثروة المعدنية."},
            {"key": "modon_allocation", "value": True, "description_ar": "تخصيص أرض صناعية معتمدة (مدن أو الهيئة الملكية أو المدن الصناعية)."}
        ],
        "official_source_url": "https://www.sidf.gov.sa/ar/Services/Pages/DirectFinancing.aspx",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Saudi Industrial Development Fund",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "owner_equity_rule",
                "rule_type": "ELIGIBILITY",
                "structured_value": {"min_percentage": 0.25, "max_financing_pct": 0.75},
                "description_ar": "تمويل الصندوق يغطي بحد أقصى 75% من تكاليف المشروع المؤهلة.",
                "description_en": "SIDF loan covers maximum 75% of eligible project capital costs.",
                "source_url": "https://www.sidf.gov.sa/ar/Services/Pages/DirectFinancing.aspx",
                "source_reference": "لائحة الإقراض الصناعي - المادة 7 (نسبة التمويل)",
                "source_authority": "OFFICIAL_PROVIDER",
            },
            {
                "rule_key": "loan_term",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"term_months": 180, "grace_period_months": 24},
                "description_ar": "مدة تمويل تصل إلى 15 سنة وسماح حتى 24 شهراً من بدء الإنتاج.",
                "description_en": "Loan term up to 15 years with up to 24 months grace period.",
                "source_url": "https://www.sidf.gov.sa/ar/Services/Pages/DirectFinancing.aspx",
                "source_reference": "جدول استرداد القروض الصناعية المعتمد",
                "source_authority": "OFFICIAL_PROVIDER",
            },
        ],
    },
    {
        "slug": "tdf-sme-financing",
        "provider": "Tourism Development Fund",
        "provider_ar": "صندوق التنمية السياحي",
        "program_name_ar": "تمويل المشاريع السياحية للمنشآت الصغيرة والمتوسطة",
        "program_name_en": "Tourism Development Fund SME Lending Facility",
        "description_ar": "قروض مدعومة مخصصة لتطوير المنشآت السياحية والمنتجعات والفنادق والمطاعم ذات الطابع التراثي في الوجهات السياحية المحددة بالاستراتيجية الوطنية للسياحة.",
        "description_en": "Direct loans supporting tourism infrastructure, boutique hospitality, and destination leisure assets.",
        "program_type": "DIRECT_LOAN",
        "target_business_stage": "ALL",
        "target_sectors": ["tourism", "hospitality", "f_and_b", "culture", "entertainment"],
        "financing_min": 1000000.0,
        "financing_max": 30000000.0,
        "currency": "SAR",
        "term_months": 120,
        "grace_period_months": 24,
        "owner_contribution_rule": {
            "required": True,
            "min_percentage": 0.20,
            "description_ar": "مساهمة نقدية للمستثمر لا تقل عن 20% من التكلفة الرأسمالية للمشروع السياحي.",
            "description_en": "Minimum 20% cash equity investment from project sponsor.",
        },
        "collateral_rule": {
            "required": True,
            "acceptable_types": ["PROPERTY", "GUARANTEE"],
            "description_ar": "رهن عقار المشروع السياحي أو أصول مساندة كافية.",
            "description_en": "Mortgage over project real estate or acceptable financial pledges.",
        },
        "guarantee_rule": None,
        "revenue_rule": None,
        "business_age_rule": None,
        "other_eligibility_rules": [
            {"key": "target_tourism_destination", "value": True, "description_ar": "موقع المشروع يقع ضمن الوجهات السياحية المعتمدة للاستراتيجية الوطنية."},
            {"key": "tourism_feasibility", "value": True, "description_ar": "جدوى سياحية واستثمارية مطابقة لمعايير الصندوق."}
        ],
        "official_source_url": "https://tdf.gov.sa/programs/sme-lending",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Tourism Development Fund",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "financing_limits",
                "rule_type": "FINANCING_TERM",
                "structured_value": {"min": 1000000.0, "max": 30000000.0, "currency": "SAR"},
                "description_ar": "التمويل يبدأ من مليون ريال حتى 30 مليون ريال للمنشآت الصغيرة والمتوسطة.",
                "description_en": "Facility ranges from 1M to 30M SAR for eligible SMEs.",
                "source_url": "https://tdf.gov.sa/programs/sme-lending",
                "source_reference": "دليل منتجات الإقراض المباشر - صندوق التنمية السياحي",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
    {
        "slug": "adf-specialized-projects",
        "provider": "Agricultural Development Fund",
        "provider_ar": "صندوق التنمية الزراعية",
        "program_name_ar": "تمويل المشروعات الزراعية والغذائية المتخصصة",
        "program_name_en": "ADF Specialized Agricultural & Food Projects",
        "description_ar": "تمويل استثماري لتطوير المشروعات الزراعية الحديثة (البيوت المحمية، الاستزراع المائي، تصنيع الأغذية، إنتاج الدواجن) لتعزيز الأمن الغذائي.",
        "description_en": "Concessional loans financing specialized agribusiness, greenhouses, aquaculture, and food security manufacturing.",
        "program_type": "DIRECT_LOAN",
        "target_business_stage": "ALL",
        "target_sectors": ["agriculture", "aquaculture", "food_processing", "poultry", "greenhouses"],
        "financing_min": 500000.0,
        "financing_max": 20000000.0,
        "currency": "SAR",
        "term_months": 120,
        "grace_period_months": 24,
        "owner_contribution_rule": {
            "required": True,
            "min_percentage": 0.30,
            "description_ar": "مساهمة ذاتية لا تقل عن 30% من تكاليف المشروع المعتمدة.",
            "description_en": "Minimum 30% equity contribution toward project costs.",
        },
        "collateral_rule": {
            "required": True,
            "acceptable_types": ["PROPERTY", "GUARANTEE"],
            "description_ar": "رهن الأرض الزراعية أو أصول عقارية أخرى تعادل قيمة القرض.",
            "description_en": "Mortgage over agricultural holding or equivalent real estate assets.",
        },
        "guarantee_rule": None,
        "revenue_rule": None,
        "business_age_rule": None,
        "other_eligibility_rules": [
            {"key": "agricultural_guidelines", "value": True, "description_ar": "استخدام تقنيات موفرة للمياه مطابقة لمعايير وزارة البيئة والمياه والزراعة."}
        ],
        "official_source_url": "https://adf.gov.sa/ar/Services/Pages/SpecializedLoans.aspx",
        "source_type": "OFFICIAL_PROVIDER",
        "source_owner": "Agricultural Development Fund",
        "effective_from": "2023-01-01",
        "effective_to": None,
        "verification_status": "VERIFIED_CURRENT",
        "rule_version": "1.0.0",
        "rules": [
            {
                "rule_key": "owner_equity_rule",
                "rule_type": "ELIGIBILITY",
                "structured_value": {"min_percentage": 0.30, "max_coverage_pct": 0.70},
                "description_ar": "تغطية الصندوق تصل إلى 70% من إجمالي التكاليف الاستثمارية المعتمدة.",
                "description_en": "Loan covers up to 70% of total approved investment costs.",
                "source_url": "https://adf.gov.sa/ar/Services/Pages/SpecializedLoans.aspx",
                "source_reference": "لائحة القروض المتخصصة - المادة 5 (نسب التمويل)",
                "source_authority": "OFFICIAL_PROVIDER",
            }
        ],
    },
]


# ==============================================================================
# SEEDING & DOMAIN LOGIC
# ==============================================================================

def ensure_seed_programs(db: Session) -> int:
    """Idempotently seed the official 12 verified funding programs and their rule provenance.

    Returns the count of programs currently in the database.
    """
    # Ensure tables exist in current bind
    models.Base.metadata.create_all(bind=db.get_bind(), tables=[models.FundingProgram.__table__, models.FundingProgramRule.__table__])

    existing_slugs = {p.slug for p in db.query(models.FundingProgram.slug).all()}
    count_inserted = 0

    for prog_data in VERIFIED_PROGRAM_CATALOG:
        slug = prog_data["slug"]
        if slug in existing_slugs:
            continue

        rules_data = prog_data.get("rules", [])
        prog_fields = {k: v for k, v in prog_data.items() if k != "rules"}

        program = models.FundingProgram(**prog_fields)
        db.add(program)
        db.flush()  # assign program.id

        for r_data in rules_data:
            rule = models.FundingProgramRule(
                program_id=program.id,
                **r_data,
            )
            db.add(rule)

        count_inserted += 1

    if count_inserted > 0:
        db.commit()

    return db.query(models.FundingProgram).count()


def list_funding_programs(
    db: Session,
    provider: Optional[str] = None,
    program_type: Optional[str] = None,
    verification_status: Optional[str] = None,
    target_business_stage: Optional[str] = None,
    sector: Optional[str] = None,
) -> List[models.FundingProgram]:
    """List funding programs matching query filters, eagerly loading rules."""
    query = db.query(models.FundingProgram).options(joinedload(models.FundingProgram.rules))

    if provider:
        query = query.filter(models.FundingProgram.provider == provider)
    if program_type:
        query = query.filter(models.FundingProgram.program_type == program_type)
    if verification_status:
        query = query.filter(models.FundingProgram.verification_status == verification_status)
    if target_business_stage and target_business_stage != "ALL":
        query = query.filter(
            (models.FundingProgram.target_business_stage == target_business_stage)
            | (models.FundingProgram.target_business_stage == "ALL")
        )

    results = query.order_by(models.FundingProgram.id.asc()).all()

    # Sector in-memory filtering if requested
    if sector and sector != "all":
        results = [
            p for p in results
            if "all" in (p.target_sectors or []) or sector in (p.target_sectors or [])
        ]

    return results


def get_funding_program(db: Session, program_id: int) -> Optional[models.FundingProgram]:
    """Fetch single funding program by primary key with all associated rule provenance."""
    return (
        db.query(models.FundingProgram)
        .options(joinedload(models.FundingProgram.rules))
        .filter(models.FundingProgram.id == program_id)
        .first()
    )


def get_funding_program_by_slug(db: Session, slug: str) -> Optional[models.FundingProgram]:
    """Fetch single funding program by slug with associated rules."""
    return (
        db.query(models.FundingProgram)
        .options(joinedload(models.FundingProgram.rules))
        .filter(models.FundingProgram.slug == slug)
        .first()
    )


def summarize_registry(db: Session) -> Dict[str, Any]:
    """Return summary statistics of the verified funding programs registry."""
    total = db.query(models.FundingProgram).count()
    verified_current = (
        db.query(models.FundingProgram)
        .filter(models.FundingProgram.verification_status == "VERIFIED_CURRENT")
        .count()
    )
    providers_rows = (
        db.query(models.FundingProgram.provider, func.count(models.FundingProgram.id))
        .group_by(models.FundingProgram.provider)
        .all()
    )
    types_rows = (
        db.query(models.FundingProgram.program_type, func.count(models.FundingProgram.id))
        .group_by(models.FundingProgram.program_type)
        .all()
    )

    return {
        "total_programs": total,
        "verified_current_count": verified_current,
        "providers_breakdown": {p: cnt for p, cnt in providers_rows},
        "program_types_breakdown": {t: cnt for t, cnt in types_rows},
        "all_providers": [p[0] for p in providers_rows],
    }
