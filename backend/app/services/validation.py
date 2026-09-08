"""Evidence-driven Market Validation OS Service (Wave 4).

Governs hypotheses, experiments, evidence collection, demand signals, customer
interviews, surveys, competitor claims, and immutable validation decisions.
Never fabricates results, demand percentages, or synthetic validation scores.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app import models

# Hypothesis Types
HYPOTHESIS_CUSTOMER_PROBLEM = "CUSTOMER_PROBLEM"
HYPOTHESIS_CUSTOMER_SEGMENT = "CUSTOMER_SEGMENT"
HYPOTHESIS_VALUE_PROPOSITION = "VALUE_PROPOSITION"
HYPOTHESIS_DEMAND = "DEMAND"
HYPOTHESIS_WILLINGNESS_TO_PAY = "WILLINGNESS_TO_PAY"
HYPOTHESIS_PRICE = "PRICE"
HYPOTHESIS_CHANNEL = "CHANNEL"
HYPOTHESIS_COMPETITOR_POSITIONING = "COMPETITOR_POSITIONING"
HYPOTHESIS_BUSINESS_MODEL = "BUSINESS_MODEL"

# Hypothesis Statuses
STATUS_NOT_TESTED = "NOT_TESTED"
STATUS_TESTING = "TESTING"
STATUS_SUPPORTED = "SUPPORTED"
STATUS_PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
STATUS_NOT_SUPPORTED = "NOT_SUPPORTED"
STATUS_INCONCLUSIVE = "INCONCLUSIVE"

# Workspace Overall Statuses
WS_STATUS_NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
WS_STATUS_IN_PROGRESS = "IN_PROGRESS"
WS_STATUS_PARTIALLY_VALIDATED = "PARTIALLY_VALIDATED"
WS_STATUS_VALIDATED = "VALIDATED"
WS_STATUS_NOT_VALIDATED = "NOT_VALIDATED"

# Decision States
DECISION_GO = "GO"
DECISION_GO_WITH_CONDITIONS = "GO_WITH_CONDITIONS"
DECISION_PIVOT = "PIVOT"
DECISION_STOP = "STOP"

# Evidence Directions
DIRECTION_SUPPORTING = "SUPPORTING"
DIRECTION_REFUTING = "REFUTING"
DIRECTION_NEUTRAL = "NEUTRAL"
VALID_DIRECTIONS = (DIRECTION_SUPPORTING, DIRECTION_REFUTING, DIRECTION_NEUTRAL)


def get_or_create_validation_workspace(
    db: Session,
    user: models.User,
    study_id: int,
) -> models.ValidationWorkspace:
    """Retrieves or initializes the validation workspace for a given study."""
    study = db.query(models.FeasibilityStudy).filter_by(id=study_id).first()
    if not study:
        raise ValueError("Feasibility study not found")
    if study.project.owner_id != user.id:
        raise PermissionError("User does not have access to this study's project")

    ws = (
        db.query(models.ValidationWorkspace)
        .filter_by(study_id=study.id)
        .order_by(models.ValidationWorkspace.id.desc())
        .first()
    )
    if not ws:
        ws = models.ValidationWorkspace(
            project_id=study.project_id,
            study_id=study.id,
            user_id=user.id,
            status=WS_STATUS_NEEDS_EVIDENCE,
        )
        db.add(ws)
        db.flush()

        # Seed initial structured hypothesis templates
        initial_hypotheses = [
            models.ValidationHypothesis(
                workspace_id=ws.id,
                hypothesis_type=HYPOTHESIS_CUSTOMER_PROBLEM,
                statement="العملاء المستهدفون في السوق يواجهون هذه المشكلة بوضوح ويبحثون عن بديل أفضل.",
                importance="CRITICAL",
                status=STATUS_NOT_TESTED,
                rationale="التحقق من وجود الألم الفعلي لدى الشريحة المستهدفة قبل بدء الإنفاق الرأسمالي.",
                created_by=user.id,
            ),
            models.ValidationHypothesis(
                workspace_id=ws.id,
                hypothesis_type=HYPOTHESIS_DEMAND,
                statement="يوجد طلب فعلي قابل للقياس يكفي للوصول إلى نقطة التعادل وتغطية المصروفات التشغيلية.",
                importance="CRITICAL",
                status=STATUS_NOT_TESTED,
                rationale="إثبات وجود رغبة مؤكدة بالشراء عبر مؤشرات طلب حقيقية وليس مجرد آراء شفهية.",
                created_by=user.id,
            ),
            models.ValidationHypothesis(
                workspace_id=ws.id,
                hypothesis_type=HYPOTHESIS_WILLINGNESS_TO_PAY,
                statement="العملاء مستعدون لدفع السعر المخطط له في دراسة الجدوى دون اشتراط خصومات تضر بالهامش.",
                importance="HIGH",
                status=STATUS_NOT_TESTED,
                rationale="التأكد من مرونة السعر وتقبل الشريحة للقيمة المادية للخدمة أو المنتج.",
                created_by=user.id,
            ),
        ]
        db.add_all(initial_hypotheses)
        db.commit()
        db.refresh(ws)

    return ws


def evaluate_workspace_status(workspace: models.ValidationWorkspace) -> Dict[str, Any]:
    """Deterministically evaluates validation workspace health and coverage.
    
    Zero synthetic percentages. Transparent counts and breakdown.
    """
    hypotheses = workspace.hypotheses
    total = len(hypotheses)
    if total == 0:
        return {
            "status": WS_STATUS_NEEDS_EVIDENCE,
            "total_hypotheses": 0,
            "counts": {},
            "critical_untested": 0,
            "critical_not_supported": 0,
            "summary_ar": "لا توجد فرضيات مسجلة بعد في مساحة التحقق.",
        }

    counts = {
        STATUS_NOT_TESTED: 0,
        STATUS_TESTING: 0,
        STATUS_SUPPORTED: 0,
        STATUS_PARTIALLY_SUPPORTED: 0,
        STATUS_NOT_SUPPORTED: 0,
        STATUS_INCONCLUSIVE: 0,
    }
    critical_untested = 0
    critical_not_supported = 0
    critical_supported = 0
    critical_total = 0

    for h in hypotheses:
        # Check for genuine non-simulated supporting evidence
        real_supporting = [
            e for e in (h.evidence or [])
            if not getattr(e, "is_simulated", False)
            and getattr(e, "evidence_direction", DIRECTION_NEUTRAL) == DIRECTION_SUPPORTING
        ]
        has_real_support = len(real_supporting) > 0

        effective_status = h.status
        # If hypothesis claims to be SUPPORTED or PARTIALLY_SUPPORTED but lacks genuine empirical supporting evidence,
        # it cannot be counted as supported for workspace validation health.
        if effective_status in (STATUS_SUPPORTED, STATUS_PARTIALLY_SUPPORTED) and not has_real_support:
            effective_status = STATUS_TESTING

        counts[effective_status] = counts.get(effective_status, 0) + 1
        if h.importance == "CRITICAL":
            critical_total += 1
            if h.status == STATUS_NOT_SUPPORTED:
                critical_not_supported += 1
            elif h.status == STATUS_SUPPORTED and has_real_support:
                critical_supported += 1
            else:
                critical_untested += 1

    if critical_not_supported > 0:
        overall_status = WS_STATUS_NOT_VALIDATED
        summary_ar = f"غير مثبت: توجد {critical_not_supported} فرضية حرجة تم دحضها بالأدلة الميدانية."
    elif critical_total > 0 and critical_supported == critical_total:
        overall_status = WS_STATUS_VALIDATED
        summary_ar = "مثبت بالأدلة: تم إثبات جميع الفرضيات الحرجة للمشروع بأدلة موثقة."
    elif counts[STATUS_SUPPORTED] > 0 or counts[STATUS_PARTIALLY_SUPPORTED] > 0 or counts[STATUS_TESTING] > 0:
        overall_status = WS_STATUS_PARTIALLY_VALIDATED
        summary_ar = "مثبت جزئياً: توجد بعض الأدلة الإيجابية وما زالت فرضيات أخرى قيد الاختبار."
    else:
        overall_status = WS_STATUS_NEEDS_EVIDENCE
        summary_ar = "يحتاج إلى أدلة: الفرضيات لم تختبر ميدانياً بعد عبر تجارب فعلية."

    return {
        "status": overall_status,
        "total_hypotheses": total,
        "counts": counts,
        "critical_total": critical_total,
        "critical_supported": critical_supported,
        "critical_untested": critical_untested,
        "critical_not_supported": critical_not_supported,
        "summary_ar": summary_ar,
    }


def add_hypothesis(
    db: Session,
    workspace_id: int,
    user: models.User,
    hypothesis_type: str,
    statement: str,
    importance: str = "HIGH",
    rationale: Optional[str] = None,
) -> models.ValidationHypothesis:
    """Adds a new hypothesis to the validation workspace."""
    ws = db.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to validation workspace")

    h = models.ValidationHypothesis(
        workspace_id=ws.id,
        hypothesis_type=hypothesis_type,
        statement=statement,
        importance=importance,
        status=STATUS_NOT_TESTED,
        rationale=rationale,
        created_by=user.id,
    )
    db.add(h)
    db.commit()
    db.refresh(h)

    # Refresh workspace status
    eval_res = evaluate_workspace_status(ws)
    ws.status = eval_res["status"]
    db.commit()

    return h


def update_hypothesis(
    db: Session,
    hypothesis_id: int,
    user: models.User,
    statement: Optional[str] = None,
    importance: Optional[str] = None,
    status: Optional[str] = None,
    rationale: Optional[str] = None,
) -> models.ValidationHypothesis:
    """Updates a hypothesis. Cannot transition to SUPPORTED without genuine evidence."""
    h = db.query(models.ValidationHypothesis).filter_by(id=hypothesis_id).first()
    if not h or h.workspace.user_id != user.id:
        raise PermissionError("Access denied to hypothesis")

    if status and status in (STATUS_SUPPORTED, STATUS_PARTIALLY_SUPPORTED):
        # Strict evidence rule: verify at least one non-simulated SUPPORTING evidence exists
        real_supporting = [
            e for e in h.evidence
            if not e.is_simulated and getattr(e, "evidence_direction", DIRECTION_NEUTRAL) == DIRECTION_SUPPORTING
        ]
        if not real_supporting:
            raise ValueError(
                "لا يمكن تحويل الفرضية إلى مثبتة (SUPPORTED) دون تسجيل أدلة ميدانية حقيقية تدعمها (SUPPORTING) أولاً."
            )
    elif status and status == STATUS_NOT_SUPPORTED:
        # Strict evidence rule: verify at least one non-simulated REFUTING evidence exists
        real_refuting = [
            e for e in h.evidence
            if not e.is_simulated and getattr(e, "evidence_direction", DIRECTION_NEUTRAL) == DIRECTION_REFUTING
        ]
        if not real_refuting:
            raise ValueError(
                "لا يمكن تحويل الفرضية إلى غير مثبتة (NOT_SUPPORTED) دون تسجيل أدلة ميدانية حقيقية تدحضها (REFUTING) أولاً."
            )

    if statement is not None:
        h.statement = statement
    if importance is not None:
        h.importance = importance
    if status is not None:
        h.status = status
    if rationale is not None:
        h.rationale = rationale

    db.commit()
    db.refresh(h)

    # Refresh workspace status
    eval_res = evaluate_workspace_status(h.workspace)
    h.workspace.status = eval_res["status"]
    db.commit()

    return h


def add_experiment(
    db: Session,
    workspace_id: int,
    user: models.User,
    experiment_type: str,
    title: str,
    objective: str,
    method: str,
    success_criteria: str,
    hypothesis_id: Optional[int] = None,
    planned_sample_size: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> models.ValidationExperiment:
    """Creates a validation experiment linked to an optional hypothesis."""
    ws = db.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to validation workspace")

    if hypothesis_id:
        h = db.query(models.ValidationHypothesis).filter_by(id=hypothesis_id).first()
        if not h:
            raise ValueError("Target hypothesis not found")
        if h.workspace_id != ws.id:
            raise ValueError("لا يمكن ربط تجربة بفرضية تابعة لمساحة عمل أخرى (Cross-workspace linking is prohibited)")
        if h.status == STATUS_NOT_TESTED:
            h.status = STATUS_TESTING

    exp = models.ValidationExperiment(
        workspace_id=ws.id,
        hypothesis_id=hypothesis_id,
        experiment_type=experiment_type,
        title=title,
        objective=objective,
        method=method,
        planned_sample_size=planned_sample_size,
        success_criteria=success_criteria,
        status="PLANNED",
        start_date=start_date,
        end_date=end_date,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def update_experiment(
    db: Session,
    experiment_id: int,
    user: models.User,
    status: Optional[str] = None,
    result_summary: Optional[str] = None,
) -> models.ValidationExperiment:
    """Updates status or result of a validation experiment."""
    exp = db.query(models.ValidationExperiment).filter_by(id=experiment_id).first()
    if not exp or exp.workspace.user_id != user.id:
        raise PermissionError("Access denied to experiment")

    if status:
        exp.status = status
    if result_summary:
        exp.result_summary = result_summary

    db.commit()
    db.refresh(exp)
    return exp


def record_evidence(
    db: Session,
    workspace_id: int,
    user: models.User,
    evidence_type: str,
    title: str,
    hypothesis_id: Optional[int] = None,
    experiment_id: Optional[int] = None,
    source_type: str = "USER_RECORDED",
    source_url: Optional[str] = None,
    source_owner: Optional[str] = None,
    notes: Optional[str] = None,
    raw_value: Optional[float] = None,
    unit: Optional[str] = None,
    evidence_strength: str = "MODERATE",
    evidence_direction: Optional[str] = None,
    is_simulated: bool = False,
    structured_payload: Optional[Dict[str, Any]] = None,
) -> models.ValidationEvidence:
    """Records verifiable empirical evidence with deterministic derived values where appropriate."""
    ws = db.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to validation workspace")

    # Cross-workspace validation
    if hypothesis_id:
        h_check = db.query(models.ValidationHypothesis).filter_by(id=hypothesis_id).first()
        if not h_check:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")
        if h_check.workspace_id != ws.id:
            raise ValueError("لا يمكن ربط دليل بفرضية تابعة لمساحة عمل أخرى (Cross-workspace linking is prohibited)")

    if experiment_id:
        exp_check = db.query(models.ValidationExperiment).filter_by(id=experiment_id).first()
        if not exp_check:
            raise ValueError(f"Experiment {experiment_id} not found")
        if exp_check.workspace_id != ws.id:
            raise ValueError("لا يمكن ربط دليل بتجربة تابعة لمساحة عمل أخرى (Cross-workspace linking is prohibited)")

    # Direction validation
    if hypothesis_id:
        if not evidence_direction:
            raise ValueError("يجب تحديد أثر الدليل على الفرضية بشكل صريح (SUPPORTING, REFUTING, NEUTRAL).")
        if evidence_direction not in VALID_DIRECTIONS:
            raise ValueError(f"Invalid evidence_direction: '{evidence_direction}'. Must be one of {VALID_DIRECTIONS}")
    else:
        if not evidence_direction:
            evidence_direction = DIRECTION_NEUTRAL
        elif evidence_direction not in VALID_DIRECTIONS:
            raise ValueError(f"Invalid evidence_direction: '{evidence_direction}'. Must be one of {VALID_DIRECTIONS}")

    payload = dict(structured_payload or {})

    # Infer refuting direction if payload explicitly refutes
    if payload.get("problem_confirmed") is False or payload.get("hypothesis_supported") is False:
        evidence_direction = DIRECTION_REFUTING

    # URL Source & Competitor validation
    if source_url is not None:
        source_url = source_url.strip()
        if source_url and not (source_url.startswith("http://") or source_url.startswith("https://")):
            raise ValueError("رابط المصدر يجب أن يكون رابط ويب صحيحاً يبدأ بـ http:// أو https://")
        if not source_url:
            source_url = None

    is_competitor = (
        evidence_type in ("COMPETITOR_BENCHMARK", "URL_SOURCE")
        or source_type in ("COMPETITOR", "URL_SOURCE")
        or "competitor" in evidence_type.lower()
        or "competitor" in (source_type or "").lower()
        or "competitor" in title.lower()
        or "منافس" in title
    )
    if is_competitor:
        if not source_url:
            raise ValueError(
                "أدلة المنافسين والمصادر الخارجية تتطلب توفير رابط ويب موثق وصحيح (source_url) يبدأ بـ http:// أو https://"
            )

    # Survey validation: derive percentages ONLY if denominator > 0
    if evidence_type in ("SURVEY", "SURVEY_RESULT"):
        responses_count = payload.get("responses_count")
        if responses_count is not None and int(responses_count) > 0:
            pos_resp = payload.get("positive_responses") if payload.get("positive_responses") is not None else payload.get("agree_count", 0)
            payload["derived_agreement_rate"] = round((float(pos_resp) / float(responses_count)) * 100, 1)
        else:
            payload["derived_agreement_rate"] = None  # Never fabricate percentage from 0 or unknown responses

    # Demand signal validation: derive conversion ONLY if sample_size > 0
    if evidence_type in ("WAITLIST", "PREORDER", "ANALYTICS", "DEMAND_SIGNAL") or payload.get("signal_type"):
        sample_size = payload.get("sample_size")
        actions = payload.get("positive_actions") if payload.get("positive_actions") is not None else (payload.get("conversions") if payload.get("conversions") is not None else payload.get("leads_count"))
        if sample_size is not None and int(sample_size) > 0 and actions is not None:
            payload["derived_conversion_rate"] = round((float(actions) / float(sample_size)) * 100, 1)
        else:
            payload["derived_conversion_rate"] = None  # Protected zero denominator

    # Pricing validation: separate assumed vs tested price
    if evidence_type in ("TRANSACTION", "PRICING_TEST") or "price" in title.lower():
        assumed = payload.get("assumed_price")
        tested = payload.get("tested_price") if payload.get("tested_price") is not None else payload.get("tested_willingness_price")
        if assumed is not None and tested is not None:
            assumed_val = float(assumed)
            tested_val = float(tested)
            payload["price_variance"] = tested_val - assumed_val
            if assumed_val > 0:
                payload["price_difference_pct"] = round(((tested_val - assumed_val) / assumed_val) * 100, 1)

    ev = models.ValidationEvidence(
        workspace_id=ws.id,
        hypothesis_id=hypothesis_id,
        experiment_id=experiment_id,
        evidence_type=evidence_type,
        title=title,
        notes=notes,
        source_type=source_type,
        source_url=source_url,
        source_owner=source_owner,
        raw_value=raw_value,
        unit=unit,
        captured_at=datetime.now(timezone.utc),
        evidence_strength=evidence_strength,
        evidence_direction=evidence_direction,
        is_simulated=is_simulated,
        structured_payload=payload,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # If linked to a hypothesis and NOT simulated, update hypothesis status deterministically
    if hypothesis_id and not is_simulated:
        h = db.query(models.ValidationHypothesis).filter_by(id=hypothesis_id).first()
        if h:
            if evidence_direction == DIRECTION_REFUTING:
                if evidence_strength in ("STRONG", "MODERATE"):
                    h.status = STATUS_NOT_SUPPORTED
            elif evidence_direction == DIRECTION_SUPPORTING:
                if evidence_strength == "STRONG" and h.status in (STATUS_NOT_TESTED, STATUS_TESTING):
                    h.status = STATUS_SUPPORTED
                elif evidence_strength == "MODERATE" and h.status == STATUS_NOT_TESTED:
                    h.status = STATUS_TESTING
            elif evidence_direction == DIRECTION_NEUTRAL:
                if h.status == STATUS_NOT_TESTED:
                    h.status = STATUS_TESTING
            db.commit()

    # Recalculate workspace health
    eval_res = evaluate_workspace_status(ws)
    ws.status = eval_res["status"]
    db.commit()

    return ev


def record_validation_decision(
    db: Session,
    workspace_id: int,
    user: models.User,
    decision: str,
    decision_reason: str,
    conditions: Optional[List[str]] = None,
) -> models.ValidationDecision:
    """Records an immutable validation decision with an evidence snapshot."""
    ws = db.query(models.ValidationWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to validation workspace")

    if decision not in (DECISION_GO, DECISION_GO_WITH_CONDITIONS, DECISION_PIVOT, DECISION_STOP):
        raise ValueError(f"Invalid decision state: {decision}")

    conditions_list = [c.strip() for c in (conditions or []) if c and c.strip()]
    eval_res = evaluate_workspace_status(ws)
    critical_total = eval_res["critical_total"]
    critical_untested = eval_res["critical_untested"]
    critical_not_supported = eval_res["critical_not_supported"]
    critical_supported = eval_res["critical_supported"]

    # Gate 1: DECISION_GO GATE
    if decision == DECISION_GO:
        if critical_total == 0:
            raise ValueError("لا يمكن اتخاذ قرار انطلاق (GO) دون وجود فرضيات حرجة محددة للمشروع.")
        if critical_untested > 0:
            raise ValueError(f"لا يمكن اتخاذ قرار انطلاق (GO) مع وجود {critical_untested} فرضيات حرجة لم تُختبر بعد.")
        if critical_not_supported > 0:
            raise ValueError(f"لا يمكن اتخاذ قرار انطلاق (GO) مع وجود {critical_not_supported} فرضيات حرجة غير مثبتة أو مدحوضة.")
        if critical_supported < critical_total:
            raise ValueError("لا يمكن اتخاذ قرار انطلاق (GO) قبل إثبات كافة الفرضيات الحرجة بالأدلة الميدانية.")

        # Real evidence check: every critical hypothesis must have real (non-simulated) supporting evidence
        for h in ws.hypotheses:
            if h.importance == "CRITICAL":
                real_supporting = [
                    e for e in h.evidence
                    if not e.is_simulated and getattr(e, "evidence_direction", DIRECTION_NEUTRAL) == DIRECTION_SUPPORTING
                ]
                if not real_supporting:
                    raise ValueError(
                        f"الفرضية الحرجة '{h.statement}' غير مدعومة بأدلة ميدانية حقيقية (لا تُقبل أدلة المحاكاة AI)."
                    )

    # Gate 2: GO_WITH_CONDITIONS GATE
    elif decision == DECISION_GO_WITH_CONDITIONS:
        if eval_res["status"] not in (WS_STATUS_PARTIALLY_VALIDATED, WS_STATUS_VALIDATED):
            raise ValueError(
                f"لا يمكن اتخاذ قرار مشروط (GO_WITH_CONDITIONS) عندما تكون حالة مساحة التحقق '{eval_res['status']}'. "
                "يتطلب القرار المشروط أن تكون مساحة العمل مثبتة جزئياً (PARTIALLY_VALIDATED) أو مثبتة (VALIDATED)."
            )
        if not conditions_list:
            raise ValueError("القرار المشروط (GO_WITH_CONDITIONS) يتطلب تحديد شرط واضح واحد على الأقل.")
        if critical_not_supported > 0:
            raise ValueError(
                f"لا يمكن اتخاذ قرار مشروط (GO_WITH_CONDITIONS) مع وجود {critical_not_supported} فرضيات حرجة غير مثبتة أو مدحوضة. "
                "يجب تغيير مسار المشروع (PIVOT) أو إيقافه (STOP) أو إطلاق دورة اختبار جديدة."
            )

    # Comprehensive immutable snapshot
    hypotheses_snapshot = [
        {
            "id": h.id,
            "type": h.hypothesis_type,
            "statement": h.statement,
            "importance": h.importance,
            "status": h.status,
            "evidence_count": len(h.evidence),
            "real_evidence_count": len([e for e in h.evidence if not e.is_simulated]),
        }
        for h in ws.hypotheses
    ]
    experiments_snapshot = [
        {
            "id": exp.id,
            "hypothesis_id": exp.hypothesis_id,
            "experiment_type": exp.experiment_type,
            "title": exp.title,
            "status": exp.status,
            "planned_sample_size": exp.planned_sample_size,
            "success_criteria": exp.success_criteria,
            "result_summary": exp.result_summary,
        }
        for exp in ws.experiments
    ]
    evidence_snapshot_items = [
        {
            "id": ev.id,
            "hypothesis_id": ev.hypothesis_id,
            "experiment_id": ev.experiment_id,
            "evidence_type": ev.evidence_type,
            "title": ev.title,
            "source_type": ev.source_type,
            "source_url": ev.source_url,
            "source_owner": ev.source_owner,
            "evidence_strength": ev.evidence_strength,
            "evidence_direction": getattr(ev, "evidence_direction", DIRECTION_NEUTRAL) or DIRECTION_NEUTRAL,
            "is_simulated": ev.is_simulated,
            "captured_at": ev.captured_at.isoformat() if ev.captured_at else None,
        }
        for ev in ws.evidence
    ]
    evidence_snapshot = {
        "evaluation_summary": eval_res,
        "hypotheses": hypotheses_snapshot,
        "experiments": experiments_snapshot,
        "evidence": evidence_snapshot_items,
        "total_evidence_records": len(ws.evidence),
        "real_evidence_records": len([e for e in ws.evidence if not e.is_simulated]),
        "supported_hypotheses": [h["statement"] for h in hypotheses_snapshot if h["status"] == STATUS_SUPPORTED],
        "contradicting_hypotheses": [h["statement"] for h in hypotheses_snapshot if h["status"] == STATUS_NOT_SUPPORTED],
        "missing_hypotheses": [h["statement"] for h in hypotheses_snapshot if h["status"] in (STATUS_NOT_TESTED, STATUS_INCONCLUSIVE)],
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }

    # Latest version number
    prev_decision = (
        db.query(models.ValidationDecision)
        .filter_by(workspace_id=ws.id)
        .order_by(models.ValidationDecision.decision_version.desc())
        .first()
    )
    new_version = (prev_decision.decision_version + 1) if prev_decision else 1

    dec = models.ValidationDecision(
        workspace_id=ws.id,
        decision=decision,
        decision_reason=decision_reason,
        conditions=conditions_list,
        evidence_snapshot=evidence_snapshot,
        decided_at=datetime.now(timezone.utc),
        decision_version=new_version,
        decided_by=user.id,
    )
    db.add(dec)
    db.commit()
    db.refresh(dec)
    return dec
