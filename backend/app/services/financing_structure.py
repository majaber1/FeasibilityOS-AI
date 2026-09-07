"""
Financing Structure Service (Phase 20: Wave 2 — Funding Intelligence Capstone).

Deterministic synthesis of capital structure (Sources & Uses of Funds) for a
feasibility study, integrating:
- Funding Gap (Capex, Project Investment, Owner Capital, Existing Facilities)
- Borrowing Capacity (Safe Debt Capacity, Primary Constraints)
- Collateral (Market Value, Encumbrance, Net Available Collateral)
- Matched Verified Funding Programs (Phase 18/19 Registry & Matching)

Rules & Safeguards:
- Pure deterministic calculations; no invented interest rates or repayment terms.
- No lender approval guarantee claims.
- Sources & Uses must transparently reconcile against total project cost.
- Produces explicit warnings for funding shortfalls, overleveraging, or low equity.
- Generates actionable, sequential next steps for funding preparation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app import models
from app.services.funding_gap import compute_funding_gap
from app.services.borrowing_capacity import estimate_borrowing_capacity
from app.services.collateral import summarize_collateral
from app.services.funding_matching import evaluate_study_funding_matches

DISCLAIMER_AR = (
    "هيكل التمويل ومصادر واستخدامات الأموال المعروضة هي نموذج استرشادي مبني على القواعد "
    "المعلنة واشتراطات الملاءة المالية، ولا تمثل موافقة تمويلية أو التزاماً بنكياً."
)
DISCLAIMER_EN = (
    "The financing structure and Sources & Uses model is an advisory screening framework "
    "based on published official guidelines and solvency metrics. It does not constitute credit approval or funding commitment."
)

INTERNAL_SCREENING_ASSUMPTION_MIN_EQUITY = 0.20  # Saudi Business internal advisory screening benchmark, not a statutory rule.
# Alias for backwards-compatibility:
RECOMMENDED_MIN_EQUITY_RATIO = INTERNAL_SCREENING_ASSUMPTION_MIN_EQUITY


def compute_financing_structure(
    db: Session,
    *,
    study: models.FeasibilityStudy,
    project: models.Project,
    owner_contribution: Optional[float] = None,
    capex_assumption: Optional[float] = None,
    existing_facilities: Optional[float] = None,
    financial_period_dict: Optional[dict] = None,
    collateral_dicts: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """Computes a deterministic, reconciled Sources & Uses financing structure with hardened business semantics."""

    # 1. Compute Funding Gap & Confirmed Sources
    project_investment = float(project.investment or 0.0) if project else 0.0
    gap_data = compute_funding_gap(
        capex_assumption=capex_assumption,
        project_investment=project_investment,
        owner_contribution=owner_contribution,
        existing_facilities=existing_facilities,
    )

    total_requirement = float(gap_data["total_project_requirement"])
    owner_equity = float(gap_data["owner_available_capital"])
    existing_debt = float(gap_data.get("existing_available_facilities") or gap_data.get("existing_facilities") or 0.0)
    initial_gap = float(gap_data["funding_gap"])

    total_confirmed_sources = owner_equity + existing_debt

    # 2. Financial Profile & Internal Screening Debt Capacity
    safe_debt_capacity = 0.0
    capacity_status = "NO_DATA"
    annual_revenue = None
    if financial_period_dict:
        rev_val = financial_period_dict.get("revenue")
        annual_revenue = float(rev_val) if rev_val is not None else None

        ebitda_val = financial_period_dict.get("ebitda")
        ebitda = float(ebitda_val) if ebitda_val is not None else None

        existing_debt_val = financial_period_dict.get("existing_debt")
        fp_existing_debt = float(existing_debt_val) if existing_debt_val is not None else None

        annual_debt_service_val = financial_period_dict.get("annual_debt_service")
        annual_debt_service = float(annual_debt_service_val) if annual_debt_service_val is not None else None

        # Canonical inputs matching Funding Readiness and Borrowing Capacity services
        resolved_debt = fp_existing_debt if fp_existing_debt is not None else (existing_debt if existing_debt > 0 else None)

        cap_eval = estimate_borrowing_capacity(
            ebitda=ebitda,
            existing_debt=resolved_debt,
            annual_debt_service=annual_debt_service,
        )
        capacity_status = cap_eval.get("status", "INSUFFICIENT_DATA")
        if capacity_status == "CALCULATED":
            safe_debt_capacity = float(cap_eval.get("base_capacity") or 0.0)

    # 3. Collateral Summary
    collateral_list = collateral_dicts or []
    collateral_summary = summarize_collateral(collateral_list)
    available_collateral = float(collateral_summary.get("total_verified_value") or 0.0)

    # 4. Matched Programs Evaluation
    matches_data = evaluate_study_funding_matches(
        db,
        study=study,
        project=project,
        owner_contribution=owner_equity,
        capex_assumption=capex_assumption,
        existing_facilities=existing_debt,
        financial_period_dict=financial_period_dict,
        collateral_dicts=collateral_dicts,
    )

    all_matches = matches_data.get("matches", [])
    matched_programs = [m for m in all_matches if m.get("overall_match_status") == "MATCH"]
    possible_matches = [m for m in all_matches if m.get("overall_match_status") == "POSSIBLE_MATCH"]

    # 5. Program Allocations & Credit Enhancements Strategy
    credit_enhancements = []
    program_allocations = []
    allocated_program_debt = 0.0
    remaining_gap_to_fund = initial_gap

    # Rule 2: DO NOT ALLOCATE DEBT WHEN BORROWING CAPACITY IS UNKNOWN
    # If borrowing capacity cannot be calculated, available safe debt capacity is strictly 0.
    # Never invent monetary debt capacity when capacity is unknown.
    if capacity_status == "CALCULATED":
        available_safe_debt_cap = safe_debt_capacity
    else:
        available_safe_debt_cap = 0.0

    for prog in matched_programs:
        p_type = prog.get("program_type", "").upper()
        p_slug = prog.get("program_slug", "")
        p_provider_ar = prog.get("provider_ar", "")

        # Semantic Rule 2: Guarantee programs are Credit Enhancements, NOT cash debt sources (0 SAR cash)
        is_guarantee = (
            p_type == "GUARANTEE"
            or "كفالة" in p_provider_ar
            or p_slug.startswith("kafalah")
        )

        if is_guarantee:
            guarantee_item = {
                "program_id": prog["program_id"],
                "program_slug": prog["program_slug"],
                "provider": prog["provider"],
                "provider_ar": prog["provider_ar"],
                "program_name_ar": prog["program_name_ar"],
                "program_name_en": prog["program_name_en"],
                "program_type": "GUARANTEE",
                "match_status": "MATCH",
                "cash_contribution": 0.0,
                "role_ar": "تعزيز ائتماني وضمان تمويل للبنوك التجارية (لا يقدم سيولة نقدية مباشرة وإنما يضمن التسهيلات البنكية)",
                "role_en": "Credit enhancement and commercial bank guarantee (0 direct cash contribution)",
                "max_guarantee_amount": prog.get("financing_max"),
                "coverage_ratio": prog.get("rules_breakdown", {}).get("guarantee_rule", {}).get("max_coverage") if isinstance(prog.get("rules_breakdown"), dict) else None,
                "official_source_url": prog.get("official_source_url"),
            }
            credit_enhancements.append(guarantee_item)
            program_allocations.append({
                "program_id": prog["program_id"],
                "program_slug": prog["program_slug"],
                "provider": prog["provider"],
                "provider_ar": prog["provider_ar"],
                "program_name_ar": prog["program_name_ar"],
                "program_name_en": prog["program_name_en"],
                "program_type": "GUARANTEE",
                "match_status": "MATCH",
                "allocated_amount": 0.0,
                "allocation_status": "CREDIT_ENHANCEMENT_ONLY",
                "term_months": prog.get("term_months"),
                "grace_period_months": prog.get("grace_period_months"),
                "official_source_url": prog.get("official_source_url"),
            })
            continue

        raw_max = prog.get("financing_max")
        # Semantic Rule 3: Do NOT invent allocation if financing_max is unknown
        if raw_max is None or float(raw_max) <= 0:
            program_allocations.append({
                "program_id": prog["program_id"],
                "program_slug": prog["program_slug"],
                "provider": prog["provider"],
                "provider_ar": prog["provider_ar"],
                "program_name_ar": prog["program_name_ar"],
                "program_name_en": prog["program_name_en"],
                "program_type": prog["program_type"],
                "match_status": "MATCH",
                "allocated_amount": None,  # Displayed as UNKNOWN, 0 cash added to Sources
                "allocation_status": "UNKNOWN_LIMIT",
                "term_months": prog.get("term_months"),
                "grace_period_months": prog.get("grace_period_months"),
                "official_source_url": prog.get("official_source_url"),
            })
            continue

        # Direct cash debt program (LOAN, WORKING_CAPITAL, CO_FINANCING)
        # When borrowing capacity is unknown/uncalculated, program appears as potential option
        # with allocated_amount = None and allocation_status = CAPACITY_NOT_EVALUATED.
        if capacity_status != "CALCULATED":
            program_allocations.append({
                "program_id": prog["program_id"],
                "program_slug": prog["program_slug"],
                "provider": prog["provider"],
                "provider_ar": prog["provider_ar"],
                "program_name_ar": prog["program_name_ar"],
                "program_name_en": prog["program_name_en"],
                "program_type": prog["program_type"],
                "match_status": "MATCH",
                "allocated_amount": None,
                "allocation_status": "CAPACITY_NOT_EVALUATED",
                "term_months": prog.get("term_months"),
                "grace_period_months": prog.get("grace_period_months"),
                "official_source_url": prog.get("official_source_url"),
            })
            continue

        p_max = float(raw_max)
        # Constrain screening debt by remaining gap and safe borrowing capacity
        remaining_capacity = max(0.0, available_safe_debt_cap - allocated_program_debt)
        allocation = min(remaining_gap_to_fund, p_max, remaining_capacity)

        allocated_amount_val = round(allocation, 2)
        if allocated_amount_val > 0:
            allocated_program_debt += allocated_amount_val
            remaining_gap_to_fund -= allocated_amount_val
            program_allocations.append({
                "program_id": prog["program_id"],
                "program_slug": prog["program_slug"],
                "provider": prog["provider"],
                "provider_ar": prog["provider_ar"],
                "program_name_ar": prog["program_name_ar"],
                "program_name_en": prog["program_name_en"],
                "program_type": prog["program_type"],
                "match_status": "MATCH",
                "allocated_amount": allocated_amount_val,
                "allocation_status": "POTENTIAL_SOURCE",
                "term_months": prog.get("term_months"),
                "grace_period_months": prog.get("grace_period_months"),
                "official_source_url": prog.get("official_source_url"),
            })
        else:
            program_allocations.append({
                "program_id": prog["program_id"],
                "program_slug": prog["program_slug"],
                "provider": prog["provider"],
                "provider_ar": prog["provider_ar"],
                "program_name_ar": prog["program_name_ar"],
                "program_name_en": prog["program_name_en"],
                "program_type": prog["program_type"],
                "match_status": "MATCH",
                "allocated_amount": 0.0,
                "allocation_status": "CAPACITY_CONSTRAINED",
                "term_months": prog.get("term_months"),
                "grace_period_months": prog.get("grace_period_months"),
                "official_source_url": prog.get("official_source_url"),
            })

    # Semantic Rule 1: Include POSSIBLE_MATCH programs as potential options requiring validation (0 cash allocated)
    for prog in possible_matches:
        program_allocations.append({
            "program_id": prog["program_id"],
            "program_slug": prog["program_slug"],
            "provider": prog["provider"],
            "provider_ar": prog["provider_ar"],
            "program_name_ar": prog["program_name_ar"],
            "program_name_en": prog["program_name_en"],
            "program_type": prog["program_type"],
            "match_status": "POSSIBLE_MATCH",
            "allocated_amount": None,  # NEVER allocated cash
            "allocation_status": "VALIDATION_REQUIRED",
            "term_months": prog.get("term_months"),
            "grace_period_months": prog.get("grace_period_months"),
            "official_source_url": prog.get("official_source_url"),
        })

    # Total Identified Sources (Confirmed Equity + Confirmed Facilities + Indicative Screening Program Debt)
    total_identified_sources = round(owner_equity + existing_debt + allocated_program_debt, 2)

    # Clarified Gap Metrics (Requirement 4):
    # confirmed_funding_gap = project requirement - confirmed sources
    # potential_residual_gap = remaining gap after indicative matched-program screening capacity
    confirmed_funding_gap = max(0.0, round(total_requirement - total_confirmed_sources, 2))
    potential_residual_gap = max(0.0, round(total_requirement - total_identified_sources, 2))
    residual_gap = potential_residual_gap
    surplus = max(0.0, round(total_identified_sources - total_requirement, 2))

    # Structure Metrics & Ratios
    equity_pct = (owner_equity / total_requirement) if total_requirement > 0 else 0.0
    debt_amount = existing_debt + allocated_program_debt
    debt_pct = (debt_amount / total_requirement) if total_requirement > 0 else 0.0
    de_ratio = round(debt_amount / owner_equity, 2) if owner_equity > 0 else None
    collateral_coverage = (available_collateral / debt_amount) if debt_amount > 0 else 1.0

    # Uses of Funds Breakdown
    uses = [
        {
            "category_key": "capex",
            "name_ar": "النفقات الرأسمالية والتجهيزات",
            "name_en": "Capital Expenditure & Setup",
            "amount": float(capex_assumption or total_requirement),
            "percentage": round(((capex_assumption or total_requirement) / total_requirement) * 100, 1) if total_requirement > 0 else 100.0,
        }
    ]

    # Sources of Funds Breakdown (Separating Confirmed vs Potential Indicative)
    sources = [
        {
            "source_key": "owner_equity",
            "name_ar": "رأس مال المالك (مساهمة ذاتية مؤكدة)",
            "name_en": "Owner Equity Contribution (Confirmed)",
            "source_type": "EQUITY",
            "amount": owner_equity,
            "percentage": round(equity_pct * 100, 1),
            "is_secured": True,
        }
    ]
    if existing_debt > 0:
        sources.append({
            "source_key": "existing_facilities",
            "name_ar": "تسهيلات ائتمانية قائمة معتمدة (مؤكدة)",
            "name_en": "Existing Available Credit Facilities (Confirmed)",
            "source_type": "EXISTING_DEBT",
            "amount": existing_debt,
            "percentage": round((existing_debt / total_requirement) * 100, 1) if total_requirement > 0 else 0.0,
            "is_secured": True,
        })
    for pa in program_allocations:
        if pa.get("allocated_amount") and pa["allocated_amount"] > 0:
            sources.append({
                "source_key": f"program_{pa['program_id']}",
                "name_ar": f"{pa['provider_ar']} — {pa['program_name_ar']} (خيار تمويل محتمل - استرشادي)",
                "name_en": f"{pa['provider']} — {pa['program_name_en']} (Potential Indicative Option)",
                "source_type": "PROGRAM_DEBT",
                "amount": pa["allocated_amount"],
                "percentage": round((pa["allocated_amount"] / total_requirement) * 100, 1) if total_requirement > 0 else 0.0,
                "is_secured": False,
                "program_slug": pa["program_slug"],
                "official_source_url": pa["official_source_url"],
            })
    if residual_gap > 0:
        sources.append({
            "source_key": "residual_gap",
            "name_ar": "فجوة تمويل متبقية (غير مغطاة)",
            "name_en": "Residual Unfunded Gap",
            "source_type": "UNFUNDED",
            "amount": residual_gap,
            "percentage": round((residual_gap / total_requirement) * 100, 1) if total_requirement > 0 else 0.0,
            "is_secured": False,
        })

    # Deterministic Warnings & Alerts
    warnings = []
    if residual_gap > 0:
        warnings.append({
            "code": "RESIDUAL_GAP_EXISTS",
            "severity": "CRITICAL",
            "title_ar": "توجد فجوة تمويلية متبقية غير مغطاة",
            "title_en": "Unfunded Residual Funding Gap",
            "message_ar": f"هناك عجز تمويلي قدره {residual_gap:,.0f} ر.س ({residual_gap/total_requirement*100:.1f}%) يتطلب زيادة مساهمة المالك أو إدخال شركاء أو خفض التكاليف الاستثمارية.",
            "message_en": f"An unfunded gap of {residual_gap:,.0f} SAR ({residual_gap/total_requirement*100:.1f}%) remains; requires additional equity, partners, or capex optimization.",
        })

    # Semantic Rule 5: Explicitly label 20% threshold as Saudi Business INTERNAL_SCREENING_ASSUMPTION
    if equity_pct < INTERNAL_SCREENING_ASSUMPTION_MIN_EQUITY:
        shortfall = (INTERNAL_SCREENING_ASSUMPTION_MIN_EQUITY * total_requirement) - owner_equity
        warnings.append({
            "code": "INTERNAL_SCREENING_LOW_EQUITY",
            "severity": "WARNING",
            "title_ar": "المساهمة الذاتية دون فرضية الفحص الداخلي (20%)",
            "title_en": "Owner Equity Below Internal Screening Assumption (20%)",
            "message_ar": (
                f"المساهمة الذاتية الحالية ({equity_pct*100:.1f}%) أقل من فرضية الفحص الداخلي الاسترشادية لمنصة Saudi Business (20%). "
                f"هذه فرضية فحص داخلي استرشادية (INTERNAL_SCREENING_ASSUMPTION) وليست قاعدة تنموية أو نظامية ملزمة لجميع جهات التمويل، "
                f"حيث تطبق كل جهة اشتراطات المساهمة المعتمدة الخاصة بها من واقع سجل البرامج الموثقة (Phase 18). العجز الاسترشادي: {shortfall:,.0f} ر.س."
            ),
            "message_en": (
                f"Current owner equity ({equity_pct*100:.1f}%) is below the Saudi Business internal screening assumption (20%). "
                f"This is an advisory internal screening assumption (INTERNAL_SCREENING_ASSUMPTION), not a statutory or universal minimum. "
                f"Each funding provider applies its own verified criteria from Phase 18 registry. Advisory shortfall: {shortfall:,.0f} SAR."
            ),
        })

    if safe_debt_capacity > 0 and debt_amount > safe_debt_capacity:
        excess_debt = debt_amount - safe_debt_capacity
        warnings.append({
            "code": "EXCEEDS_SAFE_DEBT_CAPACITY",
            "severity": "WARNING",
            "title_ar": "إجمالي المديونية يتجاوز طاقة الاستدانة الآمنة",
            "title_en": "Total Debt Exceeds Safe Capacity",
            "message_ar": f"إجمالي التمويل المطلوب ({debt_amount:,.0f} ر.س) يتجاوز طاقة الاستدانة التقديرية الآمنة ({safe_debt_capacity:,.0f} ر.س) بفارق {excess_debt:,.0f} ر.س.",
            "message_en": f"Total required debt ({debt_amount:,.0f} SAR) exceeds assessed safe borrowing capacity ({safe_debt_capacity:,.0f} SAR) by {excess_debt:,.0f} SAR.",
        })

    if debt_amount > 0 and available_collateral < debt_amount:
        has_guarantee = len(credit_enhancements) > 0 or any(pa.get("program_type") == "GUARANTEE" for pa in program_allocations)
        if not has_guarantee:
            warnings.append({
                "code": "COLLATERAL_SHORTFALL",
                "severity": "ADVISORY",
                "title_ar": "تغطية الضمانات العينية للمديونية جزئية",
                "title_en": "Partial Collateral Coverage",
                "message_ar": f"الضمانات الموثقة ({available_collateral:,.0f} ر.س) تغطي {collateral_coverage*100:.1f}% من إجمالي الدين. يوصى ببرامج كفالة لسد العجز.",
                "message_en": f"Verified collateral ({available_collateral:,.0f} SAR) covers {collateral_coverage*100:.1f}% of total debt. Kafalah guarantees recommended.",
            })

    # Semantic Rule 6: Deterministic Next Actions (use MATCHED_PROGRAM instead of ELIGIBLE)
    matched_count = len(matched_programs)
    next_actions = [
        {
            "step_number": 1,
            "title_ar": "تجهيز السجل التجاري والقوائم المالية المعتمدة",
            "title_en": "Prepare Commercial Registration & Audited Financial Statements",
            "status": "READY" if annual_revenue is not None else "ACTION_REQUIRED",
            "description_ar": "التأكد من سريان السجل التجاري وإيداع القوائم المالية عبر منصة قوائم.",
            "description_en": "Ensure valid Commercial Registration (CR) and deposited statements via Qawaem platform.",
        },
        {
            "step_number": 2,
            "title_ar": "توثيق صكوك وتقييمات الأصول الضامنة",
            "title_en": "Verify Collateral Deeds & Certified Valuations",
            "status": "READY" if available_collateral > 0 else "PENDING_VALUATION",
            "description_ar": "الحصول على تقييم عقاري أو أصول معتمد من مقيّم مرخص من الهيئة السعودية للمقيّمين المعتمدين (تقييم).",
            "description_en": "Obtain certified property or asset valuation from a TAQEEM accredited valuer.",
        },
        {
            "step_number": 3,
            "title_ar": "تأكيد إيداع المساهمة الذاتية في الحساب البنكي",
            "title_en": "Confirm Owner Equity Deposit in Dedicated Bank Account",
            "status": "READY" if owner_equity >= (INTERNAL_SCREENING_ASSUMPTION_MIN_EQUITY * total_requirement) else "ACTION_REQUIRED",
            "description_ar": "التحقق من كفاية المساهمة الذاتية وفق اشتراطات كل برنامج تمويلي محدد في سجل البرامج (أو فرضية الفحص الداخلي الاسترشادية 20%).",
            "description_en": "Verify owner equity against specific funding program rules from Phase 18 registry (or internal screening assumption 20%).",
        },
        {
            "step_number": 4,
            "title_ar": "التقديم عبر البوابات الرسمية للبرامج المتطابقة",
            "title_en": "Apply via Official Portals of Matched Programs",
            "status": "MATCHED_PROGRAM" if matched_count > 0 else "NO_MATCH",
            "description_ar": f"تم تحديد {matched_count} برنامج تمويلي مطابق للفحص الأولي (MATCHED_PROGRAM)؛ ابدأ التقديم عبر بوابة النفاذ الوطني الرسمية لكل جهة.",
            "description_en": f"{matched_count} matching funding program(s) identified (MATCHED_PROGRAM); apply directly via official portals.",
        },
    ]

    return {
        "study_id": study.id,
        "project_name": project.name if project else "",
        "sector": project.industry if project else "general",
        "stage": project.stage if project else "startup",
        "total_project_requirement": total_requirement,
        "owner_equity": owner_equity,
        "existing_debt": existing_debt,
        "total_confirmed_sources": total_confirmed_sources,
        "confirmed_sources": {
            "owner_equity": owner_equity,
            "existing_debt": existing_debt,
            "total_confirmed": total_confirmed_sources,
            "coverage_percentage": round((total_confirmed_sources / total_requirement) * 100, 1) if total_requirement > 0 else 0.0,
        },
        "initial_funding_gap": confirmed_funding_gap,
        "confirmed_funding_gap": confirmed_funding_gap,
        "potential_residual_gap": potential_residual_gap,
        "potential_program_capacity": allocated_program_debt,
        "allocated_program_debt": allocated_program_debt,
        "internal_screening_debt_capacity": safe_debt_capacity,
        "safe_debt_capacity": safe_debt_capacity,
        "capacity_status": capacity_status,
        "total_identified_sources": total_identified_sources,
        "residual_gap": residual_gap,
        "surplus": surplus,
        "equity_percentage": round(equity_pct, 4),
        "debt_percentage": round(debt_pct, 4),
        "debt_to_equity_ratio": de_ratio,
        "collateral_coverage_ratio": round(collateral_coverage, 4),
        "sources": sources,
        "uses": uses,
        "program_allocations": program_allocations,
        "credit_enhancements": credit_enhancements,
        "warnings": warnings,
        "next_actions": next_actions,
        "disclaimer_ar": DISCLAIMER_AR,
        "disclaimer_en": DISCLAIMER_EN,
        "version": "1.1.0",
    }
