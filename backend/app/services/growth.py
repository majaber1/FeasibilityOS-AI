"""Deterministic Domain Service for Wave 6 Growth OS.

Lifecycle:
ACTUALS (from Launch OS)
  → BUSINESS HEALTH
  → TRENDS
  → UNIT ECONOMICS
  → RISKS
  → GROWTH OPPORTUNITIES
  → WHAT-IF SCENARIOS
  → EXPANSION READINESS
  → GROWTH FUNDING CONTEXT
  → DECISION
  → SCALE / FIX / PIVOT / HOLD / STOP

Strict Governance Principles:
- No generic AI optimism.
- No fake growth score or synthetic percentage.
- Missing data != poor performance. Missing data produces INSUFFICIENT_DATA or UNKNOWN / NOT_AVAILABLE.
- CAC calculated ONLY when acquisition spend AND acquired customers are both known for the same period.
- Deterministic trend requires at least 2 periods; zero denominator => NOT_AVAILABLE.
- What-If outputs strictly separate ACTUAL, BASELINE, USER_ASSUMPTION, PLATFORM_DERIVED.
- Growth Funding context integrates directly with Wave 2 without duplicating logic (potential funding != cash).
- SCALE decision cannot result purely from revenue growth; cash, margin, capacity, and data completeness are required.
- PIVOT decision links to a NEW Wave 4 validation cycle without overwriting historical records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app import models
from app.services.launch import evaluate_workspace_variances
from app.services.funding_matching import evaluate_study_funding_matches

CALCULATION_VERSION = "v1.0.0-growth-os"

# Business Health States
HEALTH_HEALTHY = "HEALTHY"
HEALTH_WATCH = "WATCH"
HEALTH_AT_RISK = "AT_RISK"
HEALTH_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
VALID_HEALTH_STATES = {HEALTH_HEALTHY, HEALTH_WATCH, HEALTH_AT_RISK, HEALTH_INSUFFICIENT_DATA}

# Trend Directions
TREND_IMPROVING = "IMPROVING"
TREND_STABLE = "STABLE"
TREND_DETERIORATING = "DETERIORATING"
TREND_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

# Expansion Readiness States
READINESS_READY = "READY"
READINESS_CONDITIONALLY_READY = "CONDITIONALLY_READY"
READINESS_NOT_READY = "NOT_READY"
READINESS_NEEDS_INFO = "NEEDS_INFORMATION"

# Prerequisite States
PREREQ_PASS = "PASS"
PREREQ_FAIL = "FAIL"
PREREQ_UNKNOWN = "UNKNOWN"
PREREQ_NA = "NA"

# Risk Levels
RISK_LOW = "LOW"
RISK_WATCH = "WATCH"
RISK_HIGH = "HIGH"
RISK_UNKNOWN = "UNKNOWN"

# Growth Decisions
DECISION_SCALE = "SCALE"
DECISION_FIX = "FIX"
DECISION_PIVOT = "PIVOT"
DECISION_HOLD = "HOLD"
DECISION_STOP = "STOP"
DECISION_NEEDS_INFO = "NEEDS_INFORMATION"
VALID_GROWTH_DECISIONS = {
    DECISION_SCALE,
    DECISION_FIX,
    DECISION_PIVOT,
    DECISION_HOLD,
    DECISION_STOP,
    DECISION_NEEDS_INFO,
}

# Scenario Types
SCENARIO_TYPES = {
    "NEW_BRANCH",
    "NEW_CITY",
    "NEW_REGION",
    "NEW_PRODUCT",
    "NEW_SERVICE",
    "CAPACITY_EXPANSION",
    "HIRING",
    "MARKETING_EXPANSION",
    "FRANCHISE_EXPANSION",
    "DIGITAL_TRANSFORMATION",
    "CUSTOM",
    "OTHER",
}


def get_or_create_growth_workspace(
    db: Session,
    user: models.User,
    study_id: int,
) -> models.GrowthWorkspace:
    """Retrieves or initializes the GrowthWorkspace for a feasibility study.
    Enforces ownership isolation: user must own the study's parent project.
    """
    study = db.query(models.FeasibilityStudy).filter_by(id=study_id).first()
    if not study:
        raise ValueError(f"Feasibility study {study_id} not found")
    if study.project.owner_id != user.id:
        raise PermissionError("Access denied to study's growth workspace")

    ws = db.query(models.GrowthWorkspace).filter_by(study_id=study.id).first()
    if not ws:
        ws = models.GrowthWorkspace(
            study_id=study.id,
            project_id=study.project_id,
            user_id=user.id,
            status="ACTIVE",
        )
        db.add(ws)
        db.commit()
        db.refresh(ws)

    return ws


# ==============================================================================
# 1. TREND ANALYSIS ENGINE
# ==============================================================================

def analyze_metric_trend(
    periods: List[models.LaunchActualPeriod],
    metric_attr: str,
    metric_name_ar: str,
    higher_is_better: bool = True,
) -> Dict[str, Any]:
    """Calculates deterministic trend for a specific actuals metric across recorded periods.
    
    Rules:
    - Requires at least 2 periods with known values. If < 2 periods: INSUFFICIENT_DATA.
    - Zero denominator => percentage change is NOT_AVAILABLE (None).
    - Exposes period range, metric, values, direction, absolute change, percentage change, calculation version.
    """
    known_entries = []
    for p in periods:
        val = getattr(p, metric_attr, None)
        if val is not None:
            known_entries.append((p.period_order, p.period_label, float(val)))

    known_entries.sort(key=lambda x: x[0])

    if len(known_entries) < 2:
        return {
            "metric": metric_attr,
            "metric_name_ar": metric_name_ar,
            "direction": TREND_INSUFFICIENT_DATA,
            "direction_ar": "بيانات غير كافية (يلزم دورتين فعليتين على الأقل)",
            "period_range": f"{known_entries[0][1]}" if known_entries else "لا توجد دورات",
            "values_count": len(known_entries),
            "first_value": known_entries[0][2] if known_entries else None,
            "start_value": known_entries[0][2] if known_entries else None,
            "latest_value": known_entries[-1][2] if known_entries else None,
            "absolute_change": None,
            "percentage_change": None,
            "percentage_state": "NOT_AVAILABLE",
            "reason_ar": "لا يمكن احتساب اتجاه موثوق من دورة واحدة فقط أو في حال غياب البيانات.",
            "calculation_version": CALCULATION_VERSION,
        }

    first_entry = known_entries[0]
    latest_entry = known_entries[-1]
    prev_entry = known_entries[-2]

    abs_change = round(latest_entry[2] - prev_entry[2], 2)
    pct_change = None
    pct_state = "NOT_AVAILABLE"

    if prev_entry[2] != 0.0:
        pct_change = round(((latest_entry[2] - prev_entry[2]) / abs(prev_entry[2])) * 100, 2)
        pct_state = "CALCULATED"

    # Direction determination based on recent movement
    if abs_change > 0:
        direction = TREND_IMPROVING if higher_is_better else TREND_DETERIORATING
    elif abs_change < 0:
        direction = TREND_DETERIORATING if higher_is_better else TREND_IMPROVING
    else:
        direction = TREND_STABLE

    direction_ar = {
        TREND_IMPROVING: "في تحسن مستمر",
        TREND_STABLE: "مستقر",
        TREND_DETERIORATING: "في تراجع يستوجب المتابعة",
        TREND_INSUFFICIENT_DATA: "بيانات غير كافية",
    }.get(direction, direction)

    return {
        "metric": metric_attr,
        "metric_name_ar": metric_name_ar,
        "direction": direction,
        "direction_ar": direction_ar,
        "period_range": f"{first_entry[1]} إلى {latest_entry[1]}",
        "values_count": len(known_entries),
        "first_value": first_entry[2],
        "start_value": first_entry[2],
        "previous_value": prev_entry[2],
        "latest_value": latest_entry[2],
        "absolute_change": abs_change,
        "percentage_change": pct_change,
        "percentage_state": pct_state,
        "reason_ar": f"تغيرت القيمة من {prev_entry[2]:,.2f} إلى {latest_entry[2]:,.2f} عبر الدورات المرصودة.",
        "calculation_version": CALCULATION_VERSION,
    }


def evaluate_all_trends(periods: List[models.LaunchActualPeriod]) -> Dict[str, Any]:
    """Runs multi-period trend evaluation across all canonical actual operational metrics."""
    rev_trend = analyze_metric_trend(periods, "actual_revenue", "الإيراد الفعلي", higher_is_better=True)
    opex_trend = analyze_metric_trend(periods, "total_actual_opex", "المصاريف التشغيلية الفعلية", higher_is_better=False)
    net_cf_trend = analyze_metric_trend(periods, "net_cashflow", "صافي التدفق النقدي", higher_is_better=True)
    ticket_trend = analyze_metric_trend(periods, "average_ticket_size", "متوسط قيمة الفاتورة (AOV)", higher_is_better=True)
    tx_trend = analyze_metric_trend(periods, "transactions_count", "عدد المعاملات والطلبات", higher_is_better=True)
    cash_trend = analyze_metric_trend(periods, "closing_cash_balance", "رصيد النقدية الختامي", higher_is_better=True)

    trends_list = [rev_trend, opex_trend, net_cf_trend, ticket_trend, tx_trend, cash_trend]
    has_sufficient = any(t["direction"] != TREND_INSUFFICIENT_DATA for t in trends_list)

    metrics_dict = {
        "actual_revenue": rev_trend,
        "revenue": rev_trend,
        "total_actual_opex": opex_trend,
        "opex": opex_trend,
        "net_cashflow": net_cf_trend,
        "average_ticket_size": ticket_trend,
        "average_ticket": ticket_trend,
        "transactions_count": tx_trend,
        "transactions": tx_trend,
        "closing_cash_balance": cash_trend,
        "cash_balance": cash_trend,
    }

    return {
        "periods_analyzed": len(periods),
        "has_sufficient_history": has_sufficient,
        "total_periods_recorded": len(periods),
        "metrics": metrics_dict,
        "trends": {
            "revenue": rev_trend,
            "opex": opex_trend,
            "net_cashflow": net_cf_trend,
            "average_ticket": ticket_trend,
            "transactions": tx_trend,
            "cash_balance": cash_trend,
        },
        "trends_list": trends_list,
        "calculation_version": CALCULATION_VERSION,
    }


# ==============================================================================
# 2. UNIT ECONOMICS ENGINE
# ==============================================================================

def calculate_unit_economics(period: Optional[models.LaunchActualPeriod]) -> Dict[str, Any]:
    """Calculates unit economics strictly from known inputs for a given operational period.
    
    Rules:
    - CAC requires both known acquisition/marketing spend AND known acquired customers count for the same period.
    - If either is missing: NOT_AVAILABLE / NEEDS_INFORMATION.
    - No synthetic LTV/churn assumptions.
    """
    if not period:
        return {
            "period_label": None,
            "status": "NEEDS_INFORMATION",
            "metrics": {},
            "missing_inputs": ["actual_period"],
            "calculation_version": CALCULATION_VERSION,
        }

    missing_inputs = []
    rev = period.actual_revenue
    tx = period.transactions_count
    aov = period.average_ticket_size
    marketing = period.actual_opex_marketing
    cogs = period.actual_opex_cogs
    opex = period.total_actual_opex
    salaries = period.actual_opex_salaries
    rent = period.actual_opex_rent
    cust_count = getattr(period, "acquired_customers_count", None)

    # 1. Average Order Value / Revenue per Transaction
    calc_aov = None
    aov_state = "NOT_AVAILABLE"
    if aov is not None:
        calc_aov = aov
        aov_state = "RECORDED"
    elif rev is not None and tx is not None:
        if tx > 0:
            calc_aov = round(rev / tx, 2)
            aov_state = "CALCULATED"
        else:
            aov_state = "ZERO_TRANSACTIONS"
    else:
        if rev is None:
            missing_inputs.append("actual_revenue")
        if tx is None:
            missing_inputs.append("transactions_count")

    # 2. Contribution Margin (Revenue - COGS) / Revenue
    gross_profit = None
    gross_margin_pct = None
    gm_state = "NOT_AVAILABLE"
    if rev is not None and cogs is not None:
        gross_profit = round(rev - cogs, 2)
        if rev > 0:
            gross_margin_pct = round((gross_profit / rev) * 100, 2)
            gm_state = "CALCULATED"
        else:
            gm_state = "ZERO_REVENUE"
    else:
        if cogs is None:
            missing_inputs.append("actual_opex_cogs")

    # 3. Fixed Cost Proportion (Salaries + Rent) / Total OPEX
    fixed_cost_pct = None
    fixed_state = "NOT_AVAILABLE"
    if opex is not None and opex > 0 and (salaries is not None or rent is not None):
        fixed_sum = (salaries or 0.0) + (rent or 0.0)
        fixed_cost_pct = round((fixed_sum / opex) * 100, 2)
        fixed_state = "CALCULATED"

    # 4. Operating Margin (Revenue - Total OPEX) / Revenue
    operating_margin_pct = None
    op_margin_state = "NOT_AVAILABLE"
    if rev is not None and opex is not None:
        op_profit = round(rev - opex, 2)
        if rev > 0:
            operating_margin_pct = round((op_profit / rev) * 100, 2)
            op_margin_state = "CALCULATED"
        else:
            op_margin_state = "ZERO_REVENUE"
    else:
        if opex is None:
            missing_inputs.append("total_actual_opex")

    # 5. Customer Acquisition Cost (CAC)
    # Strict rule: requires known acquisition/marketing spend AND known acquired customers count for same period.
    cac = None
    cac_known = False
    cac_state = "NOT_AVAILABLE"
    cac_reason_ar = "غير متوفر: يلزم توفر ميزانية التسويق الفعلي وعدد العملاء المستقطبين لنفس الفترة."
    acq_count = cust_count if (cust_count is not None and cust_count > 0) else None
    if marketing is not None and acq_count is not None and acq_count > 0:
        cac = round(marketing / acq_count, 2)
        cac_known = True
        cac_state = "CALCULATED"
        cac_reason_ar = f"تم احتساب تكلفة الاستقطاب استناداً لنفقات التسويق {marketing:,.2f} ر.س مقسومة على {acq_count} عميل مستقطب."
    else:
        if marketing is None:
            missing_inputs.append("actual_opex_marketing")
        if cust_count is None:
            missing_inputs.append("acquired_customers_count")

    cac_metric = {
        "value": cac,
        "is_known": cac_known,
        "note_ar": cac_reason_ar,
        "unit": "SAR",
        "state": cac_state,
        "label_ar": "تكلفة اكتساب العميل الفعلي (CAC)",
        "inputs_used": {"marketing_spend": marketing, "acquired_customers": acq_count},
    }

    return {
        "period_label": period.period_label,
        "period_order": period.period_order,
        "status": "CALCULATED" if not missing_inputs else "PARTIAL",
        "inputs": {
            "actual_revenue": rev,
            "transactions_count": tx,
            "acquired_customers_count": cust_count,
            "actual_opex_marketing": marketing,
            "actual_opex_cogs": cogs,
            "actual_opex_salaries": salaries,
            "actual_opex_rent": rent,
            "total_actual_opex": opex,
        },
        "metrics": {
            "average_ticket_size": {
                "value": calc_aov,
                "is_known": calc_aov is not None,
                "unit": "SAR",
                "state": aov_state,
                "label_ar": "متوسط قيمة الطلب / الفاتورة (AOV)",
                "inputs_used": {"revenue": rev, "transactions": tx},
            },
            "contribution_margin_pct": {
                "value": gross_margin_pct,
                "is_known": gross_margin_pct is not None,
                "unit": "%",
                "state": gm_state,
                "label_ar": "نسبة هامش المساهمة / الربح الإجمالي",
                "inputs_used": {"revenue": rev, "cogs": cogs},
            },
            "fixed_cost_proportion_pct": {
                "value": fixed_cost_pct,
                "is_known": fixed_cost_pct is not None,
                "unit": "%",
                "state": fixed_state,
                "label_ar": "نسبة التكاليف الثابتة من إجمالي المصاريف",
                "inputs_used": {"salaries": salaries, "rent": rent, "total_opex": opex},
            },
            "gross_margin": {
                "gross_profit": gross_profit,
                "margin_pct": gross_margin_pct,
                "unit": "%",
                "state": gm_state,
                "label_ar": "هامش الربح الإجمالي (Gross Margin)",
                "inputs_used": {"revenue": rev, "cogs": cogs},
            },
            "operating_margin": {
                "margin_pct": operating_margin_pct,
                "unit": "%",
                "state": op_margin_state,
                "label_ar": "هامش التشغيل الفعلي (Operating Margin)",
                "inputs_used": {"revenue": rev, "total_opex": opex},
            },
            "cac": cac_metric,
            "customer_acquisition_cost": cac_metric,
            "lifetime_value": {
                "value": None,
                "unit": "SAR",
                "state": "NOT_AVAILABLE",
                "label_ar": "القيمة الدائمة للعميل (LTV)",
                "reason_ar": "غير متوفر لعدم توفر معدلات الاحتفاظ والتسرب الفعلية على فترة زمنية كافية (يمنع التقدير الاصطناعي).",
            },
        },
        "missing_inputs": list(set(missing_inputs)),
        "calculation_version": CALCULATION_VERSION,
    }


# ==============================================================================
# 3. DETERMINISTIC BUSINESS HEALTH & RUNWAY ENGINE
# ==============================================================================

def calculate_actual_runway(launch_ws: Optional[models.LaunchWorkspace]) -> Dict[str, Any]:
    """Calculates cash runway reusing Wave 5 semantics:
    Requires explicit known cash balance + actual negative burn rate from net cashflow history.
    If burn cannot be determined: runway = NOT_AVAILABLE, status = NOT_AVAILABLE.
    """
    if not launch_ws or not launch_ws.actual_periods:
        return {
            "status": "NOT_AVAILABLE",
            "runway_months": None,
            "current_cash": None,
            "monthly_burn": None,
            "is_burning_cash": False,
            "reason_ar": "لا توجد دورات تشغيلية فعلية لتحديد معدل الحرق النقدي أو رصيد النقدية.",
        }

    periods = sorted(launch_ws.actual_periods, key=lambda x: x.period_order)
    latest = periods[-1]
    current_cash = latest.closing_cash_balance

    # Burn rate: Periods where net_cashflow (or revenue - opex) is negative
    cfs = []
    for p in periods:
        cf = p.net_cashflow
        if cf is None and p.actual_revenue is not None and p.total_actual_opex is not None:
            cf = round(p.actual_revenue - p.total_actual_opex, 2)
        if cf is not None:
            cfs.append(cf)

    monthly_burn: Optional[float] = None
    negative_cfs = [abs(cf) for cf in cfs if cf < 0]
    if negative_cfs:
        monthly_burn = round(sum(negative_cfs) / len(negative_cfs), 2)
    elif cfs:
        # All known periods have net_cashflow >= 0; burn rate is 0 (not burning cash)
        monthly_burn = 0.0

    if current_cash is None or monthly_burn is None:
        return {
            "status": "NOT_AVAILABLE",
            "runway_months": None,
            "current_cash": current_cash,
            "monthly_burn": monthly_burn,
            "is_burning_cash": False,
            "reason_ar": "يتطلب احتساب مدرج السيولة رصيد نقدية معلوم ومعدل حرق نقدي تاريخي محدد.",
        }

    if monthly_burn > 0:
        runway_months = round(current_cash / monthly_burn, 1)
        return {
            "status": "CALCULATED",
            "runway_months": runway_months,
            "current_cash": current_cash,
            "monthly_burn": monthly_burn,
            "is_burning_cash": True,
            "reason_ar": f"مدرج السيولة المتبقي {runway_months} أشهر استناداً إلى متوسط حرق شهري فعلي {monthly_burn:,.2f} ر.س.",
        }
    else:
        return {
            "status": "NOT_BURNING_CASH",
            "runway_months": None,
            "current_cash": current_cash,
            "monthly_burn": 0.0,
            "is_burning_cash": False,
            "reason_ar": "النشاط يحقق تدفقاً نقدياً موجباً أو متعادلاً ولا يعاني من حرق نقدي.",
        }


def evaluate_business_health(
    growth_ws_or_launch_ws: Any = None,
    launch_ws: Optional[models.LaunchWorkspace] = None,
) -> Dict[str, Any]:
    """Evaluates deterministic business health based strictly on actuals and approved baselines.
    
    Allowed States: HEALTHY, WATCH, AT_RISK, INSUFFICIENT_DATA.
    Missing data != poor performance. If key metrics are absent, state is INSUFFICIENT_DATA.
    No weighted arbitrary percentage scores.
    """
    target_launch_ws = launch_ws
    if target_launch_ws is None:
        if isinstance(growth_ws_or_launch_ws, models.LaunchWorkspace):
            target_launch_ws = growth_ws_or_launch_ws
        elif isinstance(growth_ws_or_launch_ws, models.GrowthWorkspace):
            db = Session.object_session(growth_ws_or_launch_ws)
            if db:
                target_launch_ws = db.query(models.LaunchWorkspace).filter_by(study_id=growth_ws_or_launch_ws.study_id).first()

    if not target_launch_ws or not target_launch_ws.actual_periods:
        return {
            "overall_state": HEALTH_INSUFFICIENT_DATA,
            "overall_state_ar": "بيانات غير كافية (لم يتم تسجيل أداء فعلي بعد)",
            "health_state": HEALTH_INSUFFICIENT_DATA,
            "health_name_ar": "بيانات غير كافية (لم يتم تسجيل أداء فعلي بعد)",
            "summary_ar": "لا توجد دورات تشغيلية فعلية مرصودة في مساحة الإطلاق لتقييم صحة الأعمال.",
            "health_summary_ar": "لا توجد دورات تشغيلية فعلية مرصودة في مساحة الإطلاق لتقييم صحة الأعمال.",
            "recommendation_ar": "استكمال تسجيل البيانات التشغيلية للدورة القادمة في مساحة الإطلاق لتفعيل التحليل الكامل.",
            "factors": [],
            "missing_inputs": ["actual_periods"],
            "calculation_version": CALCULATION_VERSION,
        }

    periods = sorted(target_launch_ws.actual_periods, key=lambda x: x.period_order)
    latest_p = periods[-1]
    prev_p = periods[-2] if len(periods) >= 2 else None

    factors = []
    has_insufficient = False
    critical_risks = 0
    watch_count = 0

    # 1. Revenue Trajectory
    if prev_p and latest_p.actual_revenue is not None and prev_p.actual_revenue is not None:
        rev_diff = latest_p.actual_revenue - prev_p.actual_revenue
        if rev_diff > 0:
            res = "POSITIVE"
            reason = f"الإيرادات في نمو إيجابي (زيادة بمقدار {rev_diff:,.2f} ر.س عن الدورة السابقة)."
        elif rev_diff < 0:
            res = "WARNING"
            watch_count += 1
            reason = f"تراجع الإيرادات بمقدار {abs(rev_diff):,.2f} ر.س مقارنة بالدورة السابقة."
        else:
            res = "NEUTRAL"
            reason = "الإيرادات مستقرة تماماً ومطابقة للدورة السابقة."
        factors.append({
            "metric": "revenue_growth",
            "metric_name_ar": "مسار نمو الإيراد الفعلي",
            "current_value": latest_p.actual_revenue,
            "comparison_value": prev_p.actual_revenue,
            "comparison_period": prev_p.period_label,
            "result": res,
            "reason": reason,
            "data_source": latest_p.source_type,
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })
    elif latest_p.actual_revenue is not None:
        factors.append({
            "metric": "revenue_growth",
            "metric_name_ar": "مسار نمو الإيراد الفعلي",
            "current_value": latest_p.actual_revenue,
            "comparison_value": None,
            "comparison_period": None,
            "result": "INSUFFICIENT_DATA",
            "reason": "توجد دورة فعلية واحدة فقط، يلزم دورتان على الأقل لقياس النمو المقارن.",
            "data_source": latest_p.source_type,
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })
    else:
        has_insufficient = True
        factors.append({
            "metric": "revenue_growth",
            "metric_name_ar": "مسار نمو الإيراد الفعلي",
            "current_value": None,
            "comparison_value": None,
            "result": "INSUFFICIENT_DATA",
            "reason": "قيمة الإيراد الفعلي للدورة الحالية غير مسجلة.",
            "data_source": "UNKNOWN",
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })

    # 2. Net Cash Flow
    net_cf = latest_p.net_cashflow
    if net_cf is None and latest_p.actual_revenue is not None and latest_p.total_actual_opex is not None:
        net_cf = round(latest_p.actual_revenue - latest_p.total_actual_opex, 2)

    if net_cf is not None:
        if net_cf > 0:
            res = "POSITIVE"
            reason = f"تدفق نقدي تشغيلي موجب بمقدار {net_cf:,.2f} ر.س."
        elif net_cf < 0:
            res = "NEGATIVE"
            critical_risks += 1
            reason = f"حرق نقدي صافٍ (تدفق سالب) بمقدار {net_cf:,.2f} ر.س."
        else:
            res = "NEUTRAL"
            reason = "صافي التدفق النقدي عند نقطة التعادل التام (0.00 ر.س)."
        factors.append({
            "metric": "net_cashflow",
            "metric_name_ar": "صافي التدفق النقدي",
            "current_value": net_cf,
            "comparison_value": 0.0,
            "comparison_period": "نقطة التعادل",
            "result": res,
            "reason": reason,
            "data_source": latest_p.source_type,
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })
    else:
        has_insufficient = True
        factors.append({
            "metric": "net_cashflow",
            "metric_name_ar": "صافي التدفق النقدي",
            "current_value": None,
            "comparison_value": None,
            "result": "INSUFFICIENT_DATA",
            "reason": "لم يتم احتساب التدفق النقدي لغياب بيانات الإيراد أو النفقات التشغيلية.",
            "data_source": "UNKNOWN",
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })

    # 3. Cash Position & Runway (reusing Wave 5 burn-rate semantics)
    runway_info = calculate_actual_runway(target_launch_ws)
    cash_bal = latest_p.closing_cash_balance
    if runway_info["status"] == "CALCULATED":
        runway = runway_info["runway_months"]
        if runway < 1.5:
            res = "CRITICAL"
            critical_risks += 1
            reason = f"مخاطر سيولة مرتفعة: مدرج السيولة المتبقي {runway} أشهر فقط (أقل من 1.5 شهر استناداً لمعدل الحرق الفعلي)."
        elif runway < 3.0:
            res = "WARNING"
            watch_count += 1
            reason = f"مدرج السيولة متحفظ: {runway} أشهر حرق نقدي (بين 1.5 شهر و 3 أشهر)."
        else:
            res = "POSITIVE"
            reason = f"مدرج سيولة مريح: يغطي {runway} أشهر من معدل الحرق النقدي الفعلي."
        factors.append({
            "metric": "cash_runway",
            "metric_name_ar": "مدرج السيولة المتبقي (أشهر)",
            "current_value": runway,
            "comparison_value": 3.0,
            "comparison_period": "الحد الآمن (3 أشهر)",
            "result": res,
            "reason": reason,
            "data_source": latest_p.source_type,
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })
    elif runway_info["status"] == "NOT_BURNING_CASH":
        factors.append({
            "metric": "cash_runway",
            "metric_name_ar": "مدرج السيولة المتبقي (أشهر)",
            "current_value": None,
            "comparison_value": 3.0,
            "comparison_period": "الحد الآمن",
            "result": "POSITIVE",
            "reason": "النشاط يحقق تدفقاً نقدياً موجباً أو متعادلاً ولا يوجد حرق نقدي.",
            "data_source": latest_p.source_type,
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })
    elif cash_bal is not None:
        factors.append({
            "metric": "cash_balance",
            "metric_name_ar": "رصيد النقدية الختامي",
            "current_value": cash_bal,
            "comparison_value": None,
            "comparison_period": None,
            "result": "RECORDED",
            "reason": f"الرصيد النقدي الفعلي المسجل هو {cash_bal:,.2f} ر.س (المدرج غير متاح لعدم توفر تاريخ حرق نقدي).",
            "data_source": latest_p.source_type,
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })
    else:
        has_insufficient = True
        factors.append({
            "metric": "cash_runway",
            "metric_name_ar": "مدرج السيولة النقدية",
            "current_value": None,
            "comparison_value": None,
            "result": "INSUFFICIENT_DATA",
            "reason": runway_info["reason_ar"],
            "data_source": "UNKNOWN",
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })

    # 4. Forecast vs Actual Variance Alert
    variances = evaluate_workspace_variances(target_launch_ws)
    var_alert = variances.get("overall_health")
    if var_alert == "MATERIAL_VARIANCE":
        critical_risks += 1
        factors.append({
            "metric": "forecast_variance",
            "metric_name_ar": "انحراف التوقعات عن الفعلي",
            "current_value": "MATERIAL_VARIANCE",
            "comparison_value": "NORMAL",
            "comparison_period": "خطة العمل",
            "result": "CRITICAL",
            "reason": "يوجد انحراف مالي جوهري يتجاوز 25% مقارنة بخط الأساس المعتمد.",
            "data_source": "Launch Variance Engine",
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })
    elif var_alert == "WATCH":
        watch_count += 1
        factors.append({
            "metric": "forecast_variance",
            "metric_name_ar": "انحراف التوقعات عن الفعلي",
            "current_value": "WATCH",
            "comparison_value": "NORMAL",
            "comparison_period": "خطة العمل",
            "result": "WARNING",
            "reason": "انحراف متوسط بين 10% و 25% مقارنة بخطة العمل التقديرية.",
            "data_source": "Launch Variance Engine",
            "data_period": latest_p.period_label,
            "calculation_version": CALCULATION_VERSION,
        })

    # Overall State Determination
    if has_insufficient and len([f for f in factors if f["result"] in ("POSITIVE", "NEGATIVE", "WARNING", "CRITICAL")]) < 2:
        overall_state = HEALTH_INSUFFICIENT_DATA
        overall_ar = "بيانات غير كافية لتقييم صحة الأعمال"
        summary_ar = "البيانات الفعلية المدخلة غير كافية لإصدار تقييم قطعي لصحة المنشأة. نقص البيانات لا يعني تعثراً."
    elif critical_risks >= 2 or (critical_risks == 1 and watch_count >= 1):
        overall_state = HEALTH_AT_RISK
        overall_ar = "نشاط تحت المخاطر (AT_RISK)"
        summary_ar = "توجد مؤشرات مالية حرجة تتعلق بعجز التدفق النقدي أو سرعة حرق السيولة النقدية أو الانحراف الجوهري."
    elif critical_risks == 1 or watch_count >= 1:
        overall_state = HEALTH_WATCH
        overall_ar = "قيد المراقبة والتحفظ (WATCH)"
        summary_ar = "الأداء العام مستمر مع وجود نقاط انتباه تشغيلية تستدعي ترشيد المصاريف وتحسين التحصيل."
    else:
        overall_state = HEALTH_HEALTHY
        overall_ar = "نشاط سليم ومستقر (HEALTHY)"
        summary_ar = "المؤشرات المالية والتشغيلية تسير ضمن المسار الإيجابي أو المستقر وتوفر تدفقاً نقدياً كافياً."

    recommendation_ar = "المحافظة على مسار الأداء وتوثيق الدروس المستفادة."
    if overall_state == HEALTH_INSUFFICIENT_DATA:
        recommendation_ar = "استكمال تسجيل البيانات التشغيلية للدورة القادمة في مساحة الإطلاق لتفعيل التحليل الكامل."
    elif overall_state == HEALTH_AT_RISK:
        recommendation_ar = "تفعيل خطة معالجة عاجلة (FIX) لخفض المصاريف غير الضرورية وتأمين السيولة المطلوبة."
    elif overall_state == HEALTH_WATCH:
        recommendation_ar = "مراقبة مسار الإيراد وترشيد المصاريف التشغيلية لتجنب تآكل مدرج السيولة."

    return {
        "overall_state": overall_state,
        "overall_state_ar": overall_ar,
        "health_state": overall_state,
        "health_name_ar": overall_ar,
        "summary_ar": summary_ar,
        "health_summary_ar": summary_ar,
        "recommendation_ar": recommendation_ar,
        "critical_risks_count": critical_risks,
        "watch_count": watch_count,
        "factors": factors,
        "calculation_version": CALCULATION_VERSION,
    }


# ==============================================================================
# 4. DETERMINISTIC RISK DETECTION ENGINE
# ==============================================================================

def detect_growth_risks(
    launch_ws: Optional[models.LaunchWorkspace],
) -> List[Dict[str, Any]]:
    """Transparent rule-based risk detection across CASH, MARGIN, REVENUE, COST, CUSTOMER,
    FORECAST_VARIANCE, CAPACITY, FUNDING, EXECUTION, and DATA_QUALITY.
    
    Levels: LOW, WATCH, HIGH, UNKNOWN.
    Missing input strictly results in UNKNOWN.
    """
    risks = []
    if not launch_ws or not launch_ws.actual_periods:
        return [
            {
                "category": "DATA_QUALITY",
                "risk_type": "DATA_INCOMPLETENESS",
                "risk_title_ar": "غياب البيانات الفعلية",
                "level": RISK_UNKNOWN,
                "trigger": "NO_ACTUAL_PERIODS",
                "input_value": None,
                "threshold_rule": "at least 1 recorded operational actual period",
                "reason_ar": "لم يتم تسجيل دورات أداء فعلية بعد في مساحة الإطلاق.",
                "period": None,
                "source": "Launch Workspace",
                "calculation_version": CALCULATION_VERSION,
            }
        ]

    periods = sorted(launch_ws.actual_periods, key=lambda x: x.period_order)
    latest = periods[-1]
    prev = periods[-2] if len(periods) >= 2 else None

    # Risk 1: CASH Runway Risk (reusing Wave 5 burn-rate semantics)
    runway_info = calculate_actual_runway(launch_ws)
    if runway_info["status"] == "NOT_AVAILABLE":
        risks.append({
            "category": "CASH",
            "risk_type": "CASH_RUNWAY_DEPLETION",
            "risk_title_ar": "مخاطر استنزاف السيولة النقدية ومدرج التشغيل",
            "level": RISK_UNKNOWN,
            "trigger": "CASH_RUNWAY_MONTHS",
            "input_value": None,
            "status": "NOT_AVAILABLE",
            "threshold_rule": "requires closing_cash_balance and historical net cashflow burn rate",
            "reason_ar": runway_info["reason_ar"],
            "period": latest.period_label,
            "source": "UNKNOWN",
            "calculation_version": CALCULATION_VERSION,
        })
    elif runway_info["status"] == "NOT_BURNING_CASH":
        risks.append({
            "category": "CASH",
            "risk_type": "CASH_RUNWAY_DEPLETION",
            "risk_title_ar": "مخاطر استنزاف السيولة النقدية ومدرج التشغيل",
            "level": RISK_LOW,
            "trigger": "CASH_RUNWAY_MONTHS",
            "input_value": None,
            "status": "NOT_BURNING_CASH",
            "threshold_rule": "no cash burn detected (net cashflow >= 0)",
            "reason_ar": runway_info["reason_ar"],
            "period": latest.period_label,
            "source": latest.source_type,
            "calculation_version": CALCULATION_VERSION,
        })
    else:
        runway = runway_info["runway_months"]
        if runway < 2.0:
            lvl = RISK_HIGH
            reason = f"رصيد النقدية الحالي يغطي أقل من شهرين ({runway} شهر) استناداً إلى متوسط الحرق الشهري الفعلي ({runway_info['monthly_burn']:,.2f} ر.س)."
        elif runway < 3.0:
            lvl = RISK_WATCH
            reason = f"رصيد النقدية يغطي {runway} أشهر، وهو أقل من عازل الأمان الموصى به (3 أشهر)."
        else:
            lvl = RISK_LOW
            reason = f"مدرج السيولة آمن ({runway} أشهر تغطية حرق نقدي)."
        risks.append({
            "category": "CASH",
            "risk_type": "CASH_RUNWAY_DEPLETION",
            "risk_title_ar": "مخاطر استنزاف السيولة النقدية ومدرج التشغيل",
            "level": lvl,
            "trigger": "CASH_RUNWAY_MONTHS",
            "input_value": runway,
            "status": "CALCULATED",
            "threshold_rule": "HIGH: < 2.0 months | WATCH: < 3.0 months | LOW: >= 3.0 months",
            "reason_ar": reason,
            "period": latest.period_label,
            "source": latest.source_type,
            "calculation_version": CALCULATION_VERSION,
        })

    # Risk 2: Fixed Cost Overhang (> 70% of total opex)
    # Missing salary or rent input strictly results in UNKNOWN
    salaries = latest.actual_opex_salaries
    rent = latest.actual_opex_rent
    opex = latest.total_actual_opex
    if salaries is None or rent is None or opex is None or opex <= 0:
        risks.append({
            "category": "COST",
            "risk_type": "FIXED_COST_OVERHANG",
            "risk_title_ar": "تضخم التكاليف الثابتة التشغيلية",
            "level": RISK_UNKNOWN,
            "trigger": "FIXED_COSTS_PROPORTION_PCT",
            "input_value": None,
            "threshold_rule": "FIXED_COST_OVERHANG: (salaries + rent) / opex > 70%",
            "reason_ar": "بيانات الرواتب أو الإيجار أو إجمالي المصروفات غير مكتملة في الدورة الأخيرة.",
            "period": latest.period_label,
            "source": "UNKNOWN",
            "calculation_version": CALCULATION_VERSION,
        })
    else:
        fixed_costs = salaries + rent
        fixed_pct = round((fixed_costs / opex) * 100, 1)
        if (fixed_costs / opex) > 0.70:
            lvl = RISK_HIGH if fixed_pct > 80.0 else RISK_WATCH
            reason = f"تشكل التكاليف الثابتة (الرواتب والإيجار) {fixed_pct}% من إجمالي المصروفات التشغيلية."
        else:
            lvl = RISK_LOW
            reason = f"نسبة التكاليف الثابتة في النطاق الآمن ({fixed_pct}% من إجمالي المصروفات)."
        risks.append({
            "category": "COST",
            "risk_type": "FIXED_COST_OVERHANG",
            "risk_title_ar": "تضخم التكاليف الثابتة التشغيلية",
            "level": lvl,
            "trigger": "FIXED_COSTS_PROPORTION_PCT",
            "input_value": fixed_pct,
            "threshold_rule": "FIXED_COST_OVERHANG: (salaries + rent) / opex > 70%",
            "reason_ar": reason,
            "period": latest.period_label,
            "source": latest.source_type,
            "calculation_version": CALCULATION_VERSION,
        })

    # Risk 3: REVENUE Trend Risk
    # If previous revenue was zero, percentage_change=None, level=UNKNOWN
    if prev and latest.actual_revenue is not None and prev.actual_revenue is not None:
        if prev.actual_revenue <= 0:
            risks.append({
                "category": "REVENUE",
                "risk_type": "REVENUE_CONTRACTION",
                "risk_title_ar": "مخاطر تراجع وتذبذب الإيرادات",
                "level": RISK_UNKNOWN,
                "trigger": "REVENUE_GROWTH_PCT",
                "input_value": None,
                "percentage_change": None,
                "threshold_rule": "HIGH: < -15% | WATCH: < 0% | LOW: >= 0% (requires prev revenue > 0)",
                "reason_ar": "إيرادات الدورة السابقة كانت صفراً؛ لا يمكن احتساب نسبة نمو ذات دلالة إحصائية.",
                "period": latest.period_label,
                "source": latest.source_type,
                "calculation_version": CALCULATION_VERSION,
            })
        else:
            rev_change_pct = round(((latest.actual_revenue - prev.actual_revenue) / prev.actual_revenue) * 100, 1)
            if rev_change_pct < -15.0:
                lvl = RISK_HIGH
                reason = f"تراجع حاد في الإيرادات بنسبة {abs(rev_change_pct):.1f}% مقارنة بالدورة السابقة."
            elif rev_change_pct < 0.0:
                lvl = RISK_WATCH
                reason = f"تراجع طفيف في الإيرادات بنسبة {abs(rev_change_pct):.1f}%."
            else:
                lvl = RISK_LOW
                reason = f"الإيرادات تنمو بمعدل إيجابي (+{rev_change_pct:.1f}%)."
            risks.append({
                "category": "REVENUE",
                "risk_type": "REVENUE_CONTRACTION",
                "risk_title_ar": "مخاطر تراجع وتذبذب الإيرادات",
                "level": lvl,
                "trigger": "REVENUE_GROWTH_PCT",
                "input_value": rev_change_pct,
                "percentage_change": rev_change_pct,
                "threshold_rule": "HIGH: < -15% | WATCH: < 0% | LOW: >= 0%",
                "reason_ar": reason,
                "period": latest.period_label,
                "source": latest.source_type,
                "calculation_version": CALCULATION_VERSION,
            })
    else:
        risks.append({
            "category": "REVENUE",
            "risk_type": "REVENUE_CONTRACTION",
            "risk_title_ar": "مخاطر تراجع وتذبذب الإيرادات",
            "level": RISK_UNKNOWN,
            "trigger": "REVENUE_GROWTH_PCT",
            "input_value": None,
            "percentage_change": None,
            "threshold_rule": "requires at least 2 comparable revenue periods",
            "reason_ar": "لا تتوفر دورتان متتاليتان بإيرادات معلومة لاحتساب نسبة التغير بدقة.",
            "period": latest.period_label,
            "source": "UNKNOWN",
            "calculation_version": CALCULATION_VERSION,
        })

    # Risk 4: FORECAST_VARIANCE Risk
    variances = evaluate_workspace_variances(launch_ws)
    var_alert = variances.get("overall_health")
    if var_alert == "MATERIAL_VARIANCE":
        lvl = RISK_HIGH
        reason = "انحراف مالي فعلي جوهري يتجاوز 25% مقارنة بخطة العمل التقديرية."
    elif var_alert == "WATCH":
        lvl = RISK_WATCH
        reason = "انحراف متوسط بين 10% و 25% مقارنة بالتقديرات المعتمدة."
    elif var_alert == "NORMAL":
        lvl = RISK_LOW
        reason = "الأداء الفعلي يتطابق مع خطة العمل بهامش انحراف ضمن الحدود الطبيعية (< 10%)."
    else:
        lvl = RISK_UNKNOWN
        reason = "بيانات المقارنة بين خط الأساس المعتمد والفعلي غير متوفرة بالكامل."

    risks.append({
        "category": "FORECAST_VARIANCE",
        "risk_type": "MATERIAL_FORECAST_VARIANCE",
        "risk_title_ar": "مخاطر الانحراف التراكمي عن الخطة المعتمدة",
        "level": lvl,
        "trigger": "FORECAST_VS_ACTUAL_VARIANCE",
        "input_value": var_alert,
        "threshold_rule": "HIGH: MATERIAL_VARIANCE (>25%) | WATCH: WATCH (10-25%) | LOW: NORMAL (<10%)",
        "reason_ar": reason,
        "period": latest.period_label,
        "source": "Launch Variance Summary",
        "calculation_version": CALCULATION_VERSION,
    })

    # Risk 5: EXECUTION / Operational Blockers
    blocked_milestones = [m for m in launch_ws.milestones if m.status == "BLOCKED"]
    blocked_tasks = [t for t in launch_ws.tasks if t.status == "BLOCKED"]
    if blocked_milestones or blocked_tasks:
        lvl = RISK_HIGH if blocked_milestones else RISK_WATCH
        risks.append({
            "category": "EXECUTION",
            "risk_type": "OPERATIONAL_EXECUTION_BLOCKERS",
            "risk_title_ar": "معطلات تشغيلية وتنفيذية معلقة",
            "level": lvl,
            "trigger": "BLOCKED_ITEMS_COUNT",
            "input_value": len(blocked_milestones) + len(blocked_tasks),
            "threshold_rule": "HIGH: blocked milestones > 0 | WATCH: blocked tasks > 0",
            "reason_ar": f"يوجد {len(blocked_milestones)} معالم معطلة و {len(blocked_tasks)} مهام متعثرة في مسار التنفيذ.",
            "period": latest.period_label,
            "source": "Launch Milestones & Tasks",
            "calculation_version": CALCULATION_VERSION,
        })
    else:
        risks.append({
            "category": "EXECUTION",
            "risk_type": "OPERATIONAL_EXECUTION_BLOCKERS",
            "risk_title_ar": "معطلات تشغيلية وتنفيذية معلقة",
            "level": RISK_LOW,
            "trigger": "BLOCKED_ITEMS_COUNT",
            "input_value": 0,
            "threshold_rule": "HIGH: blocked milestones > 0 | WATCH: blocked tasks > 0",
            "reason_ar": "لا توجد معالم أو مهام تنفيذية معطلة في خطة الإطلاق والتشغيل.",
            "period": latest.period_label,
            "source": "Launch Milestones & Tasks",
            "calculation_version": CALCULATION_VERSION,
        })

    return risks


# ==============================================================================
# 5. DETERMINISTIC EXPANSION READINESS ENGINE
# ==============================================================================

def evaluate_expansion_readiness(
    growth_ws: models.GrowthWorkspace,
    launch_ws: Optional[models.LaunchWorkspace],
    scenario: Optional[models.GrowthScenario] = None,
) -> Dict[str, Any]:
    """Evaluates transparent expansion readiness prerequisites across 5 standard codes:
    OPERATING_STABILITY, RUNWAY_ADEQUACY, UNIT_ECONOMICS, CAPACITY_UTILIZATION, DATA_COMPLETENESS.
    
    Allowed States: READY, CONDITIONALLY_READY, NOT_READY, NEEDS_INFORMATION.
    Every prerequisite returns PASS, FAIL, UNKNOWN, or NOT_APPLICABLE with reason.
    Hard blocker produces NOT_READY.
    Critical UNKNOWN must produce NEEDS_INFORMATION.
    No arbitrary percentage score.
    """
    prereqs = []
    hard_blockers = 0
    critical_unknowns = 0
    passes = 0

    study = growth_ws.study if growth_ws else None
    periods = launch_ws.actual_periods if launch_ws else []
    periods_count = len(periods)
    latest_p = periods[-1] if periods else None

    # 1. OPERATING_STABILITY
    blocked_count = len([m for m in (launch_ws.milestones if launch_ws else []) if m.status == "BLOCKED"])
    if not launch_ws:
        p_status = PREREQ_UNKNOWN
        critical_unknowns += 1
        p_reason = "مساحة الإطلاق غير مهيأة بعد لتقييم الاستقرار التشغيلي."
    elif blocked_count == 0:
        p_status = PREREQ_PASS
        passes += 1
        p_reason = "لا توجد أي معالم تشغيلية أو نظامية معطلة في مسار التنفيذ."
    else:
        p_status = PREREQ_FAIL
        hard_blockers += 1
        p_reason = f"يوجد {blocked_count} معالم تشغيلية معطلة يجب إغلاقها أولاً."
    prereqs.append({
        "code": "OPERATING_STABILITY",
        "key": "operating_stability",
        "name_ar": "استقرار العمليات وغياب المعطلات الجوهرية",
        "status": p_status,
        "is_critical": True,
        "reason_ar": p_reason,
    })

    # 2. RUNWAY_ADEQUACY (reusing Wave 5 burn-rate semantics)
    runway_info = calculate_actual_runway(launch_ws)
    if runway_info["status"] == "NOT_AVAILABLE":
        p_status = PREREQ_UNKNOWN
        critical_unknowns += 1
        p_reason = runway_info["reason_ar"]
    elif runway_info["status"] == "NOT_BURNING_CASH":
        p_status = PREREQ_PASS
        passes += 1
        p_reason = "النشاط يحقق تدفقاً نقدياً موجباً أو متعادلاً (لا يوجد حرق نقدي)، ومدرج السيولة آمن."
    else:
        runway = runway_info["runway_months"]
        if runway >= 3.0:
            p_status = PREREQ_PASS
            passes += 1
            p_reason = f"رصيد النقدية يوفر مدرج أمان مريح للتوسع استناداً إلى الحرق الشهري ({runway} أشهر)."
        elif runway >= 2.0:
            p_status = PREREQ_FAIL
            p_reason = f"مدرج السيولة محدود ({runway} أشهر حرق نقدي)، مما قد يعرض النشاط لعجز نقدي في حال التوسع."
        else:
            p_status = PREREQ_FAIL
            hard_blockers += 1
            p_reason = f"مدرج السيولة حرج جداً ({runway} أشهر حرق نقدي)، يمنع التوسع قبل تأمين سيولة كافية."
    prereqs.append({
        "code": "RUNWAY_ADEQUACY",
        "key": "runway_adequacy",
        "name_ar": "كفاية مدرج السيولة النقدية (3 أشهر فأكثر)",
        "status": p_status,
        "is_critical": True,
        "reason_ar": p_reason,
    })

    # 3. UNIT_ECONOMICS
    if not latest_p:
        p_status = PREREQ_UNKNOWN
        critical_unknowns += 1
        p_reason = "لم يتم تسجيل أي دورة تشغيلية فعلية لقياس اقتصاديات الوحدة."
    else:
        rev = latest_p.actual_revenue
        opex = latest_p.total_actual_opex
        cogs = latest_p.actual_opex_cogs
        if rev is not None and opex is not None:
            if rev >= opex:
                p_status = PREREQ_PASS
                passes += 1
                p_reason = f"النشاط يحقق أرباحاً تشغيلية فعلية (إيراد {rev:,.2f} مقابل نفقات {opex:,.2f} ر.س)."
            elif cogs is not None and rev > cogs:
                p_status = PREREQ_PASS
                passes += 1
                p_reason = "هامش المساهمة موجب ويغطي التكاليف المباشرة."
            else:
                p_status = PREREQ_FAIL
                hard_blockers += 1
                p_reason = "عجز تشغيلي أو هوامش سلبية غير مواتية للتوسع."
        else:
            p_status = PREREQ_UNKNOWN
            critical_unknowns += 1
            p_reason = "بيانات الإيراد الفعلي أو إجمالي المصاريف التشغيلية غير مكتملة."
    prereqs.append({
        "code": "UNIT_ECONOMICS",
        "key": "unit_economics",
        "name_ar": "صحة وهوامش اقتصاديات الوحدة",
        "status": p_status,
        "is_critical": True,
        "reason_ar": p_reason,
    })

    # 4. CAPACITY_UTILIZATION
    # Do not mark CAPACITY_UTILIZATION = PASS merely because actual periods exist.
    # Without explicit capacity/capacity-utilization evidence, return UNKNOWN or NOT_APPLICABLE.
    # For capacity-sensitive SCALE scenarios, unknown capacity must remain visible and must not silently PASS.
    assumptions_map = {
        a.key: a.value_number
        for a in (study.study_assumptions if study and study.study_assumptions else [])
        if a.is_active
    }
    cap_util = (
        assumptions_map.get("capacity_utilization")
        or assumptions_map.get("capacity_utilization_rate")
        or assumptions_map.get("capacity_rate")
    )
    profile = getattr(study, "business_profile", None) if study else None
    profile_cap = profile.capacity_value if profile else None
    scen_cap = (scenario.capacity_assumptions or {}) if scenario else {}
    target_cap_increase = scen_cap.get("target_capacity_increase_pct") if scen_cap else getattr(scenario, "target_capacity_increase_pct", None)
    industry = getattr(study, "industry", None) if study else None
    is_digital_service = industry in ("software", "fintech", "consulting", "digital_services")

    is_capacity_sensitive_scenario = (
        scenario is not None
        and (
            scenario.scenario_type in ("CAPACITY_EXPANSION", "NEW_BRANCH", "NEW_PRODUCT", "NEW_SERVICE", "FRANCHISE_EXPANSION")
            or bool(scen_cap)
            or (target_cap_increase is not None and target_cap_increase > 0)
        )
    )

    cap_is_critical = False
    if cap_util is not None:
        if 40.0 <= cap_util <= 85.0:
            p_status = PREREQ_PASS
            passes += 1
            p_reason = f"معدل استغلال الطاقة الاستيعابية مثبت بنسبة {cap_util:.1f}%، ضمن النطاق المقبول للتوسع."
        elif cap_util > 85.0:
            p_status = PREREQ_PASS
            passes += 1
            p_reason = f"معدل استغلال الطاقة الاستيعابية مرتفع ({cap_util:.1f}%)؛ التوسع يسهم في فك الاختناق التشغيلي."
        else:
            p_status = PREREQ_FAIL
            hard_blockers += 1
            p_reason = f"معدل استغلال الطاقة الاستيعابية منخفض حالياً ({cap_util:.1f}%)؛ التوسع غير مبرر قبل تحسين الاستغلال."
    elif profile_cap is not None and profile_cap > 0:
        p_status = PREREQ_PASS
        passes += 1
        unit_str = f" {profile.capacity_unit}" if profile.capacity_unit else " وحدة"
        p_reason = f"الطاقة الاستيعابية موثقة في ملف المنشأة ({profile_cap:,.0f}{unit_str})."
    elif scen_cap.get("verified_utilization_rate") is not None:
        v_rate = float(scen_cap["verified_utilization_rate"])
        p_status = PREREQ_PASS
        passes += 1
        p_reason = f"معدل استغلال الطاقة مثبت في سيناريو النمو بنسبة {v_rate:.1f}%."
    elif is_digital_service:
        p_status = "NOT_APPLICABLE"
        p_reason = "طبيعة النشاط الرقمي/الخدمي غير مقيدة بطاقة استيعابية مكانية محددة."
    else:
        # Without explicit capacity evidence, status remains UNKNOWN
        p_status = PREREQ_UNKNOWN
        if is_capacity_sensitive_scenario and scenario and scenario.scenario_type == "CAPACITY_EXPANSION":
            cap_is_critical = True
            critical_unknowns += 1
            p_reason = "سيناريو توسعة الطاقة الاستيعابية (CAPACITY_EXPANSION) يتطلب توثيق بيانات الطاقة الحالية؛ الطاقة مجهولة حالياً."
        elif is_capacity_sensitive_scenario:
            p_reason = f"سيناريو التوسع ({scenario.title if scenario else ''}) حساس للطاقة ولكن لم تسجل بيانات استغلال الطاقة؛ تبقى الحالة مجهولة (UNKNOWN)."
        else:
            p_reason = "لم تسجل أدلة أو بيانات موثقة عن معدل استغلال الطاقة الاستيعابية؛ تبقى الحالة مجهولة (UNKNOWN)."

    prereqs.append({
        "code": "CAPACITY_UTILIZATION",
        "key": "capacity_utilization",
        "name_ar": "استيعاب وجاهزية الطاقة التشغيلية",
        "status": p_status,
        "is_critical": cap_is_critical,
        "reason_ar": p_reason,
    })

    # 5. DATA_COMPLETENESS
    if periods_count == 0:
        p_status = PREREQ_UNKNOWN
        critical_unknowns += 1
        p_reason = "لم يتم تسجيل أي دورة تشغيلية فعلية حتى الآن."
    elif periods_count >= 2:
        p_status = PREREQ_PASS
        passes += 1
        p_reason = f"تاريخ تشغيلي فعلي كافٍ ومكتمل ({periods_count} دورات مسجلة)."
    else:
        p_status = PREREQ_FAIL
        hard_blockers += 1
        p_reason = f"فترة التشغيل غير كافية للتوسع ({periods_count} دورة فقط؛ يلزم دورتان على الأقل)."
    prereqs.append({
        "code": "DATA_COMPLETENESS",
        "key": "data_completeness",
        "name_ar": "اكتمال سجل الأداء التاريخي",
        "status": p_status,
        "is_critical": True,
        "reason_ar": p_reason,
    })

    # Overall Readiness State (Hard blockers ALWAYS override unknowns)
    if hard_blockers > 0:
        readiness_state = READINESS_NOT_READY
        readiness_ar = "غير جاهز للتوسع حالياً (NOT_READY)"
        summary_ar = "توجد معطلات صريحة أو عجز في مدرج السيولة أو تراجع في الإيرادات يستوجب المعالجة أولاً."
    elif critical_unknowns > 0:
        readiness_state = READINESS_NEEDS_INFO
        readiness_ar = "يلزم استكمال البيانات (NEEDS_INFORMATION)"
        summary_ar = "توجد متطلبات جوهرية غير معلومة تمنع تقييم الجاهزية للتوسع بموثوقية."
    elif passes == len(prereqs):
        readiness_state = READINESS_READY
        readiness_ar = "جاهز للتوسع المدروس (READY)"
        summary_ar = "النشاط يحقق كافة المتطلبات المسبقة: استقرار الإيرادات، تاريخ تشغيلي كافٍ، ومدرج سيولة مريح."
    else:
        readiness_state = READINESS_CONDITIONALLY_READY
        readiness_ar = "جاهز بشروط محددة (CONDITIONALLY_READY)"
        summary_ar = "يمكن البدء في التوسع بشرط الالتزام بضوابط السيولة وإدارة تكاليف الاستثمار."

    return {
        "readiness_state": readiness_state,
        "readiness_state_ar": readiness_ar,
        "summary_ar": summary_ar,
        "prerequisites": prereqs,
        "passes_count": passes,
        "hard_blockers_count": hard_blockers,
        "critical_unknowns_count": critical_unknowns,
        "calculation_version": CALCULATION_VERSION,
    }


# ==============================================================================
# 6. GROWTH FUNDING CONTEXT (Wave 2 Integration)
# ==============================================================================

def get_growth_funding_context(
    study_or_growth_ws: Any,
    launch_ws: Optional[models.LaunchWorkspace] = None,
    scenario: Optional[models.GrowthScenario] = None,
) -> Dict[str, Any]:
    """Synthesizes Growth Funding Context by integrating Wave 2 services without logic duplication.
    
    Rules:
    - Potential funding != cash.
    - Program match != approved financing.
    - Separates: current available cash, growth investment need, confirmed funding, potential funding capacity, funding gap.
    - Unknown capacity remains UNKNOWN.
    - Unknown funding values are never coerced to 0.0.
    """
    if isinstance(study_or_growth_ws, models.GrowthWorkspace):
        growth_ws = study_or_growth_ws
        study = growth_ws.study
        if launch_ws is None:
            db = Session.object_session(growth_ws)
            if db:
                launch_ws = db.query(models.LaunchWorkspace).filter_by(study_id=growth_ws.study_id).first()
    elif isinstance(study_or_growth_ws, models.FeasibilityStudy):
        study = study_or_growth_ws
        growth_ws = None
    else:
        study = getattr(study_or_growth_ws, "study", study_or_growth_ws)
        growth_ws = None

    # Current cash from latest actuals
    latest_p = sorted(launch_ws.actual_periods, key=lambda x: x.period_order)[-1] if (launch_ws and launch_ws.actual_periods) else None
    cash_on_hand = latest_p.closing_cash_balance if latest_p else None

    # Growth investment required from proposed scenario
    growth_investment = scenario.investment_required if scenario else None

    # Wave 2 context: Owner capital & confirmed facilities from study assumptions
    assumptions_map = {a.key: a.value_number for a in study.study_assumptions if a.is_active} if (study and study.study_assumptions) else {}
    owner_equity = assumptions_map.get("owner_contribution")
    confirmed_facilities = assumptions_map.get("existing_available_facilities")

    # Tracking known and unknown components - never coerce unknown to 0.0
    known_confirmed_amounts: Dict[str, float] = {}
    unknown_components: List[str] = []

    if cash_on_hand is not None:
        known_confirmed_amounts["cash_on_hand"] = cash_on_hand
    else:
        unknown_components.append("cash_on_hand")

    if owner_equity is not None:
        known_confirmed_amounts["owner_equity"] = owner_equity
    else:
        unknown_components.append("owner_equity")

    if confirmed_facilities is not None:
        known_confirmed_amounts["confirmed_facilities"] = confirmed_facilities
    else:
        unknown_components.append("confirmed_facilities")

    if growth_investment is None:
        unknown_components.append("growth_investment")

    known_total = round(sum(known_confirmed_amounts.values()), 2)

    # Funding gap calculation - strictly requires ALL components to be known
    if unknown_components:
        funding_gap = None
        if "cash_on_hand" in unknown_components:
            funding_gap_status = "NOT_AVAILABLE"
        else:
            funding_gap_status = "NEEDS_INFORMATION"
    else:
        funding_gap = max(0.0, round(growth_investment - known_total, 2))
        funding_gap_status = "CALCULATED"

    # Wave 2 funding programs lookup using real deterministic evaluator
    db = Session.object_session(study) if study else None
    matched_programs = []
    matches_count = 0
    if db and study:
        project = getattr(study, "project", None)
        eval_res = evaluate_study_funding_matches(
            db,
            study=study,
            project=project,
            owner_contribution=owner_equity,
            existing_facilities=confirmed_facilities,
            capex_assumption=growth_investment,
        )
        for m in eval_res.get("matches", []):
            st = m.get("overall_match_status", "NOT_EVALUATED")
            matched_programs.append({
                "program_id": m.get("program_id"),
                "program_name_ar": m.get("program_name_ar"),
                "sponsor_name_ar": m.get("provider_ar") or m.get("sponsor_name_ar") or "جهة تمويل معتمدة",
                "funding_type": m.get("funding_type") or m.get("program_type") or "تمويل تنموي",
                "fit_status": st,
                "overall_match_status": st,
                "status_reason_ar": m.get("status_reason_ar"),
            })
        matches_count = eval_res.get("matches_count", 0)

    confirmed_funding_status = "CONFIRMED" if (owner_equity is not None or confirmed_facilities is not None) else "UNKNOWN"

    return {
        "context_type": "WAVE_2_INTEGRATION",
        "disclaimer_ar": "التمويل المحتمل ليس سيولة نقدية متاحة ولا يغني عن تحقيق مدرج سيولة تشغيلي آمن.",
        "summary_ar": f"تم الربط مع منظومة التمويل في Wave 2؛ تم رصد {matches_count} برنامج تمويلي مطابق.",
        "wave2_matched_programs_count": matches_count,
        "wave2_matched_programs": matched_programs,
        "study_id": study.id if study else None,
        "known_confirmed_amounts": known_confirmed_amounts,
        "unknown_components": unknown_components,
        "known_total": known_total,
        "funding_gap_status": funding_gap_status,
        "feasibility_reference": {
            "funding_needed": study.project.investment if (study and getattr(study, "project", None)) else (study.payload.get("investment") if study and getattr(study, "payload", None) else None),
            "capital_structure": None,
            "recommended_structure": None,
        },
        "current_available_cash": {
            "amount": cash_on_hand,
            "status": "RECORDED_ACTUAL" if cash_on_hand is not None else "UNKNOWN",
            "source": f"الدورة الفعلية {latest_p.period_label}" if latest_p else "غير متوفر",
            "label_ar": "السيولة النقدية المتاحة فعلياً",
        },
        "growth_investment_need": {
            "amount": growth_investment,
            "status": "USER_ASSUMPTION" if growth_investment is not None else "UNKNOWN",
            "source": f"سيناريو التوسع: {scenario.title}" if scenario else "لم يتم اختيار سيناريو",
            "label_ar": "الاحتياج الاستثماري المقترح للتوسع",
        },
        "confirmed_funding": {
            "owner_equity": owner_equity,
            "confirmed_credit_facilities": confirmed_facilities,
            "total_confirmed": round((owner_equity or 0.0) + (confirmed_facilities or 0.0), 2) if (owner_equity is not None or confirmed_facilities is not None) else None,
            "status": confirmed_funding_status,
            "label_ar": "التمويل المؤكد المتاح",
        },
        "potential_funding_capacity": {
            "status": "POTENTIAL_NOT_CASH",
            "note_ar": "الطاقة التمويلية المحتملة لا تعني موافقة ائتمانية ولا تُعد نقدية متاحة.",
            "programs_link": f"/studies/{study.id}/funding-matches" if study else "#",
            "readiness_link": f"/studies/{study.id}/funding-readiness" if study else "#",
        },
        "funding_gap": {
            "gap_amount": funding_gap,
            "status": funding_gap_status,
            "funding_gap_status": funding_gap_status,
            "known_confirmed_amounts": known_confirmed_amounts,
            "unknown_components": unknown_components,
            "known_total": known_total,
            "label_ar": "الفجوة التمويلية للتوسع",
            "rule_explanation_ar": "الفجوة التمويلية = استثمار التوسع المطلوب - (النقدية المتاحة + التمويل المؤكد).",
        },
        "calculation_version": CALCULATION_VERSION,
    }


# ==============================================================================
# 7. DETERMINISTIC WHAT-IF ENGINE
# ==============================================================================

def execute_what_if_scenario(
    growth_ws: models.GrowthWorkspace,
    user: Optional[models.User] = None,
    scenario_id: Optional[int] = None,
    model_type: str = "CUSTOM",
    title: Optional[str] = None,
    scenario_name: Optional[str] = None,
    scenario_type: Optional[str] = None,
    target_horizon_months: int = 12,
    capex_required: Optional[float] = None,
    additional_monthly_opex: Optional[float] = None,
    expected_monthly_revenue_uplift: Optional[float] = None,
    target_capacity_increase_pct: Optional[float] = None,
    user_assumptions: Optional[Dict[str, Any]] = None,
    revenue_change_pct: Optional[float] = None,
    opex_change_pct: Optional[float] = None,
    new_headcount_cost: Optional[float] = None,
    new_marketing_spend: Optional[float] = None,
    new_branch_capex: Optional[float] = None,
    volume_change_pct: Optional[float] = None,
    **kwargs,
) -> models.GrowthWhatIfModel:
    """Executes deterministic What-If analysis strictly separating ACTUAL, BASELINE,
    USER_ASSUMPTION, and PLATFORM_DERIVED outputs.
    
    Output strictly labeled:
    - ACTUAL: historical actual values
    - BASELINE: approved study projections
    - USER_ASSUMPTION: explicit user overrides (omitted assumptions are NEVER tagged USER_ASSUMPTION)
    - PLATFORM_DERIVED: purely calculated projections
    If neither ACTUAL nor approved BASELINE exists:
    base revenue = None, base opex = None, status = NEEDS_INFORMATION, simulated values = None.
    Never invent synthetic fallbacks (100000/60000).
    Scenario result != forecast guarantee.
    """
    db = Session.object_session(growth_ws)
    launch_ws = db.query(models.LaunchWorkspace).filter_by(study_id=growth_ws.study_id).first()

    effective_title = title or scenario_name or "محاكاة سيناريو توسع"
    effective_model_type = scenario_type or model_type or "CUSTOM"
    effective_capex = capex_required if capex_required is not None else new_branch_capex

    # 1. Historical Actual Baseline
    latest_p = sorted(launch_ws.actual_periods, key=lambda x: x.period_order)[-1] if (launch_ws and launch_ws.actual_periods) else None
    act_rev = latest_p.actual_revenue if latest_p else None
    act_opex = latest_p.total_actual_opex if latest_p else None
    act_cash = latest_p.closing_cash_balance if latest_p else None

    # 2. Approved Baseline Projection (from study / snapshot)
    snapshot = launch_ws.baseline_snapshots[0] if (launch_ws and launch_ws.baseline_snapshots) else None
    proj_rev = None
    proj_opex = None
    if snapshot and snapshot.monthly_projections:
        p0 = snapshot.monthly_projections[0]
        proj_rev = p0.get("projected_revenue")
        proj_opex = p0.get("projected_opex")

    # Strictly no synthetic defaults (never invent 100000.0 or 60000.0)
    base_rev = act_rev if act_rev is not None else proj_rev
    base_opex = act_opex if act_opex is not None else proj_opex

    # 3. User Assumptions Assembly - ONLY explicitly supplied non-None values
    final_user_assumptions = {}
    if user_assumptions:
        for k, v in user_assumptions.items():
            if v is not None:
                final_user_assumptions[k] = v

    explicit_args = {
        "capex_required": effective_capex,
        "additional_monthly_opex": additional_monthly_opex,
        "expected_monthly_revenue_uplift": expected_monthly_revenue_uplift,
        "target_capacity_increase_pct": target_capacity_increase_pct,
        "revenue_change_pct": revenue_change_pct,
        "opex_change_pct": opex_change_pct,
        "new_headcount_cost": new_headcount_cost,
        "new_marketing_spend": new_marketing_spend,
        "new_branch_capex": new_branch_capex,
        "volume_change_pct": volume_change_pct,
    }
    for k, v in explicit_args.items():
        if v is not None and k not in final_user_assumptions:
            final_user_assumptions[k] = v

    # 4. Platform Derived Projections (Deterministic)
    if base_rev is None or base_opex is None:
        derived_outputs = {
            "status": "NEEDS_INFORMATION",
            "simulated_monthly_revenue": None,
            "simulated_monthly_opex": None,
            "simulated_net_monthly": None,
            "initial_cash_after_capex": None,
            "estimated_cash_payback_months": None,
            "estimated_net_runway_impact_months": None,
            "minimum_cash_required": effective_capex,
            "monthly_forward_projections": [],
            "reason_ar": "لا توجد بيانات فعلية سابقة ولا خط أساس معتمد لاحتساب سيناريو ماذا-لو. الحالة: يلزم استكمال البيانات (NEEDS_INFORMATION).",
            "disclaimer_ar": "نتائج السيناريو هي مخرجات مشتقة من افتراضات المستخدم ولا تشكل ضماناً مالياً مستقبلياً.",
            "calculation_version": CALCULATION_VERSION,
        }
    else:
        rev_pct = final_user_assumptions.get("revenue_change_pct") or 0.0
        vol_pct = final_user_assumptions.get("volume_change_pct") or 0.0
        opex_pct = final_user_assumptions.get("opex_change_pct") or 0.0
        effective_rev_pct = rev_pct + vol_pct
        uplift_rev = final_user_assumptions.get("expected_monthly_revenue_uplift") or 0.0
        uplift_opex = (
            (final_user_assumptions.get("additional_monthly_opex") or 0.0)
            + (final_user_assumptions.get("new_headcount_cost") or 0.0)
            + (final_user_assumptions.get("new_marketing_spend") or 0.0)
        )

        simulated_monthly_revenue = round((base_rev * (1.0 + (effective_rev_pct / 100.0))) + uplift_rev, 2)
        simulated_monthly_opex = round((base_opex * (1.0 + (opex_pct / 100.0))) + uplift_opex, 2)
        simulated_net_monthly = round(simulated_monthly_revenue - simulated_monthly_opex, 2)

        simulated_cash = act_cash if act_cash is not None else None
        initial_cash_after_capex = None
        if simulated_cash is not None and effective_capex is not None:
            initial_cash_after_capex = round(simulated_cash - effective_capex, 2)

        # Calculate Payback Months & Runway Impact
        net_monthly_gain = (simulated_net_monthly - (base_rev - base_opex))
        payback_months = None
        if effective_capex and effective_capex > 0:
            gain_for_payback = net_monthly_gain if net_monthly_gain > 0 else simulated_net_monthly
            if gain_for_payback > 0:
                payback_months = int(round(effective_capex / gain_for_payback))

        # Calculate forward trajectory
        horizon = min(60, max(1, target_horizon_months))
        forward_projections = []
        curr_cash = initial_cash_after_capex if initial_cash_after_capex is not None else simulated_cash

        for m in range(1, horizon + 1):
            m_rev = simulated_monthly_revenue
            m_opex = simulated_monthly_opex
            m_net = round(m_rev - m_opex, 2)
            if curr_cash is not None:
                curr_cash = round(curr_cash + m_net, 2)

            forward_projections.append({
                "month": m,
                "period_label": f"Sim+M{m:02d}",
                "projected_revenue": m_rev,
                "projected_opex": m_opex,
                "projected_net_cashflow": m_net,
                "projected_cash_balance": curr_cash,
            })

        derived_outputs = {
            "status": "CALCULATED",
            "simulated_monthly_revenue": simulated_monthly_revenue,
            "simulated_monthly_opex": simulated_monthly_opex,
            "simulated_net_monthly": simulated_net_monthly,
            "initial_cash_after_capex": initial_cash_after_capex,
            "estimated_cash_payback_months": payback_months,
            "estimated_net_runway_impact_months": round(payback_months - 12, 1) if payback_months else None,
            "minimum_cash_required": effective_capex or 0.0,
            "monthly_forward_projections": forward_projections,
            "disclaimer_ar": "نتائج السيناريو هي مخرجات مشتقة من افتراضات المستخدم ولا تشكل ضماناً مالياً مستقبلياً.",
            "calculation_version": CALCULATION_VERSION,
        }

    model = models.GrowthWhatIfModel(
        workspace_id=growth_ws.id,
        scenario_id=scenario_id,
        model_type=effective_model_type,
        title=effective_title,
        user_assumptions=final_user_assumptions,
        baseline_inputs={
            "base_revenue": base_rev,
            "base_opex": base_opex,
            "is_from_actuals": act_rev is not None,
        },
        actual_inputs={
            "actual_revenue": act_rev,
            "actual_opex": act_opex,
            "closing_cash_balance": act_cash,
            "period_label": latest_p.period_label if latest_p else None,
        },
        derived_outputs=derived_outputs,
        created_by=user.id if user else growth_ws.user_id,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


# ==============================================================================
# 8. MONTHLY BUSINESS REVIEW SNAPSHOTS
# ==============================================================================

def create_monthly_business_review(
    growth_ws: models.GrowthWorkspace,
    user: models.User,
    review_period: str,
    review_notes: Optional[str] = None,
) -> models.GrowthMonthlyReview:
    """Freezes an immutable Monthly Business Review snapshot.
    
    Rules:
    - Historical reviews are immutable.
    - New review creates a new incremental version, not rewriting past history.
    """
    db = Session.object_session(growth_ws)
    launch_ws = db.query(models.LaunchWorkspace).filter_by(study_id=growth_ws.study_id).first()

    health_eval = evaluate_business_health(launch_ws)
    trends_eval = evaluate_all_trends(launch_ws.actual_periods if launch_ws else [])
    unit_eval = calculate_unit_economics(launch_ws.actual_periods[-1] if (launch_ws and launch_ws.actual_periods) else None)
    risks_eval = detect_growth_risks(launch_ws)
    variances_eval = evaluate_workspace_variances(launch_ws) if launch_ws else {}

    # Version sequence
    latest_review = (
        db.query(models.GrowthMonthlyReview)
        .filter_by(workspace_id=growth_ws.id)
        .order_by(models.GrowthMonthlyReview.version_number.desc())
        .first()
    )
    new_version = (latest_review.version_number + 1) if latest_review else 1

    review = models.GrowthMonthlyReview(
        workspace_id=growth_ws.id,
        review_period=review_period,
        version_number=new_version,
        actual_periods_covered=[p.period_label for p in (launch_ws.actual_periods if launch_ws else [])],
        health_state=health_eval["overall_state"],
        health_snapshot=health_eval,
        trend_summary=trends_eval,
        unit_economics_snapshot=unit_eval,
        risks_snapshot=risks_eval,
        variances_snapshot=variances_eval,
        cash_runway_snapshot={
            "closing_cash": launch_ws.actual_periods[-1].closing_cash_balance if (launch_ws and launch_ws.actual_periods) else None,
            "period": launch_ws.actual_periods[-1].period_label if (launch_ws and launch_ws.actual_periods) else None,
        },
        open_actions=[
            {"id": a.id, "title": a.title, "status": a.status, "category": a.category}
            for a in growth_ws.actions if a.status != "COMPLETED"
        ],
        scenarios_evaluated=[
            {"id": s.id, "title": s.title, "type": s.scenario_type, "status": s.status}
            for s in growth_ws.scenarios
        ],
        missing_information=unit_eval.get("missing_inputs", []) + (health_eval.get("missing_inputs", [])),
        review_notes=review_notes,
        created_by=user.id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


# ==============================================================================
# 9. GROWTH STRATEGIC DECISION ENGINE & PIVOT INTEGRATION
# ==============================================================================

def record_growth_decision(
    growth_ws: models.GrowthWorkspace,
    user: models.User,
    decision: str,
    decision_reason: str,
    user_assumptions: Optional[Dict[str, Any]] = None,
    conditions: Optional[List[str]] = None,
    re_evaluation_date: Optional[str] = None,
    growth_scenario_id: Optional[int] = None,
) -> models.GrowthDecision:
    """Records an immutable strategic business decision explicitly confirmed by the user.
    
    Supported Decisions: SCALE, FIX, PIVOT, HOLD, STOP, NEEDS_INFORMATION.
    
    Semantics:
    - SCALE: Must not result merely from revenue growth; checks cash, capacity, and operational stability.
      Requires explicit same-workspace growth_scenario_id, known capex/investment requirement > 0,
      readiness state != NEEDS_INFORMATION and != NOT_READY, and funding context not treating unknown as cash.
    - FIX: Generates remediation action plan.
    - PIVOT: Links to a NEW Wave 4 validation cycle workspace without overwriting old ones.
    - HOLD: Requires reason and re-evaluation condition/date.
    - STOP: Preserves complete business history.
    - NEEDS_INFORMATION: Raised when evidence is insufficient.
    """
    if decision not in VALID_GROWTH_DECISIONS:
        raise ValueError(f"Invalid decision '{decision}'. Allowed: {sorted(list(VALID_GROWTH_DECISIONS))}")

    db = Session.object_session(growth_ws)
    launch_ws = db.query(models.LaunchWorkspace).filter_by(study_id=growth_ws.study_id).first()

    scenario = None
    if growth_scenario_id:
        scenario = db.query(models.GrowthScenario).filter_by(id=growth_scenario_id).first()

    # Pre-decision sanity checks
    readiness = evaluate_expansion_readiness(growth_ws, launch_ws, scenario=scenario)
    risks = detect_growth_risks(launch_ws)

    supporting_facts = []
    contradicting_facts = []
    unknowns = []

    # Fact categorization
    for p in readiness["prerequisites"]:
        if p["status"] == PREREQ_PASS:
            supporting_facts.append(f"{p['name_ar']}: {p['reason_ar']}")
        elif p["status"] == PREREQ_FAIL:
            contradicting_facts.append(f"{p['name_ar']}: {p['reason_ar']}")
        elif p["status"] == PREREQ_UNKNOWN:
            unknowns.append(f"{p['name_ar']}: {p['reason_ar']}")

    # SCALE Guardrail: cannot scale into the dark
    if decision == DECISION_SCALE:
        if not growth_scenario_id:
            raise ValueError("يتطلب اعتماد قرار التوسع (SCALE) تحديد سيناريو نمو معتمد (growth_scenario_id).")

        if not scenario or scenario.workspace_id != growth_ws.id:
            raise ValueError("سيناريو النمو المحدد غير موجود أو لا ينتمي إلى نفس مساحة عمل النمو الحالية.")

        scenario_investment = scenario.investment_required
        if scenario_investment is None or scenario_investment <= 0:
            raise ValueError("يتطلب قرار التوسع (SCALE) تحديد قيمة متطلبات الاستثمار أو النفقات الرأسمالية (capex / investment required) بشكل صريح وأكبر من صفر.")

        if readiness["readiness_state"] == READINESS_NEEDS_INFO:
            raise ValueError("لا يمكن اعتماد قرار التوسع (SCALE) في ظل وجود متطلبات جوهرية مجهولة (NEEDS_INFORMATION). يرجى استكمال بيانات الأداء أولاً.")
        if readiness["readiness_state"] == READINESS_NOT_READY:
            raise ValueError(f"لا يمكن اعتماد قرار التوسع (SCALE) لوجود معطلات صريحة أو عجز في مدرج السيولة: {readiness['summary_ar']}")

        funding_ctx = get_growth_funding_context(growth_ws, launch_ws, scenario)
        if funding_ctx.get("funding_gap_status") in ("NOT_AVAILABLE", "NEEDS_INFORMATION"):
            raise ValueError("لا يمكن اعتماد قرار التوسع (SCALE) في ظل عدم اكتمال بيانات السيولة أو التمويل المؤكد (حالة الفجوة التمويلية غير معلومة).")
        if funding_ctx.get("current_available_cash", {}).get("status") == "UNKNOWN":
            raise ValueError("لا يمكن اعتماد قرار التوسع (SCALE) دون توفر رصيد نقدية فعلي مسجل.")

    # Version sequence
    latest_dec = (
        db.query(models.GrowthDecision)
        .filter_by(workspace_id=growth_ws.id)
        .order_by(models.GrowthDecision.decision_version.desc())
        .first()
    )
    new_version = (latest_dec.decision_version + 1) if latest_dec else 1

    # PIVOT Integration: Link / Create new Wave 4 validation cycle workspace without overwriting old
    pivot_val_ws_id = None
    if decision == DECISION_PIVOT:
        val_workspaces = db.query(models.ValidationWorkspace).filter_by(study_id=growth_ws.study_id).all()
        new_val_ws = models.ValidationWorkspace(
            project_id=growth_ws.project_id,
            study_id=growth_ws.study_id,
            user_id=user.id,
            status="NEEDS_EVIDENCE",
        )
        db.add(new_val_ws)
        db.flush()

        pivot_hypo = models.ValidationHypothesis(
            workspace_id=new_val_ws.id,
            hypothesis_type="BUSINESS_MODEL",
            statement=f"فرضية تعديل المسار (PIVOT v{len(val_workspaces) + 1}): {decision_reason}",
            importance="CRITICAL",
            status="NOT_TESTED",
            rationale="دورة تحقق ميداني جديدة مبنية على قرار تعديل المسار التشغيلي للمنشأة.",
            created_by=user.id,
        )
        db.add(pivot_hypo)
        db.flush()
        pivot_val_ws_id = new_val_ws.id

    rec_actions = []
    if decision == DECISION_FIX:
        rec_actions = [
            "مراجعة وتخفيض بنود المصروفات التشغيلية المرتفعة",
            "إعادة التفاوض على شروط التوريد والإيجار",
            "معالجة المعالم والمهام المعطلة في خطة الإطلاق",
        ]
    elif decision == DECISION_SCALE:
        rec_actions = [
            "تأمين خط التمويل المناسب لفجوة التوسع",
            "توظيف وتدريب الكفاءات الإضافية للفرع أو الخدمة الجديدة",
            "بدء الإجراءات النظامية والترخيص للتوسع",
        ]
    elif decision == DECISION_PIVOT:
        rec_actions = [
            "تحديد شريحة العملاء المستهدفة في النموذج المعدل",
            "إجراء 10 مقابلات عملاء لاختبار القيمة المضافة الجديدة",
            "تحديث دراسة الجدوى التشغيلية",
        ]

    growth_decision = models.GrowthDecision(
        workspace_id=growth_ws.id,
        decision=decision,
        decision_version=new_version,
        decision_reason=decision_reason,
        growth_scenario_id=growth_scenario_id,
        supporting_facts=supporting_facts,
        contradicting_facts=contradicting_facts,
        unknowns=unknowns,
        user_assumptions=user_assumptions or {},
        risks=[r["risk_title_ar"] for r in risks if r["level"] in (RISK_HIGH, RISK_WATCH)],
        conditions=conditions or [],
        recommended_next_actions=rec_actions,
        pivot_validation_workspace_id=pivot_val_ws_id,
        re_evaluation_date=re_evaluation_date,
        decided_at=datetime.now(timezone.utc),
        decided_by=user.id,
    )
    db.add(growth_decision)
    db.flush()

    # Auto-generate GrowthActions for FIX or SCALE decisions
    if decision == DECISION_FIX:
        for act_title in rec_actions:
            db.add(models.GrowthAction(
                workspace_id=growth_ws.id,
                decision_id=growth_decision.id,
                title=act_title,
                action_type="REMEDIATION",
                category="OPERATIONS",
                status="PENDING",
            ))

    # Update workspace status
    if decision == DECISION_STOP:
        growth_ws.status = "STOPPED"
    elif decision == DECISION_PIVOT:
        growth_ws.status = "PIVOTED"
    elif decision == DECISION_HOLD:
        growth_ws.status = "PAUSED"
    else:
        growth_ws.status = "ACTIVE"

    db.commit()
    db.refresh(growth_decision)
    return growth_decision

