"""Financial trust helpers: input sanity warnings and user-facing IRR messaging.

Does not change frozen engines (Archetype / Knowledge / Discovery / Risk / Decision).
Only hardens Financial Engine outputs for trust and auditability.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional


IRR_UNAVAILABLE_EN = (
    "IRR cannot be calculated for these cash flows."
)
IRR_UNAVAILABLE_AR = (
    "لا يمكن حساب معدل العائد الداخلي لهذه التدفقات النقدية."
)
IRR_REASON_EN = (
    "No valid internal rate of return was found in range — often because cash flows "
    "do not change sign, or the profile is too extreme for a stable IRR."
)
IRR_REASON_AR = (
    "لم يتم العثور على معدل عائد داخلي صالح ضمن النطاق — غالباً لأن التدفقات النقدية "
    "لا تغيّر الإشارة، أو لأن الملف متطرف جداً لاستقرار الحساب."
)
IRR_MISSING_CONDITION_EN = (
    "Requires an initial outflow followed by net inflows (a sign change) within the projection window."
)
IRR_MISSING_CONDITION_AR = (
    "يتطلب تدفقاً أولياً سالباً يتبعه صافي تدفقات موجبة (تغير إشارة) ضمن نافذة الإسقاط."
)


def irr_user_message(irr: Optional[float], *, language: str = "en") -> str:
    """Never surface raw null IRR to users."""
    if irr is None:
        return IRR_UNAVAILABLE_AR if language == "ar" else IRR_UNAVAILABLE_EN
    # irr is stored as a decimal rate (0.25 = 25%).
    pct = float(irr) * 100.0
    return f"{pct:.1f}%"


def irr_metric_state(irr: Optional[float], *, language: str = "en") -> dict[str, Any]:
    """Structured IRR display for UI — never includes the literal 'null'."""
    ar = language == "ar"
    if irr is None:
        return {
            "label": "معدل العائد الداخلي" if ar else "IRR",
            "available": False,
            "display": IRR_UNAVAILABLE_AR if ar else IRR_UNAVAILABLE_EN,
            "reason": IRR_REASON_AR if ar else IRR_REASON_EN,
            "missing_condition": IRR_MISSING_CONDITION_AR if ar else IRR_MISSING_CONDITION_EN,
        }
    return {
        "label": "معدل العائد الداخلي" if ar else "IRR",
        "available": True,
        "display": irr_user_message(irr, language=language),
        "reason": None,
        "missing_condition": None,
    }


PAYBACK_UNAVAILABLE_EN = (
    "Payback period cannot be calculated for these cash flows."
)
PAYBACK_UNAVAILABLE_AR = (
    "لا يمكن حساب فترة الاسترداد لهذه التدفقات النقدية."
)
PAYBACK_REASON_EN = (
    "Cumulative cash flow never recovers the initial investment inside the projection window."
)
PAYBACK_REASON_AR = (
    "التدفق النقدي التراكمي لا يسترد الاستثمار الأولي داخل نافذة الإسقاط."
)
PAYBACK_MISSING_CONDITION_EN = (
    "Requires cumulative net cash flows to turn non-negative within the modeled years."
)
PAYBACK_MISSING_CONDITION_AR = (
    "يتطلب أن يصبح صافي التدفق التراكمي غير سالب خلال السنوات المُنمذَجة."
)


def payback_user_message(payback_months: Optional[float], *, language: str = "en") -> str:
    """Never surface raw null payback to users."""
    if payback_months is None:
        return PAYBACK_UNAVAILABLE_AR if language == "ar" else PAYBACK_UNAVAILABLE_EN
    months = float(payback_months)
    if language == "ar":
        return f"{months:.1f} شهراً"
    return f"{months:.1f} months"


def payback_metric_state(
    payback_months: Optional[float], *, language: str = "en"
) -> dict[str, Any]:
    """Structured Payback display for UI — never includes the literal 'null'."""
    ar = language == "ar"
    if payback_months is None:
        return {
            "label": "فترة الاسترداد" if ar else "Payback Period",
            "available": False,
            "display": PAYBACK_UNAVAILABLE_AR if ar else PAYBACK_UNAVAILABLE_EN,
            "reason": PAYBACK_REASON_AR if ar else PAYBACK_REASON_EN,
            "missing_condition": PAYBACK_MISSING_CONDITION_AR if ar else PAYBACK_MISSING_CONDITION_EN,
        }
    return {
        "label": "فترة الاسترداد" if ar else "Payback Period",
        "available": True,
        "display": payback_user_message(payback_months, language=language),
        "reason": None,
        "missing_condition": None,
    }


def attach_financial_display_fields(payload: dict[str, Any], *, language: str = "en") -> dict[str, Any]:
    """Ensure user-facing display fields exist; keep raw numeric keys for evidence/logs only."""
    out = dict(payload or {})
    irr = out.get("irr")
    payback = out.get("payback_months")
    if payback is None and out.get("payback_years") is not None:
        try:
            payback = float(out["payback_years"]) * 12.0
        except (TypeError, ValueError):
            payback = None

    irr_state = irr_metric_state(irr if isinstance(irr, (int, float)) or irr is None else None, language=language)
    # If irr is a non-numeric string already, treat as unavailable
    if irr is not None and not isinstance(irr, (int, float)):
        irr_state = irr_metric_state(None, language=language)

    payback_state = payback_metric_state(
        payback if isinstance(payback, (int, float)) or payback is None else None,
        language=language,
    )

    out["irr_display"] = irr_state["display"]
    out["irr_available"] = bool(irr_state["available"])
    out["irr_state"] = irr_state
    out["payback_display"] = payback_state["display"]
    out["payback_available"] = bool(payback_state["available"])
    out["payback_state"] = payback_state
    return out


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_financial_inputs(
    *,
    archetype: str | None,
    capex: float,
    annual_revenues: Iterable[float],
    annual_costs: Iterable[float],
    assumptions: dict[str, float] | None = None,
    language: str = "en",
) -> list[str]:
    """Soft validation — never blocks. Returns human-readable warnings."""
    warnings: list[str] = []
    assumptions = assumptions or {}
    arch = (archetype or "").lower().strip()
    revenues = [float(x) for x in annual_revenues]
    costs = [float(x) for x in annual_costs]
    y1_rev = revenues[0] if revenues else 0.0
    y1_cost = costs[0] if costs else 0.0

    if capex <= 0 and y1_rev > 0:
        warnings.append(
            "Initial investment (CAPEX) is zero while revenue is positive — NPV/IRR may be misleading."
            if language != "ar"
            else "الاستثمار الأولي صفر مع وجود إيرادات — قد تكون NPV/IRR مضللة."
        )

    if y1_rev > 0 and y1_cost <= 0:
        warnings.append(
            "Year-1 operating costs are zero while revenue is positive — costs may be missing."
            if language != "ar"
            else "تكاليف التشغيل لسنة 1 صفر مع وجود إيراد — قد تكون التكاليف ناقصة."
        )

    if arch in {"data_center", "datacenter", "colocation"}:
        mw = _as_float(assumptions.get("mw_capacity")) or _as_float(assumptions.get("mw"))
        if mw and mw > 0 and capex > 0:
            per_mw = capex / mw
            # Saudi hyperscale / colo ballpark: ~SAR 8M–20M per IT MW all-in.
            low, high = 8_000_000.0, 20_000_000.0
            if per_mw < low:
                expected_low = int(mw * low)
                expected_high = int(mw * high)
                warnings.append(
                    f"CAPEX looks unusually low for a {mw:g} MW data center "
                    f"(~SAR {per_mw:,.0f}/MW). Expected range about "
                    f"SAR {expected_low:,.0f}–{expected_high:,.0f}."
                    if language != "ar"
                    else f"النفقات الرأسمالية منخفضة بشكل غير معتاد لمركز بيانات بسعة {mw:g} ميجاواط "
                    f"(حوالي {per_mw:,.0f} ر.س/ميجاواط). النطاق المتوقع تقريباً "
                    f"{expected_low:,.0f}–{expected_high:,.0f} ر.س."
                )
            elif per_mw > high * 1.5:
                warnings.append(
                    f"CAPEX looks unusually high for a {mw:g} MW data center (~SAR {per_mw:,.0f}/MW)."
                    if language != "ar"
                    else f"النفقات الرأسمالية مرتفعة بشكل غير معتاد لمركز بيانات بسعة {mw:g} ميجاواط."
                )

    if arch in {"real_estate", "residential", "property"}:
        units = _as_float(assumptions.get("units")) or _as_float(assumptions.get("unit_count"))
        if units and units >= 50 and 0 < capex < units * 200_000:
            warnings.append(
                f"CAPEX looks low for {int(units)} residential units "
                f"(~SAR {capex / units:,.0f}/unit)."
                if language != "ar"
                else f"النفقات الرأسمالية منخفضة لـ {int(units)} وحدة سكنية."
            )

    if arch in {"services", "professional_services", "cybersecurity", "mssp"}:
        headcount = _as_float(assumptions.get("consultants_headcount")) or _as_float(
            assumptions.get("headcount")
        )
        if headcount and headcount > 0 and 0 < capex < headcount * 5_000:
            warnings.append(
                "Initial investment looks very low relative to services headcount."
                if language != "ar"
                else "الاستثمار الأولي منخفض جداً مقارنة بعدد فريق الخدمات."
            )

    if arch in {"saas", "saas_digital", "software"}:
        if y1_rev > 0 and capex > y1_rev * 20:
            warnings.append(
                "CAPEX is very large relative to year-1 SaaS revenue — check units (SAR vs thousands)."
                if language != "ar"
                else "النفقات الرأسمالية كبيرة جداً مقارنة بإيراد SaaS لسنة 1 — تحقق من الوحدات."
            )

    return warnings


def services_capacity_revenue(
    *,
    billing_rate: float | None,
    utilization_rate: float | None,
    headcount: float | None,
    active_contracts: float | None = None,
    billable_hours_month: float | None = None,
    billable_period: float | None = None,
    mrc: float | None = None,
) -> tuple[float | None, list[str]]:
    """Revenue for professional services.

    Preferred:
      billing_rate × utilization × resources × billable_period
    where billable_period is annual billable hours when provided, otherwise
    hours/month × 12 (default 160 × 12).

    Fallback: MRC × 12
    Returns (annual_year1_revenue, notes).
    """
    notes: list[str] = []
    hours = billable_hours_month if billable_hours_month and billable_hours_month > 0 else 160.0
    # billable_period: prefer explicit annual hours; values ≤ 24 treated as months.
    if billable_period is not None and billable_period > 0:
        if billable_period <= 24:
            period = float(hours) * float(billable_period)
            notes.append("services_billable_period_interpreted_as_months")
        else:
            period = float(billable_period)
            notes.append("services_billable_period_annual_hours")
    else:
        period = float(hours) * 12.0
        notes.append("services_billable_period_defaulted_hours_x_12")

    util = utilization_rate
    if util is not None and util > 1:
        util = util / 100.0

    resources = headcount if headcount and headcount > 0 else None
    if resources is None and active_contracts and active_contracts > 0 and billing_rate:
        # Contract-based capacity proxy when headcount missing.
        resources = active_contracts
        notes.append("services_revenue_used_active_contracts_as_resource_proxy")

    tm_annual = None
    if billing_rate and util is not None and resources:
        tm_annual = float(billing_rate) * float(util) * float(resources) * float(period)
        notes.append("services_revenue_from_billing_rate_x_utilization_x_resources")

    mrc_annual = float(mrc) * 12.0 if mrc is not None and mrc > 0 else None
    if tm_annual is not None and mrc_annual is not None:
        # Retainers + billable capacity: take the larger coherent signal, note divergence.
        chosen = max(tm_annual, mrc_annual)
        if abs(tm_annual - mrc_annual) / max(tm_annual, mrc_annual) > 0.35:
            notes.append("services_mrc_and_capacity_revenue_diverged_using_max")
        return chosen, notes
    if tm_annual is not None:
        return tm_annual, notes
    if mrc_annual is not None:
        notes.append("services_revenue_from_mrc_only")
        return mrc_annual, notes
    return None, notes
