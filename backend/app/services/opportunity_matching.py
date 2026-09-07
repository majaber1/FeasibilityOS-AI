"""Deterministic Opportunity Fit & Matching Engine (Wave 3B).

Transitions the user from:
"What opportunities exist?" -> "Which VERIFIED opportunity fits ME, and why?"

Authoritative Principles:
1. Deterministic & Evidence-Based: No AI probability, no weighted scoring, no arbitrary % match.
2. Explicit Unknown States: UNKNOWN never converts into PASS or FAIL.
3. Hard Constraints vs Preferences: Hard constraint failure -> NOT_MATCHED. Preference mismatch -> POSSIBLE_MATCH.
4. Actionable Gate: Only active, verified opportunities with supported opportunity_existence are evaluated.
   Non-actionable opportunities return NOT_EVALUATED.
5. Budget Integrity: UNKNOWN investment requirement != budget fit -> NEEDS_INFORMATION.
6. Geography Integrity: KSA_NATIONAL proves national scope, but site/territory availability is UNKNOWN.
7. Snapshot Auditability: Captures fit profile snapshot, source version, and criterion evaluations for persistent audit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app import models
from app.services.opportunities import (
    STATUS_VERIFIED_CURRENT,
    STATUS_VERIFIED_PARTIAL,
    STATUS_UNVERIFIED,
    STATUS_STALE,
    STATUS_CHANGED,
    STATUS_DISCONTINUED,
)

# Match States
STATE_MATCH = "MATCH"
STATE_POSSIBLE_MATCH = "POSSIBLE_MATCH"
STATE_NEEDS_INFORMATION = "NEEDS_INFORMATION"
STATE_NOT_MATCHED = "NOT_MATCHED"
STATE_NOT_EVALUATED = "NOT_EVALUATED"

ALL_MATCH_STATES = [
    STATE_MATCH,
    STATE_POSSIBLE_MATCH,
    STATE_NEEDS_INFORMATION,
    STATE_NOT_MATCHED,
    STATE_NOT_EVALUATED,
]

# Criterion Evaluation Results
CRITERION_PASS = "PASS"
CRITERION_FAIL = "FAIL"
CRITERION_UNKNOWN = "UNKNOWN"
CRITERION_NOT_APPLICABLE = "NOT_APPLICABLE"

# Constraint Strengths
STRENGTH_HARD = "HARD"
STRENGTH_PREFERENCE = "PREFERENCE"

CALCULATION_VERSION = "1.0.0"


def evaluate_single_opportunity(
    opp: models.VerifiedOpportunity,
    profile_snapshot: Dict[str, Any],
) -> Tuple[str, Dict[str, Any], str, List[str]]:
    """Deterministically evaluates one opportunity against a user fit profile snapshot.

    Returns:
        (match_state, criteria_evaluations, summary_reason, missing_information)
    """
    # --------------------------------------------------------------------------
    # 1. Eligibility Check (Rule: Only actionable, verified opportunities)
    # --------------------------------------------------------------------------
    existence_supported = bool(
        opp.field_provenance
        and isinstance(opp.field_provenance, dict)
        and opp.field_provenance.get("opportunity_existence", {}).get("supported") is True
    )

    if (
        not opp.is_active
        or opp.verification_status not in (STATUS_VERIFIED_PARTIAL, STATUS_VERIFIED_CURRENT)
        or not existence_supported
    ):
        reason_parts = []
        if not opp.is_active:
            reason_parts.append("الفرصة غير نشطة حالياً")
        if opp.verification_status not in (STATUS_VERIFIED_PARTIAL, STATUS_VERIFIED_CURRENT):
            reason_parts.append(f"حالة التحقق غير كافية ({opp.verification_status})")
        if not existence_supported:
            reason_parts.append("وجود الفرصة غير موثق بمصدر أولي مستقل")

        summary = "غير قابلة للتقييم: " + "، ".join(reason_parts)
        return (
            STATE_NOT_EVALUATED,
            {},
            summary,
            ["تحقق المصدر الأولي وفعالية الفرصة غير مكتملة"],
        )

    criteria: Dict[str, Any] = {}
    missing_info: List[str] = []
    hard_fails = 0
    material_unknowns = 0
    preference_mismatches = 0
    non_critical_unknowns = 0

    prov = opp.field_provenance if isinstance(opp.field_provenance, dict) else {}

    # --------------------------------------------------------------------------
    # 2. Excluded Sectors (HARD Constraint)
    # --------------------------------------------------------------------------
    excluded_sectors = profile_snapshot.get("excluded_sectors") or []
    if excluded_sectors:
        if opp.sector in excluded_sectors:
            criteria["excluded_sectors"] = {
                "criterion": "excluded_sectors",
                "label_ar": "القطاعات المستبعدة",
                "constraint_strength": STRENGTH_HARD,
                "user_value": excluded_sectors,
                "opportunity_value": opp.sector,
                "result": CRITERION_FAIL,
                "reason": f"قطاع الفرصة ({opp.sector}) يقع ضمن قائمة القطاعات المستبعدة صراحة من المستثمر.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("sector"),
            }
            hard_fails += 1
        else:
            criteria["excluded_sectors"] = {
                "criterion": "excluded_sectors",
                "label_ar": "القطاعات المستبعدة",
                "constraint_strength": STRENGTH_HARD,
                "user_value": excluded_sectors,
                "opportunity_value": opp.sector,
                "result": CRITERION_PASS,
                "reason": f"قطاع الفرصة ({opp.sector}) ليس ضمن القطاعات المستبعدة.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("sector"),
            }

    # --------------------------------------------------------------------------
    # 3. Available Capital / Budget Fit (Rule: UNKNOWN != FIT)
    # --------------------------------------------------------------------------
    user_capital = profile_snapshot.get("available_capital")
    capital_strength = profile_snapshot.get("capital_constraint_type") or STRENGTH_HARD

    if user_capital is not None and user_capital > 0:
        if opp.investment_min is None:
            criteria["available_capital"] = {
                "criterion": "available_capital",
                "label_ar": "الميزانية ورأس المال المتاح",
                "constraint_strength": capital_strength,
                "user_value": f"{user_capital:,.0f} ر.س (USER_ASSUMPTION)",
                "opportunity_value": "غير معلن رسمياً (UNKNOWN)",
                "result": CRITERION_UNKNOWN,
                "reason": "الاستثمار المطلوب غير منشور في البوابة العامة للمصدر ويتطلب طلباً مباشراً للمعلومات أو إفصاحاً تعاقدياً.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("investment_min"),
            }
            material_unknowns += 1
            missing_info.append("الحد الأدنى والأقصى للاستثمار الرأسمالي والتجهيزي غير معلن رسمياً")
        else:
            # Verified investment limits exist
            if user_capital < opp.investment_min:
                criteria["available_capital"] = {
                    "criterion": "available_capital",
                    "label_ar": "الميزانية ورأس المال المتاح",
                    "constraint_strength": capital_strength,
                    "user_value": f"{user_capital:,.0f} ر.س (USER_ASSUMPTION)",
                    "opportunity_value": f"الحد الأدنى: {opp.investment_min:,.0f} ر.س",
                    "result": CRITERION_FAIL,
                    "reason": f"رأس المال المتاح ({user_capital:,.0f} ر.س) يقل عن الحد الأدنى الموثق للاستثمار ({opp.investment_min:,.0f} ر.س).",
                    "source_type": opp.source_type,
                    "source_url": opp.official_source_url,
                    "source_version": opp.data_version,
                    "provenance": prov.get("investment_min"),
                }
                if capital_strength == STRENGTH_HARD:
                    hard_fails += 1
                else:
                    preference_mismatches += 1
            else:
                criteria["available_capital"] = {
                    "criterion": "available_capital",
                    "label_ar": "الميزانية ورأس المال المتاح",
                    "constraint_strength": capital_strength,
                    "user_value": f"{user_capital:,.0f} ر.س (USER_ASSUMPTION)",
                    "opportunity_value": f"الحد الأدنى: {opp.investment_min:,.0f} ر.س",
                    "result": CRITERION_PASS,
                    "reason": f"رأس المال المتاح يغطي الحد الأدنى للاستثمار الموثق ({opp.investment_min:,.0f} ر.س).",
                    "source_type": opp.source_type,
                    "source_url": opp.official_source_url,
                    "source_version": opp.data_version,
                    "provenance": prov.get("investment_min"),
                }
    else:
        criteria["available_capital"] = {
            "criterion": "available_capital",
            "label_ar": "الميزانية ورأس المال المتاح",
            "constraint_strength": STRENGTH_PREFERENCE,
            "user_value": "غير محدد من المستخدم",
            "opportunity_value": "غير معلن" if opp.investment_min is None else f"{opp.investment_min:,.0f} ر.س",
            "result": CRITERION_NOT_APPLICABLE,
            "reason": "المستثمر لم يدخل قيد رأس مال محدد.",
            "source_type": opp.source_type,
            "source_url": opp.official_source_url,
            "source_version": opp.data_version,
            "provenance": prov.get("investment_min"),
        }

    # --------------------------------------------------------------------------
    # 4. Preferred Sectors (PREFERENCE by default)
    # --------------------------------------------------------------------------
    preferred_sectors = profile_snapshot.get("preferred_sectors") or []
    if preferred_sectors:
        if opp.sector in preferred_sectors:
            criteria["sector"] = {
                "criterion": "sector",
                "label_ar": "القطاع المفضل",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": preferred_sectors,
                "opportunity_value": opp.sector,
                "result": CRITERION_PASS,
                "reason": f"يتطابق قطاع الفرصة ({opp.sector}) مع القطاعات المفضلة للمستثمر.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("sector"),
            }
        else:
            criteria["sector"] = {
                "criterion": "sector",
                "label_ar": "القطاع المفضل",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": preferred_sectors,
                "opportunity_value": opp.sector,
                "result": CRITERION_FAIL,
                "reason": f"قطاع الفرصة ({opp.sector}) ليس ضمن القطاعات المفضلة، ولكنه غير مستبعد كقيد حتمي.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("sector"),
            }
            preference_mismatches += 1

    # --------------------------------------------------------------------------
    # 5. Opportunity Type (FRANCHISE vs BUSINESS_OPPORTUNITY)
    # --------------------------------------------------------------------------
    preferred_types = profile_snapshot.get("preferred_opportunity_types") or []
    type_strength = profile_snapshot.get("opportunity_type_constraint") or STRENGTH_PREFERENCE

    if preferred_types:
        if opp.opportunity_type in preferred_types:
            criteria["opportunity_type"] = {
                "criterion": "opportunity_type",
                "label_ar": "نوع الفرصة (امتياز / مشروع مستقل)",
                "constraint_strength": type_strength,
                "user_value": preferred_types,
                "opportunity_value": opp.opportunity_type,
                "result": CRITERION_PASS,
                "reason": f"نوع الفرصة ({opp.opportunity_type}) يطابق الخيار المطلوب.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
        else:
            is_hard = type_strength == STRENGTH_HARD
            criteria["opportunity_type"] = {
                "criterion": "opportunity_type",
                "label_ar": "نوع الفرصة (امتياز / مشروع مستقل)",
                "constraint_strength": type_strength,
                "user_value": preferred_types,
                "opportunity_value": opp.opportunity_type,
                "result": CRITERION_FAIL if is_hard else CRITERION_NOT_APPLICABLE,
                "reason": f"نوع الفرصة ({opp.opportunity_type}) لا يطابق خيار المستثمر ({preferred_types}).",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
            if is_hard:
                hard_fails += 1
            else:
                preference_mismatches += 1

    # --------------------------------------------------------------------------
    # 6. Geography: Scope vs Territory Availability
    # Rule: KSA_NATIONAL supports national scope, but does NOT prove specific site availability
    # --------------------------------------------------------------------------
    target_region = profile_snapshot.get("target_region")
    target_city = profile_snapshot.get("target_city")

    if target_region or target_city:
        loc_str = f"{target_city or ''} ({target_region or ''})".strip()
        # Geographic Scope
        if opp.geography == "KSA_NATIONAL" or (opp.region and target_region and opp.region == target_region):
            criteria["geographic_scope"] = {
                "criterion": "geographic_scope",
                "label_ar": "النطاق الجغرافي للعلامة",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": loc_str,
                "opportunity_value": opp.geography,
                "result": CRITERION_PASS,
                "reason": "العلامة مرخصة للتوسع في نطاق المملكة العربية السعودية الشامل.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("geography"),
            }
        else:
            criteria["geographic_scope"] = {
                "criterion": "geographic_scope",
                "label_ar": "النطاق الجغرافي للعلامة",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": loc_str,
                "opportunity_value": opp.geography,
                "result": CRITERION_NOT_APPLICABLE,
                "reason": f"نطاق الفرصة ({opp.geography}) لا يغطي المنطقة المستهدفة صراحة.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("geography"),
            }
            preference_mismatches += 1

        # Territory Availability (Strictly UNKNOWN unless explicitly published per site)
        criteria["territory_availability"] = {
            "criterion": "territory_availability",
            "label_ar": "توفر الموقع/المحافظة المستهدفة",
            "constraint_strength": STRENGTH_PREFERENCE,
            "user_value": loc_str,
            "opportunity_value": "غير معلن للموقع المحدد (UNKNOWN)",
            "result": CRITERION_UNKNOWN,
            "reason": "توفر حصة إقليمية أو موقع شاغر محدد في هذه المدينة يتطلب تقديم طلب تأهيل للشركة ووثيقة إفصاح معتمدة.",
            "source_type": opp.source_type,
            "source_url": opp.official_source_url,
            "source_version": opp.data_version,
            "provenance": prov.get("geography"),
        }
        non_critical_unknowns += 1
        missing_info.append(f"توفر رخصة أو موقع محدد في {loc_str} غير منشور رسمياً")

    # --------------------------------------------------------------------------
    # 7. Business Model & Target Customer
    # --------------------------------------------------------------------------
    # 7. Business Model, Target Customer & Experience Sectors (PREFERENCE)
    # Evaluated deterministically as PREFERENCE criteria.
    # Mismatches lower match strength (MATCH -> POSSIBLE_MATCH), never cause NOT_MATCHED.
    # --------------------------------------------------------------------------
    target_cust = profile_snapshot.get("target_customer")
    if target_cust and target_cust != "ANY":
        if opp.target_customer == target_cust:
            criteria["target_customer"] = {
                "criterion": "target_customer",
                "label_ar": "نوع العميل المستهدف (B2B / B2C)",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": target_cust,
                "opportunity_value": opp.target_customer,
                "result": CRITERION_PASS,
                "reason": f"نموذج العميل المستهدف متطابق ({opp.target_customer}).",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
        elif opp.target_customer is None:
            criteria["target_customer"] = {
                "criterion": "target_customer",
                "label_ar": "نوع العميل المستهدف (B2B / B2C)",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": target_cust,
                "opportunity_value": "غير معلن رسمياً (UNKNOWN)",
                "result": CRITERION_UNKNOWN,
                "reason": "نوع العميل المستهدف للفرصة غير منشور رسمياً في البوابة العامة.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
            non_critical_unknowns += 1
        else:
            criteria["target_customer"] = {
                "criterion": "target_customer",
                "label_ar": "نوع العميل المستهدف (B2B / B2C)",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": target_cust,
                "opportunity_value": opp.target_customer or "غير محدد",
                "result": CRITERION_FAIL,
                "reason": f"نوع عميل الفرصة ({opp.target_customer}) يختلف عن خيار المستثمر ({target_cust})، ويُعد عامل تفضيل.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
            preference_mismatches += 1

    # Preferred Business Models
    preferred_models = profile_snapshot.get("preferred_business_models") or []
    if preferred_models:
        if opp.business_model is None:
            criteria["business_model"] = {
                "criterion": "business_model",
                "label_ar": "نموذج العمل التجاري",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": preferred_models,
                "opportunity_value": "غير معلن رسمياً (UNKNOWN)",
                "result": CRITERION_UNKNOWN,
                "reason": "نموذج العمل التشغيلي للفرصة غير منشور صراحة في الإفصاح العام.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
            non_critical_unknowns += 1
        elif any(
            m.strip().lower() in opp.business_model.lower() or opp.business_model.lower() in m.strip().lower()
            for m in preferred_models if m.strip()
        ):
            criteria["business_model"] = {
                "criterion": "business_model",
                "label_ar": "نموذج العمل التجاري",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": preferred_models,
                "opportunity_value": opp.business_model,
                "result": CRITERION_PASS,
                "reason": f"نموذج عمل الفرصة ({opp.business_model}) يتوافق مع نماذج العمل المفضلة للمستثمر.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
        else:
            criteria["business_model"] = {
                "criterion": "business_model",
                "label_ar": "نموذج العمل التجاري",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": preferred_models,
                "opportunity_value": opp.business_model,
                "result": CRITERION_FAIL,
                "reason": f"نموذج عمل الفرصة ({opp.business_model}) يختلف عن التفضيلات المحددة، كعامل تفضيل غير حتمي.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("opportunity_existence"),
            }
            preference_mismatches += 1

    # Experience Sectors
    experience_sectors = profile_snapshot.get("experience_sectors") or []
    if experience_sectors:
        if opp.sector in experience_sectors:
            criteria["experience_sector"] = {
                "criterion": "experience_sector",
                "label_ar": "توافق الخبرة السابقة للمستثمر",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": experience_sectors,
                "opportunity_value": opp.sector,
                "result": CRITERION_PASS,
                "reason": f"يمتلك المستثمر خبرة سابقة في قطاع الفرصة ({opp.sector}). (ملاحظة: الخبرة السابقة ميزة تفضيلية ولا تضمن الأداء المالي).",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("sector"),
            }
        else:
            criteria["experience_sector"] = {
                "criterion": "experience_sector",
                "label_ar": "توافق الخبرة السابقة للمستثمر",
                "constraint_strength": STRENGTH_PREFERENCE,
                "user_value": experience_sectors,
                "opportunity_value": opp.sector,
                "result": CRITERION_FAIL,
                "reason": f"قطاع الفرصة ({opp.sector}) ليس ضمن القطاعات التي يمتلك المستثمر خبرة فيها، ويُعامل كعامل تفضيل استرشادي فقط.",
                "source_type": opp.source_type,
                "source_url": opp.official_source_url,
                "source_version": opp.data_version,
                "provenance": prov.get("sector"),
            }
            preference_mismatches += 1

    # --------------------------------------------------------------------------
    # 8. Deterministic Match State Determination
    # --------------------------------------------------------------------------
    if hard_fails > 0:
        match_state = STATE_NOT_MATCHED
        summary_reason = "غير متطابق: يتعارض مع قيد حتمي واحد أو أكثر حدده المستثمر."
    elif material_unknowns > 0:
        match_state = STATE_NEEDS_INFORMATION
        summary_reason = "يتطلب معلومات إضافية: هناك بيانات جوهرية (مثل حجم الاستثمار المطلوب) غير معلنة في المصدر الرسمي المنشور."
    elif preference_mismatches > 0 or non_critical_unknowns > 0:
        match_state = STATE_POSSIBLE_MATCH
        summary_reason = "تطابق محتمل: لا يتعارض مع أي قيد حتمي، ولكن توجد تفضيلات غير محققة أو تفاصيل غير مؤكدة."
    else:
        match_state = STATE_MATCH
        summary_reason = "تطابق تام: مستوفٍ لجميع القيود والشروط المحددة من قبل المستثمر مع توافر الأدلة الموثقة."

    return match_state, criteria, summary_reason, missing_info


def execute_match_run(
    db: Session,
    user: models.User,
    fit_profile: models.OpportunityFitProfile,
) -> models.OpportunityMatchRun:
    """Executes a matching run across all actionable opportunities and persists results."""
    # Build profile snapshot
    profile_snapshot = {
        "available_capital": fit_profile.available_capital,
        "capital_constraint_type": fit_profile.capital_constraint_type,
        "preferred_sectors": fit_profile.preferred_sectors or [],
        "excluded_sectors": fit_profile.excluded_sectors or [],
        "preferred_opportunity_types": fit_profile.preferred_opportunity_types or [],
        "opportunity_type_constraint": fit_profile.opportunity_type_constraint,
        "target_region": fit_profile.target_region,
        "target_city": fit_profile.target_city,
        "preferred_business_models": fit_profile.preferred_business_models or [],
        "target_customer": fit_profile.target_customer,
        "experience_sectors": fit_profile.experience_sectors or [],
        "notes": fit_profile.notes,
        "profile_version": fit_profile.version,
    }

    # Create MatchRun
    match_run = models.OpportunityMatchRun(
        user_id=user.id,
        fit_profile_id=fit_profile.id,
        fit_profile_version=fit_profile.version,
        fit_profile_snapshot=profile_snapshot,
        calculation_version=CALCULATION_VERSION,
        evaluated_at=datetime.now(timezone.utc),
    )
    db.add(match_run)
    db.flush()

    # Query all actionable opportunities (and preserve non-actionable as NOT_EVALUATED)
    all_opportunities = db.query(models.VerifiedOpportunity).all()

    for opp in all_opportunities:
        match_state, criteria, summary_reason, missing_info = evaluate_single_opportunity(
            opp=opp,
            profile_snapshot=profile_snapshot,
        )

        result = models.OpportunityMatchResult(
            match_run_id=match_run.id,
            opportunity_id=opp.id,
            opportunity_version=opp.data_version,
            verification_status_at_eval=opp.verification_status,
            match_state=match_state,
            criteria_evaluations=criteria,
            summary_reason=summary_reason,
            missing_information=missing_info,
        )
        db.add(result)

    db.commit()
    db.refresh(match_run)
    return match_run


def get_latest_match_run(db: Session, user_id: int) -> Optional[models.OpportunityMatchRun]:
    """Retrieves the user's latest match run, verifying current validity."""
    return (
        db.query(models.OpportunityMatchRun)
        .filter(models.OpportunityMatchRun.user_id == user_id)
        .order_by(models.OpportunityMatchRun.id.desc())
        .first()
    )


def build_fit_snapshot_for_study(match_result: models.OpportunityMatchResult) -> Dict[str, Any]:
    """Builds a frozen, immutable opportunity fit snapshot to be attached to a study payload."""
    match_run = match_result.match_run
    return {
        "match_run_id": match_run.id,
        "match_result_id": match_result.id,
        "evaluated_at": match_run.evaluated_at.isoformat() if match_run.evaluated_at else None,
        "calculation_version": match_run.calculation_version,
        "match_state": match_result.match_state,
        "summary_reason": match_result.summary_reason,
        "criteria_evaluations": match_result.criteria_evaluations,
        "missing_information": match_result.missing_information,
        "fit_profile_snapshot": match_run.fit_profile_snapshot,
        "opportunity_id": match_result.opportunity_id,
        "opportunity_version_at_eval": match_result.opportunity_version,
    }


def resolve_current_match_state(
    match_result: models.OpportunityMatchResult,
    opportunity: models.VerifiedOpportunity,
) -> Tuple[str, bool, Optional[str]]:
    """Authoritatively resolves the current presentation match state for a match result.

    Considers at minimum:
    1. opportunity.data_version != match_result.opportunity_version
    2. verification status changed to: UNVERIFIED, STALE, CHANGED, DISCONTINUED
       (or not in VERIFIED_PARTIAL, VERIFIED_CURRENT)
    3. opportunity inactive (not opportunity.is_active)
    4. opportunity_existence no longer supported

    Current presentation becomes:
        NOT_EVALUATED
    with:
        requires_re_evaluation = True

    Historical stored result remains immutable.

    Returns:
        (current_match_state, requires_re_evaluation, reason_if_stale)
    """
    existence_supported = bool(
        opportunity.field_provenance
        and isinstance(opportunity.field_provenance, dict)
        and opportunity.field_provenance.get("opportunity_existence", {}).get("supported") is True
    )

    reasons = []

    if str(opportunity.data_version) != str(match_result.opportunity_version):
        reasons.append("تم تحديث بيانات الفرصة الرسمية (إصدار جديد متاح)")

    if not opportunity.is_active:
        reasons.append("أصبحت الفرصة غير نشطة حالياً")

    if opportunity.verification_status not in (STATUS_VERIFIED_PARTIAL, STATUS_VERIFIED_CURRENT):
        reasons.append(f"حالة التحقق للفرصة ({opportunity.verification_status}) غير مؤهلة أو تغيرت")

    if not existence_supported:
        reasons.append("توثيق وجود الفرصة بالمصدر الأولي لم يعد مدعوماً")

    # If the opportunity was previously a valid evaluated match (not NOT_EVALUATED)
    # and any condition triggered, it is stale and requires re-evaluation.
    # If it was already NOT_EVALUATED at eval time, check if version or verification changed.
    if match_result.match_state == STATE_NOT_EVALUATED:
        if str(opportunity.data_version) != str(match_result.opportunity_version):
            return STATE_NOT_EVALUATED, True, "تم تحديث بيانات الفرصة الرسمية - يلزم إعادة التقييم"
        if opportunity.verification_status != match_result.verification_status_at_eval:
            return STATE_NOT_EVALUATED, True, f"تغيرت حالة التحقق للفرصة إلى {opportunity.verification_status} - يلزم إعادة التقييم"
        return STATE_NOT_EVALUATED, False, match_result.summary_reason

    if reasons:
        reason_str = "تغيرت بيانات المصدر أو أصبحت غير فعالة منذ آخر تقييم، ويتطلب إعادة التقييم: " + "، ".join(reasons)
        return STATE_NOT_EVALUATED, True, reason_str

    return match_result.match_state, False, None
