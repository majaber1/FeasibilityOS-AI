"""
Funding Matching Service (Phase 19: Wave 2 — Funding Intelligence).

Pure deterministic evaluation matching a feasibility study and its financial
profile against verified Saudi funding programs seeded in Phase 18.

Rules evaluated:
1. Sector Match (Project industry vs target_sectors)
2. Business Stage Match (Project stage vs target_business_stage)
3. Financing Amount Range (Funding gap vs financing_min / financing_max)
4. Owner Contribution Ratio (Actual equity vs required min_percentage)
5. Collateral Requirement (Available verified collateral vs collateral_rule)
6. Revenue Threshold (Annual revenue vs revenue_rule.max_annual_revenue)
7. Debt Capacity Advisory (Funding gap vs safe_debt_capacity)

Allowed Match States:
- MATCH: Study satisfies all verified rules currently stored for this program.
- POSSIBLE_MATCH: Meets core criteria, but non-blocking or supplemental rules
  are pending/borderline.
- NEEDS_INFORMATION: Critical required study data is missing.
- NOT_MATCHED: Explicitly fails at least one hard rule.

No fabricated credit scores, interest rates, or bank approval claims.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload

from app import models
from app.services.funding_gap import compute_funding_gap
from app.services.borrowing_capacity import estimate_borrowing_capacity
from app.services.financial_health import compute_metrics, summarize

STATUS_MATCH = "MATCH"
STATUS_POSSIBLE_MATCH = "POSSIBLE_MATCH"
STATUS_NEEDS_INFO = "NEEDS_INFORMATION"
STATUS_NOT_MATCHED = "NOT_MATCHED"
STATUS_NOT_EVALUATED = "NOT_EVALUATED"

DISCLAIMER_AR = (
    "نتائج المطابقة هي فحص آلي استرشادي مبني على القواعد المعتمدة المعلنة من الجهات "
    "التمويلية في المملكة العربية السعودية، ولا تشكل موافقة ائتمانية أو التزاماً بالتمويل."
)
DISCLAIMER_EN = (
    "Matching results are deterministic screening indicators based on published official "
    "rules from Saudi funding institutions and do not constitute credit approval or funding commitment."
)

SECTOR_SYNONYMS = {
    "tech": "technology", "it": "technology", "software": "technology",
    "saas": "technology", "retail": "retail", "ecommerce": "retail",
    "trade": "trade", "commercial": "trade", "wholesale": "wholesale",
    "services": "services", "manufacturing": "manufacturing",
    "industry": "manufacturing", "industrial": "manufacturing",
    "logistics": "logistics", "supply_chain": "logistics",
    "transport": "logistics", "healthcare": "healthcare",
    "health": "healthcare", "medical": "medical",
    "tourism": "tourism", "hospitality": "hospitality",
    "food_beverage": "food_beverage", "restaurant": "food_beverage",
    "cafe": "food_beverage", "agriculture": "agriculture",
    "agri": "agriculture", "farming": "agriculture",
    "contracting": "contracting", "construction": "contracting",
    "education": "education", "energy": "energy", "mining": "mining",
}


def _normalize_sector(raw: Optional[str]) -> str:
    if not raw:
        return ""
    clean = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return SECTOR_SYNONYMS.get(clean, clean)


def _normalize_stage(raw: Optional[str]) -> str:
    if not raw:
        return "STARTUP"
    s = raw.strip().upper()
    if s in {"IDEA", "MVP", "EARLY", "STARTUP", "PRE_REVENUE", "SEED"}:
        return "STARTUP"
    if s in {"EXPANSION", "GROWTH", "SCALE"}:
        return "EXPANSION"
    if s in {"EXISTING", "OPERATING", "MATURE"}:
        return "EXISTING"
    return "STARTUP"


def _append_eval(evals, *, rule_key, name_ar, name_en, rule_type, required,
                 actual, result, note_ar, note_en, src_url, src_auth, ver):
    evals.append({
        "rule_key": rule_key,
        "rule_name_ar": name_ar,
        "rule_name_en": name_en,
        "rule_type": rule_type,
        "required_value": required,
        "actual_value": actual,
        "result": result,
        "notes_ar": note_ar,
        "notes_en": note_en,
        "source_url": src_url,
        "source_authority": src_auth,
        "rule_version": ver,
    })


def evaluate_single_program_match(
    *,
    program: models.FundingProgram,
    study_id: int,
    study_sector: str,
    study_stage: str,
    project_cost: float,
    owner_contribution: Optional[float],
    funding_gap: float,
    current_annual_revenue: Optional[float],
    available_collateral_value: float,
    collateral_coverage_ratio: float,
    safe_debt_capacity: float,
    norm_study_stage: str = "",
) -> Dict[str, Any]:
    """Deterministically evaluates one verified funding program against study."""

    evals: List[Dict[str, Any]] = []
    passed: List[str] = []
    failed: List[str] = []
    unknown: List[str] = []
    missing: List[str] = []

    rules_map = {r.rule_key: r for r in (program.rules or [])}

    def _prov(key):
        r = rules_map.get(key)
        return (
            r.source_url if r else program.official_source_url,
            r.source_authority if r else program.source_owner,
            r.rule_version if r else program.rule_version,
        )

    def _classify(key, result):
        if result == "PASS":
            passed.append(key)
        elif result == "FAIL":
            failed.append(key)
        else:
            unknown.append(key)

    if not norm_study_stage:
        norm_study_stage = _normalize_stage(study_stage)

    # --- 1. Sector ---
    targets = [s.lower() for s in (program.target_sectors or [])]
    ns = _normalize_sector(study_sector)
    su, sa, sv = _prov("sector")
    if "all" in targets:
        sr, nar, nen = "PASS", "البرنامج يقبل جميع القطاعات المؤهلة.", "Program accepts all eligible sectors."
    elif ns and any(ns == _normalize_sector(t) or ns in t.lower() for t in targets):
        sr = "PASS"
        nar = f"قطاع المشروع ({study_sector}) ضمن المستهدف."
        nen = f"Sector ({study_sector}) is in target sectors."
    elif not ns:
        sr = "UNKNOWN"
        nar = "قطاع المشروع غير محدد."
        nen = "Project sector is not specified."
        missing.append("Study sector/industry is undefined")
    else:
        sr = "FAIL"
        nar = f"قطاع المشروع ({study_sector}) خارج المستهدف: {', '.join(program.target_sectors)}."
        nen = f"Sector ({study_sector}) not among targets: {', '.join(program.target_sectors)}."
    _append_eval(evals, rule_key="sector", name_ar="مطابقة قطاع النشاط",
                 name_en="Sector Eligibility", rule_type="ELIGIBILITY",
                 required=program.target_sectors, actual=study_sector or "UNKNOWN",
                 result=sr, note_ar=nar, note_en=nen, src_url=su, src_auth=sa, ver=sv)
    _classify("sector", sr)

    # --- 2. Business Stage ---
    ts = (program.target_business_stage or "ALL").upper()
    su2, sa2, sv2 = program.official_source_url, program.source_owner, program.rule_version
    if ts == "ALL":
        stgr = "PASS"
        stgar = "البرنامج متاح لجميع المراحل."
        stgen = "Program accepts all business stages."
    elif ts == norm_study_stage:
        stgr = "PASS"
        stgar = f"مرحلة المشروع ({norm_study_stage}) تتطابق مع المستهدف."
        stgen = f"Stage ({norm_study_stage}) matches target."
    else:
        stgr = "FAIL"
        stgar = f"البرنامج مخصص لـ ({ts}) بينما المشروع ({norm_study_stage})."
        stgen = f"Program targets ({ts}), project is ({norm_study_stage})."
    _append_eval(evals, rule_key="business_stage", name_ar="مرحلة المشروع",
                 name_en="Business Stage", rule_type="ELIGIBILITY",
                 required=ts, actual=norm_study_stage, result=stgr,
                 note_ar=stgar, note_en=stgen, src_url=su2, src_auth=sa2, ver=sv2)
    _classify("business_stage", stgr)

    # --- 3. Financing Amount ---
    fu, fa, fv = _prov("financing_limit")
    fmin, fmax = program.financing_min, program.financing_max
    if funding_gap <= 0:
        fr = "UNKNOWN"
        far = "فجوة التمويل غير محددة."
        fen = "Funding gap is zero or undefined."
        missing.append("Funding gap is zero or undefined")
    elif fmax is not None and funding_gap > fmax:
        fr = "FAIL"
        far = f"المطلوب ({funding_gap:,.0f} ر.س) يتجاوز السقف ({fmax:,.0f} ر.س)."
        fen = f"Required ({funding_gap:,.0f} SAR) exceeds ceiling ({fmax:,.0f} SAR)."
    elif fmin is not None and funding_gap < fmin:
        fr = "FAIL"
        far = f"المطلوب ({funding_gap:,.0f} ر.س) أقل من الحد الأدنى ({fmin:,.0f} ر.س)."
        fen = f"Required ({funding_gap:,.0f} SAR) below minimum ({fmin:,.0f} SAR)."
    else:
        fr = "PASS"
        far = f"المطلوب ({funding_gap:,.0f} ر.س) ضمن النطاق ({fmin or 0:,.0f}-{fmax or 0:,.0f} ر.س)."
        fen = f"Required ({funding_gap:,.0f} SAR) within range ({fmin or 0:,.0f}-{fmax or 0:,.0f} SAR)."
    _append_eval(evals, rule_key="financing_limit", name_ar="نطاق التمويل",
                 name_en="Financing Amount Range", rule_type="FINANCING_TERM",
                 required={"min": fmin, "max": fmax, "currency": "SAR"},
                 actual={"funding_gap": funding_gap, "currency": "SAR"},
                 result=fr, note_ar=far, note_en=fen, src_url=fu, src_auth=fa, ver=fv)
    _classify("financing_limit", fr)

    # --- 4. Owner Contribution ---
    or_rule = program.owner_contribution_rule or {}
    ou, oa, ov = _prov("owner_contribution")
    min_pct = or_rule.get("min_percentage")
    if min_pct is not None:
        rpct = float(min_pct)
        if project_cost > 0 and owner_contribution is not None:
            apct = owner_contribution / project_cost
            if apct >= (rpct - 0.001):
                orr = "PASS"
                oar = f"المساهمة ({apct*100:.1f}%) ≥ المطلوب ({rpct*100:.0f}%)."
                oen = f"Equity ({apct*100:.1f}%) ≥ required ({rpct*100:.0f}%)."
            else:
                orr = "FAIL"
                short = (rpct * project_cost) - owner_contribution
                oar = f"المساهمة ({apct*100:.1f}%) أقل من ({rpct*100:.0f}%). العجز: {short:,.0f} ر.س."
                oen = f"Equity ({apct*100:.1f}%) < required ({rpct*100:.0f}%). Shortfall: {short:,.0f} SAR."
        else:
            orr = "UNKNOWN"
            oar = "المساهمة أو التكلفة غير مسجلة."
            oen = "Owner contribution or project cost not recorded."
            missing.append("Owner contribution or project cost not specified")
    else:
        orr = "PASS"
        oar = "لا يشترط البرنامج نسبة محددة."
        oen = "No minimum owner contribution percentage required."
    eq_actual = round(owner_contribution / project_cost, 4) if (project_cost > 0 and owner_contribution is not None) else None
    _append_eval(evals, rule_key="owner_contribution", name_ar="المساهمة الذاتية",
                 name_en="Owner Equity Contribution", rule_type="ELIGIBILITY",
                 required={"min_percentage": min_pct} if min_pct else "NONE",
                 actual={"owner_contribution": owner_contribution, "project_cost": project_cost, "actual_percentage": eq_actual},
                 result=orr, note_ar=oar, note_en=oen, src_url=ou, src_auth=oa, ver=ov)
    _classify("owner_contribution", orr)

    # --- 5. Collateral ---
    cr_rule = program.collateral_rule or {}
    cu, ca2, cv = _prov("collateral")
    creq = cr_rule.get("required", False)
    if creq:
        if program.program_type == "GUARANTEE":
            crr = "PASS"
            car = "برامج الكفالة توفر ضمانات بديلة."
            cen = "Guarantee programs provide substitute guarantees."
        elif available_collateral_value > 0 and (available_collateral_value >= funding_gap or collateral_coverage_ratio >= 0.8):
            crr = "PASS"
            car = f"ضمانات ({available_collateral_value:,.0f} ر.س) بنسبة ({collateral_coverage_ratio*100:.1f}%) كافية."
            cen = f"Collateral ({available_collateral_value:,.0f} SAR) at ({collateral_coverage_ratio*100:.1f}%) meets requirement."
        elif available_collateral_value > 0:
            crr = "UNKNOWN"
            car = f"ضمانات جزئية ({available_collateral_value:,.0f} ر.س) قد تتطلب كفالة مكملة."
            cen = f"Partial collateral ({available_collateral_value:,.0f} SAR); supplemental guarantor may be needed."
        else:
            crr = "FAIL"
            car = "يشترط البرنامج ضمانات ولا توجد مسجلة."
            cen = "Program requires collateral; none registered."
    else:
        crr = "PASS"
        car = "لا يشترط البرنامج ضمانات مسبقة."
        cen = "No collateral prerequisite."
    _append_eval(evals, rule_key="collateral", name_ar="الضمانات",
                 name_en="Collateral Requirement", rule_type="COLLATERAL_REQUIREMENT",
                 required=cr_rule if cr_rule else {"required": False},
                 actual={"available_collateral": available_collateral_value, "coverage_ratio": round(collateral_coverage_ratio, 4)},
                 result=crr, note_ar=car, note_en=cen, src_url=cu, src_auth=ca2, ver=cv)
    _classify("collateral", crr)

    # --- 6. Revenue ---
    rr_rule = program.revenue_rule or {}
    ru, ra2, rv = _prov("revenue")
    max_rev = rr_rule.get("max_annual_revenue")
    if max_rev is not None:
        lim = float(max_rev)
        if current_annual_revenue is not None and current_annual_revenue > 0:
            if current_annual_revenue <= lim:
                rrr = "PASS"
                rar = f"الإيرادات ({current_annual_revenue:,.0f} ر.س) ≤ السقف ({lim:,.0f} ر.س)."
                ren = f"Revenue ({current_annual_revenue:,.0f} SAR) ≤ ceiling ({lim:,.0f} SAR)."
            else:
                rrr = "FAIL"
                rar = f"الإيرادات ({current_annual_revenue:,.0f} ر.س) تتجاوز السقف ({lim:,.0f} ر.س)."
                ren = f"Revenue ({current_annual_revenue:,.0f} SAR) exceeds ceiling ({lim:,.0f} SAR)."
        elif norm_study_stage == "STARTUP":
            rrr = "PASS"
            rar = "مشروع ناشئ يندرج ضمن المنشآت الصغيرة."
            ren = "Startup complies with small enterprise thresholds."
        else:
            rrr = "UNKNOWN"
            rar = "لم تسجل بيانات إيرادات."
            ren = "Revenue data not recorded."
    else:
        rrr = "PASS"
        rar = "لا يوجد سقف إيرادات."
        ren = "No revenue ceiling required."
    _append_eval(evals, rule_key="revenue", name_ar="سقف الإيرادات",
                 name_en="Revenue & Enterprise Size", rule_type="ELIGIBILITY",
                 required={"max_annual_revenue": max_rev} if max_rev else "NONE",
                 actual={"annual_revenue": current_annual_revenue},
                 result=rrr, note_ar=rar, note_en=ren, src_url=ru, src_auth=ra2, ver=rv)
    _classify("revenue", rrr)

    # --- 7. Debt Capacity Advisory ---
    if funding_gap > 0 and safe_debt_capacity > 0:
        if safe_debt_capacity >= funding_gap:
            dcr = "PASS"
            dar = f"طاقة الاستدانة ({safe_debt_capacity:,.0f} ر.س) تغطي الفجوة."
            den = f"Debt capacity ({safe_debt_capacity:,.0f} SAR) covers gap."
        else:
            dcr = "UNKNOWN"
            dar = f"الفجوة ({funding_gap:,.0f} ر.س) تتجاوز طاقة الاستدانة ({safe_debt_capacity:,.0f} ر.س)."
            den = f"Gap ({funding_gap:,.0f} SAR) exceeds capacity ({safe_debt_capacity:,.0f} SAR)."
    else:
        dcr = "UNKNOWN"
        dar = "لم يتم احتساب طاقة الاستدانة."
        den = "Debt capacity not computed."
    _append_eval(evals, rule_key="debt_capacity_advisory", name_ar="مؤشر طاقة الاستدانة",
                 name_en="Debt Capacity Fit Advisory", rule_type="ADVISORY",
                 required={"minimum_capacity_required": funding_gap},
                 actual={"safe_debt_capacity": safe_debt_capacity},
                 result=dcr, note_ar=dar, note_en=den,
                 src_url=program.official_source_url, src_auth=program.source_owner,
                 ver=program.rule_version)
    # Advisory is non-blocking for classification

    # --- Overall Status ---
    if failed:
        status = STATUS_NOT_MATCHED
        reason_ar = f"المشروع لا يستوفي {len(failed)} من الشروط الإلزامية."
        reason_en = f"Study fails {len(failed)} mandatory rule(s)."
    elif unknown and ("financing_limit" in unknown or "owner_contribution" in unknown):
        status = STATUS_NEEDS_INFO
        reason_ar = "يتعذر تقييم الأهلية لنقص بيانات أساسية."
        reason_en = "Cannot complete evaluation due to missing core data."
    elif unknown:
        status = STATUS_POSSIBLE_MATCH
        reason_ar = "مؤهل مبدئياً مع اشتراطات فرعية تحتاج تحقق."
        reason_en = "Meets core parameters with secondary conditions to verify."
    else:
        status = STATUS_MATCH
        reason_ar = "بيانات الدراسة تستوفي جميع القواعد المسجلة."
        reason_en = "Study satisfies all verified rules for this program."

    return {
        "program_id": program.id,
        "program_slug": program.slug,
        "provider": program.provider,
        "provider_ar": program.provider_ar,
        "program_name_ar": program.program_name_ar,
        "program_name_en": program.program_name_en,
        "program_type": program.program_type,
        "target_business_stage": program.target_business_stage,
        "financing_min": program.financing_min,
        "financing_max": program.financing_max,
        "term_months": program.term_months,
        "grace_period_months": program.grace_period_months,
        "official_source_url": program.official_source_url,
        "source_owner": program.source_owner,
        "rule_version": program.rule_version,
        "last_verified_at": program.last_verified_at.isoformat() if program.last_verified_at else None,
        "overall_match_status": status,
        "status_reason_ar": reason_ar,
        "status_reason_en": reason_en,
        "passed_rules": passed,
        "failed_rules": failed,
        "unknown_rules": unknown,
        "missing_information": missing,
        "rule_evaluations": evals,
    }


def evaluate_study_funding_matches(
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
    """Evaluates all verified Saudi funding programs against a feasibility study."""

    project_investment = float(project.investment or 0.0) if project else 0.0
    gap_res = compute_funding_gap(
        capex_assumption=capex_assumption,
        project_investment=project_investment,
        owner_contribution=owner_contribution,
        existing_facilities=existing_facilities,
    )
    total_cost = gap_res["total_project_requirement"]
    gap_amount = gap_res["funding_gap"]
    owner_cap = gap_res["owner_available_capital"]

    collat_list = collateral_dicts or []
    verified = [c for c in collat_list if c.get("verification_status") == "VERIFIED"]
    total_cv = sum(float(c.get("market_value", 0.0)) for c in verified)
    pledged = sum(float(c.get("pledged_amount", 0.0)) for c in verified)
    avail_c = max(0.0, total_cv - pledged)
    cov_ratio = (avail_c / gap_amount) if gap_amount > 0 else 0.0

    annual_rev = None
    safe_cap = 0.0
    health_score = None
    if financial_period_dict:
        annual_rev = float(financial_period_dict.get("revenue") or 0.0)
        metrics = compute_metrics(financial_period_dict)
        health_summary = summarize(metrics)
        health_score = health_summary.get("score")
        ebitda = float(financial_period_dict.get("ebitda") or 0.0)
        existing_debt = float(financial_period_dict.get("total_debt") or financial_period_dict.get("long_term_debt") or 0.0)
        debt_service = float(financial_period_dict.get("debt_service") or 0.0)
        cap_eval = estimate_borrowing_capacity(
            ebitda=ebitda if ebitda else None,
            existing_debt=existing_debt if existing_debt else None,
            annual_debt_service=debt_service if debt_service else None,
        )
        safe_cap = float(cap_eval.get("base_capacity") or 0.0) if cap_eval.get("status") == "CALCULATED" else 0.0

    sector = project.industry if project else "general"
    stage = project.stage if project else "startup"
    n_stage = _normalize_stage(stage)

    programs = (
        db.query(models.FundingProgram)
        .options(joinedload(models.FundingProgram.rules))
        .filter(models.FundingProgram.verification_status == "VERIFIED_CURRENT")
        .order_by(models.FundingProgram.id.asc())
        .all()
    )

    matches = []
    counts = {STATUS_MATCH: 0, STATUS_POSSIBLE_MATCH: 0, STATUS_NEEDS_INFO: 0, STATUS_NOT_MATCHED: 0}

    for prog in programs:
        m = evaluate_single_program_match(
            program=prog, study_id=study.id, study_sector=sector,
            study_stage=stage, project_cost=total_cost, owner_contribution=owner_cap,
            funding_gap=gap_amount, current_annual_revenue=annual_rev,
            available_collateral_value=avail_c, collateral_coverage_ratio=cov_ratio,
            safe_debt_capacity=safe_cap, norm_study_stage=n_stage,
        )
        matches.append(m)
        st = m["overall_match_status"]
        if st in counts:
            counts[st] += 1

    order = {STATUS_MATCH: 0, STATUS_POSSIBLE_MATCH: 1, STATUS_NEEDS_INFO: 2, STATUS_NOT_MATCHED: 3}
    matches.sort(key=lambda m: (order.get(m["overall_match_status"], 99), -(m.get("financing_max") or 0)))

    return {
        "study_id": study.id,
        "study_profile_snapshot": {
            "project_name": project.name if project else "",
            "sector": sector, "stage": stage,
            "total_project_requirement": total_cost,
            "owner_contribution": owner_cap, "funding_gap": gap_amount,
            "available_collateral": avail_c,
            "collateral_coverage_ratio": round(cov_ratio, 4),
            "annual_revenue": annual_rev,
            "safe_debt_capacity": safe_cap,
            "financial_health_score": health_score,
        },
        "total_programs_evaluated": len(programs),
        "matches_count": counts[STATUS_MATCH],
        "possible_matches_count": counts[STATUS_POSSIBLE_MATCH],
        "needs_information_count": counts[STATUS_NEEDS_INFO],
        "not_matched_count": counts[STATUS_NOT_MATCHED],
        "matches": matches,
        "disclaimer_ar": DISCLAIMER_AR,
        "disclaimer_en": DISCLAIMER_EN,
        "calculation_version": "1.0.0",
    }
