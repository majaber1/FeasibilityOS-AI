"""Domain Service for Wave 5 Launch Execution, Actuals & Reforecasting OS.

Provides:
- Launch workspace initialization strictly gated by Wave 4 validation decisions (GO / GO_WITH_CONDITIONS).
- Pre-launch execution milestone and task tracking with Saudi regulatory categories.
- Pure baseline snapshot copying from approved feasibility studies without synthetic fabrication.
- Actual operational performance recording where unknown/missing is strictly distinct from zero.
- Transparent variance calculation where missing baseline or missing actual yields NOT_AVAILABLE.
- Dynamic scenario reforecasting with transparent USER_ASSUMPTION attribution, explicit runway, and separate cash-flow-positive vs financial break-even calculation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app import models

# Workspace statuses
WS_STATUS_PLANNED = "PLANNED"
WS_STATUS_IN_PROGRESS = "IN_PROGRESS"
WS_STATUS_BLOCKED = "BLOCKED"
WS_STATUS_LAUNCHED = "LAUNCHED"
WS_STATUS_PAUSED = "PAUSED"
WS_STATUS_CANCELLED = "CANCELLED"
VALID_WORKSPACE_STATUSES = {
    WS_STATUS_PLANNED,
    WS_STATUS_IN_PROGRESS,
    WS_STATUS_BLOCKED,
    WS_STATUS_LAUNCHED,
    WS_STATUS_PAUSED,
    WS_STATUS_CANCELLED,
}

# Milestone categories
CATEGORY_REGULATORY = "REGULATORY"
CATEGORY_LOCATION = "LOCATION"
CATEGORY_EQUIPMENT = "EQUIPMENT"
CATEGORY_TEAM = "TEAM"
CATEGORY_MARKETING = "MARKETING"
CATEGORY_OPERATIONS = "OPERATIONS"

# Milestone statuses
MILESTONE_PENDING = "PENDING"
MILESTONE_IN_PROGRESS = "IN_PROGRESS"
MILESTONE_COMPLETED = "COMPLETED"
MILESTONE_BLOCKED = "BLOCKED"
MILESTONE_DELAYED = "DELAYED"
VALID_MILESTONE_STATUSES = {
    MILESTONE_PENDING,
    MILESTONE_IN_PROGRESS,
    MILESTONE_COMPLETED,
    MILESTONE_BLOCKED,
    MILESTONE_DELAYED,
}

# Task statuses
TASK_PENDING = "PENDING"
TASK_IN_PROGRESS = "IN_PROGRESS"
TASK_COMPLETED = "COMPLETED"
TASK_BLOCKED = "BLOCKED"
TASK_CANCELLED = "CANCELLED"
VALID_TASK_STATUSES = {
    TASK_PENDING,
    TASK_IN_PROGRESS,
    TASK_COMPLETED,
    TASK_BLOCKED,
    TASK_CANCELLED,
}

# Variance alert levels
ALERT_NOT_AVAILABLE = "NOT_AVAILABLE"
ALERT_NORMAL = "NORMAL"
ALERT_WATCH = "WATCH"
ALERT_MATERIAL_VARIANCE = "MATERIAL_VARIANCE"

# Source types for actuals
SOURCE_USER_ENTERED = "USER_ENTERED"
SOURCE_IMPORTED = "IMPORTED"
SOURCE_SYSTEM_INTEGRATION = "SYSTEM_INTEGRATION"
SOURCE_DOCUMENT_BACKED = "DOCUMENT_BACKED"
VALID_SOURCE_TYPES = {
    SOURCE_USER_ENTERED,
    SOURCE_IMPORTED,
    SOURCE_SYSTEM_INTEGRATION,
    SOURCE_DOCUMENT_BACKED,
}


def get_or_create_launch_workspace(
    db: Session,
    user: models.User,
    study_id: int,
) -> models.LaunchWorkspace:
    """Fetches or initializes the launch workspace for a study.

    Enforces validation gate: rejects launch creation unless the latest validation
    decision is GO or GO_WITH_CONDITIONS. Rejects STOP, PIVOT, and missing decisions.
    """
    study = db.query(models.FeasibilityStudy).filter_by(id=study_id).first()
    if not study:
        raise ValueError(f"Feasibility study {study_id} not found")
    if study.project.owner_id != user.id:
        raise PermissionError("Access denied to feasibility study")

    ws = db.query(models.LaunchWorkspace).filter_by(study_id=study_id).first()
    if ws:
        return ws

    # Check Validation Decision Gate on the CURRENT (latest) validation cycle
    val_workspaces = db.query(models.ValidationWorkspace).filter_by(study_id=study_id).order_by(models.ValidationWorkspace.id.desc()).all()
    current_val_ws = val_workspaces[0] if val_workspaces else None

    if not current_val_ws or not current_val_ws.decisions:
        raise ValueError(
            "لا يمكن تفعيل مساحة الإطلاق دون وجود قرار تحقق ميداني رسمي معتمد (GO أو GO_WITH_CONDITIONS) في دورة التحقق الحالية. "
            "لم يتم توثيق أي قرار تحقق رسمي في الدورة الحالية حتى الآن."
        )

    latest_dec = current_val_ws.decisions[0]
    if latest_dec.decision not in ("GO", "GO_WITH_CONDITIONS"):
        dec_name = latest_dec.decision or "UNKNOWN"
        raise ValueError(
            f"لا يمكن بدء مساحة الإطلاق بناءً على قرار '{dec_name}' في دورة التحقق الحالية. "
            "يتطلب الإطلاق قرار انطلاق كامل (GO) أو انطلاق مشروط (GO_WITH_CONDITIONS) معتمد في الدورة الحالية النشطة."
        )

    if not ws:
        ws = models.LaunchWorkspace(
            study_id=study.id,
            project_id=study.project_id,
            user_id=user.id,
            status=WS_STATUS_PLANNED,
        )
        db.add(ws)
        db.commit()
        db.refresh(ws)

        # Seed standard suggested pre-launch checklist items
        # Budgets are NOT invented; they remain None until user explicitly allocates.
        # Marked as suggested / applicability to confirm by founder.
        suggested_checklist = [
            (
                CATEGORY_REGULATORY,
                "إصدار السجل التجاري ورخصة بلدي وشهادة الدفاع المدني",
                "استكمال المتطلبات النظامية والتراخيص الحكومية عبر منصة بلدي ووزارة التجارة (عنصر مقترح - يرجى تأكيد انطباقه على نشاطك).",
            ),
            (
                CATEGORY_LOCATION,
                "تحديد واستئجار الموقع التجاري وتوثيق عقد إيجار",
                "اختيار الموقع المطابق للاشتراطات الفنية وتوقيع العقد عبر شبكة إيجار (عنصر مقترح - يرجى تأكيد انطباقه على نشاطك).",
            ),
            (
                CATEGORY_EQUIPMENT,
                "شراء وتوريد وتجهيز المعدات والتجهيزات الأساسية",
                "التعاقد مع الموردين المعتمدين وتركيب التجهيزات الخاصة بالنشاط (عنصر مقترح - يرجى تأكيد انطباقه على نشاطك).",
            ),
            (
                CATEGORY_TEAM,
                "استقطاب وتوظيف الكفاءات وتحقيق نسب التوطين عبر قوى",
                "إصدار التأشيرات أو التعاقد المحلي وتوثيق عقود العمل في منصة قوى (عنصر مقترح - يرجى تأكيد انطباقه على نشاطك).",
            ),
            (
                CATEGORY_MARKETING,
                "تنفيذ الحملة التسويقية والتسجيل المسبق (Pre-Launch)",
                "حملة إعلانية واختبار جاهزية العمليات التشغيلية وتجربة العميل (عنصر مقترح - يرجى تأكيد انطباقه على نشاطك).",
            ),
            (
                CATEGORY_OPERATIONS,
                "الافتتاح الرسمي والتشغيل الكامل والربط مع زاتكا",
                "إطلاق المبيعات الكامل وربط الفوترة الإلكترونية (ZATCA) وأجهزة نقاط البيع (عنصر مقترح - يرجى تأكيد انطباقه على نشاطك).",
            ),
        ]

        for cat, title, desc in suggested_checklist:
            m = models.LaunchMilestone(
                workspace_id=ws.id,
                category=cat,
                title=title,
                description=desc,
                budget_allocated=None,  # No synthetic budgets
                actual_cost=None,
                status=MILESTONE_PENDING,
                is_suggested=True,
            )
            db.add(m)

        # Baseline Snapshot: Copy ONLY real planning values from study without inventing numbers.
        investment_total = None
        if study.project and study.project.investment:
            investment_total = float(study.project.investment)
        elif (study.payload or {}).get("investment"):
            investment_total = float(study.payload["investment"])

        # Extract monthly projections from feasibility study if explicitly present
        monthly_projections = []
        study_payload = study.payload or {}
        raw_monthly = (
            study_payload.get("monthly_projections")
            or study_payload.get("financial_plan", {}).get("monthly_projections")
            or (study_payload.get("step_4") or {}).get("monthly_projections")
            or (study_payload.get("step_3") or {}).get("monthly_projections")
            or (study_payload.get("step_5") or {}).get("monthly_projections")
            or (study.results and study.results[0].detail.get("monthly_projections"))
        )
        if raw_monthly and isinstance(raw_monthly, list):
            for idx, p in enumerate(raw_monthly, 1):
                if isinstance(p, dict):
                    monthly_projections.append({
                        "month": p.get("month", idx),
                        "period_label": p.get("period_label", f"M{idx:02d}"),
                        "projected_revenue": p.get("projected_revenue"),
                        "projected_capex": p.get("projected_capex"),
                        "projected_opex": p.get("projected_opex"),
                        "projected_net_cashflow": p.get("projected_net_cashflow"),
                    })

        # Lineage metadata
        source_opp_id = getattr(study, "source_opportunity_id", None)
        source_opp_ver = getattr(study, "source_opportunity_version", None)
        funding_ctx = study_payload.get("funding_context")

        snapshot = models.LaunchBaselineSnapshot(
            workspace_id=ws.id,
            snapshot_version=1,
            total_investment=investment_total,
            monthly_projections=monthly_projections,
            frozen_at=datetime.now(timezone.utc),
            source_study_revision=study.revision,
            validation_decision_id=latest_dec.id,
            validation_decision_version=getattr(latest_dec, "decision_version", 1),
            source_opportunity_id=source_opp_id,
            source_opportunity_version=source_opp_ver,
            funding_context=funding_ctx,
            calculation_version="v1.0.0-real-lineage",
            notes="نسخة خط أساس مجمدة مطابقة للمدخلات التقديرية الحقيقية المعتمدة لدراسة الجدوى دون أي تقديرات مصطنعة.",
        )
        db.add(snapshot)
        db.commit()
        db.refresh(ws)

    return ws


def transition_launch_workspace_status(
    db: Session,
    workspace_id: int,
    user: models.User,
    target_status: str,
    actual_launch_date: Optional[str] = None,
    target_launch_date: Optional[str] = None,
) -> models.LaunchWorkspace:
    """Explicitly updates launch workspace status.
    
    Actual launch date is recorded ONLY on explicit launch transition.
    """
    ws = db.query(models.LaunchWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to launch workspace")

    target_status = target_status.strip().upper()
    if target_status not in VALID_WORKSPACE_STATUSES:
        raise ValueError(
            f"Invalid target_status: '{target_status}'. Allowed: {sorted(list(VALID_WORKSPACE_STATUSES))}"
        )

    if target_status != WS_STATUS_LAUNCHED and actual_launch_date is not None and actual_launch_date.strip() != "":
        raise ValueError(
            f"actual_launch_date cannot be set when status is '{target_status}'. It may be persisted only when status is LAUNCHED."
        )

    ws.status = target_status
    if target_status == WS_STATUS_LAUNCHED:
        ws.actual_launch_date = (
            actual_launch_date.strip()
            if (actual_launch_date and actual_launch_date.strip())
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

    if target_launch_date:
        ws.target_launch_date = target_launch_date.strip()

    db.commit()
    db.refresh(ws)
    return ws


def add_launch_milestone(
    db: Session,
    workspace_id: int,
    user: models.User,
    category: str,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    budget_allocated: Optional[float] = None,
    owner_name: Optional[str] = None,
    dependency_milestone_id: Optional[int] = None,
    is_suggested: bool = False,
    status: Optional[str] = None,
) -> models.LaunchMilestone:
    """Adds a custom milestone to the launch workspace."""
    ws = db.query(models.LaunchWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to launch workspace")

    if dependency_milestone_id is not None:
        dep_m = db.query(models.LaunchMilestone).filter_by(id=dependency_milestone_id, workspace_id=ws.id).first()
        if not dep_m:
            raise ValueError(
                f"Referenced milestone dependency {dependency_milestone_id} does not exist or does not belong to launch workspace {workspace_id}"
            )

    milestone_status = MILESTONE_PENDING
    if status is not None:
        status_norm = status.strip().upper()
        if status_norm not in VALID_MILESTONE_STATUSES:
            raise ValueError(
                f"Invalid milestone status: '{status}'. Allowed: {sorted(list(VALID_MILESTONE_STATUSES))}"
            )
        milestone_status = status_norm

    m = models.LaunchMilestone(
        workspace_id=ws.id,
        category=category,
        title=title,
        description=description,
        due_date=due_date,
        budget_allocated=budget_allocated,
        actual_cost=None,
        owner_name=owner_name,
        dependency_milestone_id=dependency_milestone_id,
        status=milestone_status,
        is_suggested=is_suggested,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def update_launch_milestone(
    db: Session,
    milestone_id: int,
    user: models.User,
    status: Optional[str] = None,
    actual_cost: Optional[float] = None,
    budget_allocated: Optional[float] = None,
    completed_date: Optional[str] = None,
    owner_name: Optional[str] = None,
    due_date: Optional[str] = None,
) -> models.LaunchMilestone:
    """Updates progress, owner, or costs of a milestone."""
    m = db.query(models.LaunchMilestone).filter_by(id=milestone_id).first()
    if not m or m.workspace.user_id != user.id:
        raise PermissionError("Access denied to milestone")

    if status:
        status_norm = status.strip().upper()
        if status_norm not in VALID_MILESTONE_STATUSES:
            raise ValueError(
                f"Invalid milestone status: '{status}'. Allowed: {sorted(list(VALID_MILESTONE_STATUSES))}"
            )
        m.status = status_norm
        if status_norm == MILESTONE_COMPLETED and not m.completed_date:
            m.completed_date = completed_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if actual_cost is not None:
        m.actual_cost = actual_cost
    if budget_allocated is not None:
        m.budget_allocated = budget_allocated
    if owner_name is not None:
        m.owner_name = owner_name
    if due_date is not None:
        m.due_date = due_date
    if completed_date:
        m.completed_date = completed_date

    db.commit()
    db.refresh(m)
    return m


def add_launch_task(
    db: Session,
    workspace_id: int,
    user: models.User,
    title: str,
    milestone_id: Optional[int] = None,
    description: Optional[str] = None,
    owner_name: Optional[str] = None,
    due_date: Optional[str] = None,
    dependency_task_id: Optional[int] = None,
    is_critical: bool = False,
    status: Optional[str] = None,
) -> models.LaunchTask:
    """Creates a discrete execution task linked to a milestone or workspace."""
    ws = db.query(models.LaunchWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to launch workspace")

    if milestone_id is not None:
        m = db.query(models.LaunchMilestone).filter_by(id=milestone_id, workspace_id=ws.id).first()
        if not m:
            raise ValueError(f"Milestone {milestone_id} does not belong to workspace {workspace_id}")

    if dependency_task_id is not None:
        dep_t = db.query(models.LaunchTask).filter_by(id=dependency_task_id, workspace_id=ws.id).first()
        if not dep_t:
            raise ValueError(
                f"Referenced task dependency {dependency_task_id} does not exist or does not belong to launch workspace {workspace_id}"
            )

    task_status = TASK_PENDING
    if status is not None:
        status_norm = status.strip().upper()
        if status_norm not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Invalid task status: '{status}'. Allowed: {sorted(list(VALID_TASK_STATUSES))}"
            )
        task_status = status_norm

    task = models.LaunchTask(
        workspace_id=ws.id,
        milestone_id=milestone_id,
        title=title,
        description=description,
        owner_name=owner_name,
        due_date=due_date,
        dependency_task_id=dependency_task_id,
        is_critical=is_critical,
        status=task_status,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_launch_task(
    db: Session,
    task_id: int,
    user: models.User,
    status: Optional[str] = None,
    owner_name: Optional[str] = None,
    due_date: Optional[str] = None,
    completed_date: Optional[str] = None,
) -> models.LaunchTask:
    """Updates status, owner, or completion of a task."""
    task = db.query(models.LaunchTask).filter_by(id=task_id).first()
    if not task or task.workspace.user_id != user.id:
        raise PermissionError("Access denied to task")

    if status:
        status_norm = status.strip().upper()
        if status_norm not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Invalid task status: '{status}'. Allowed: {sorted(list(VALID_TASK_STATUSES))}"
            )
        task.status = status_norm
        if status_norm == TASK_COMPLETED and not task.completed_date:
            task.completed_date = completed_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if owner_name is not None:
        task.owner_name = owner_name
    if due_date is not None:
        task.due_date = due_date
    if completed_date is not None:
        task.completed_date = completed_date

    db.commit()
    db.refresh(task)
    return task


def record_actual_period(
    db: Session,
    workspace_id: int,
    user: models.User,
    period_label: str,
    period_order: int,
    actual_revenue: Optional[float] = None,
    transactions_count: Optional[int] = None,
    acquired_customers_count: Optional[int] = None,
    average_ticket_size: Optional[float] = None,
    actual_capex: Optional[float] = None,
    actual_opex_salaries: Optional[float] = None,
    actual_opex_rent: Optional[float] = None,
    actual_opex_utilities: Optional[float] = None,
    actual_opex_marketing: Optional[float] = None,
    actual_opex_cogs: Optional[float] = None,
    actual_opex_other: Optional[float] = None,
    total_actual_opex: Optional[float] = None,
    closing_cash_balance: Optional[float] = None,
    source_type: str = SOURCE_USER_ENTERED,
    source_reference: Optional[str] = None,
    notes: Optional[str] = None,
) -> models.LaunchActualPeriod:
    """Records empirical operational actuals for a period.

    Missing fields remain NULL / UNKNOWN. Zero strictly means the user entered 0.0.
    Does NOT automatically change workspace status to LAUNCHED.
    Derived totals are computed ONLY when required inputs are known.
    """
    ws = db.query(models.LaunchWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to launch workspace")

    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(f"Invalid source_type: '{source_type}'. Allowed: {sorted(list(VALID_SOURCE_TYPES))}")

    # Derive AOV only when both revenue and count are known (>0)
    aov = average_ticket_size
    if aov is None and transactions_count and transactions_count > 0 and actual_revenue is not None and actual_revenue >= 0:
        aov = round(actual_revenue / transactions_count, 2)

    # Derived total OPEX:
    # If explicitly provided by caller, use it.
    # Otherwise, compute ONLY if all 6 breakdown fields are provided (not None).
    # If all breakdown fields are None -> total_actual_opex remains None.
    # If some are None, do not silently assume 0 -> remain None.
    opex_fields = [
        actual_opex_salaries,
        actual_opex_rent,
        actual_opex_utilities,
        actual_opex_marketing,
        actual_opex_cogs,
        actual_opex_other,
    ]
    calc_total_opex = total_actual_opex
    if calc_total_opex is None:
        if all(x is not None for x in opex_fields):
            calc_total_opex = round(sum(float(x) for x in opex_fields), 2)
        elif all(x is None for x in opex_fields):
            calc_total_opex = None
        else:
            calc_total_opex = None

    # Derived Net Cashflow:
    # Only calculate if actual_revenue, actual_capex, and total_actual_opex are all known.
    net_cf = None
    if actual_revenue is not None and actual_capex is not None and calc_total_opex is not None:
        net_cf = round(float(actual_revenue) - float(actual_capex) - float(calc_total_opex), 2)

    # Check if period already exists; if so update, otherwise create
    existing = (
        db.query(models.LaunchActualPeriod)
        .filter_by(workspace_id=ws.id, period_order=period_order)
        .first()
    )
    if existing:
        existing.period_label = period_label
        existing.actual_revenue = actual_revenue
        existing.transactions_count = transactions_count
        existing.acquired_customers_count = acquired_customers_count
        existing.average_ticket_size = aov
        existing.actual_capex = actual_capex
        existing.actual_opex_salaries = actual_opex_salaries
        existing.actual_opex_rent = actual_opex_rent
        existing.actual_opex_utilities = actual_opex_utilities
        existing.actual_opex_marketing = actual_opex_marketing
        existing.actual_opex_cogs = actual_opex_cogs
        existing.actual_opex_other = actual_opex_other
        existing.total_actual_opex = calc_total_opex
        existing.net_cashflow = net_cf
        existing.closing_cash_balance = closing_cash_balance
        existing.source_type = source_type
        existing.source_reference = source_reference
        existing.notes = notes
        existing.recorded_by = user.id
        period_record = existing
    else:
        period_record = models.LaunchActualPeriod(
            workspace_id=ws.id,
            period_label=period_label,
            period_order=period_order,
            actual_revenue=actual_revenue,
            transactions_count=transactions_count,
            acquired_customers_count=acquired_customers_count,
            average_ticket_size=aov,
            actual_capex=actual_capex,
            actual_opex_salaries=actual_opex_salaries,
            actual_opex_rent=actual_opex_rent,
            actual_opex_utilities=actual_opex_utilities,
            actual_opex_marketing=actual_opex_marketing,
            actual_opex_cogs=actual_opex_cogs,
            actual_opex_other=actual_opex_other,
            total_actual_opex=calc_total_opex,
            net_cashflow=net_cf,
            closing_cash_balance=closing_cash_balance,
            source_type=source_type,
            source_reference=source_reference,
            notes=notes,
            recorded_by=user.id,
        )
        db.add(period_record)

    # Note: Status is NOT mutated automatically to LAUNCHED.
    db.commit()
    db.refresh(period_record)
    return period_record


def calculate_period_variance(
    baseline_projection: Optional[Dict[str, Any]],
    actual_period: models.LaunchActualPeriod,
) -> Dict[str, Any]:
    """Calculates forecast vs actual variance.
    
    If either baseline or actual is unknown/None, variance is strictly NOT_AVAILABLE.
    Alerts (NORMAL, WATCH, MATERIAL_VARIANCE) are produced ONLY when both sides are known.
    """
    proj_rev = baseline_projection.get("projected_revenue") if baseline_projection else None
    proj_opex = baseline_projection.get("projected_opex") if baseline_projection else None
    proj_capex = baseline_projection.get("projected_capex") if baseline_projection else None
    proj_net = baseline_projection.get("projected_net_cashflow") if baseline_projection else None

    act_rev = actual_period.actual_revenue
    act_opex = actual_period.total_actual_opex
    act_capex = actual_period.actual_capex
    act_net = actual_period.net_cashflow

    # Revenue variance
    rev_diff = None
    rev_pct = None
    rev_state = "NOT_AVAILABLE"
    if proj_rev is not None and act_rev is not None:
        rev_diff = round(float(act_rev) - float(proj_rev), 2)
        if float(proj_rev) > 0:
            rev_pct = round((rev_diff / float(proj_rev)) * 100, 1)
        rev_state = "AVAILABLE"

    # OPEX variance
    opex_diff = None
    opex_pct = None
    opex_state = "NOT_AVAILABLE"
    if proj_opex is not None and act_opex is not None:
        opex_diff = round(float(act_opex) - float(proj_opex), 2)
        if float(proj_opex) > 0:
            opex_pct = round((opex_diff / float(proj_opex)) * 100, 1)
        opex_state = "AVAILABLE"

    # Net cashflow variance
    net_diff = None
    if proj_net is not None and act_net is not None:
        net_diff = round(float(act_net) - float(proj_net), 2)

    # Alert determination
    if rev_state == "NOT_AVAILABLE" or opex_state == "NOT_AVAILABLE":
        alert = ALERT_NOT_AVAILABLE
        explanation_ar = "لا يمكن حساب الانحراف لعدم توفر بيانات خط الأساس التقديري أو الأداء الفعلي بالكامل."
    else:
        worst_variance = max(
            abs(rev_pct) if rev_pct is not None else 0,
            abs(opex_pct) if opex_pct is not None else 0,
        )
        if worst_variance > 25.0:
            alert = ALERT_MATERIAL_VARIANCE
            explanation_ar = f"انحراف جوهري يتجاوز 25% (فارق الإيراد {rev_diff:,.0f} ر.س، فارق التكاليف {opex_diff:,.0f} ر.س)."
        elif worst_variance > 10.0:
            alert = ALERT_WATCH
            explanation_ar = f"انحراف متوسط يستدعي المتابعة (فارق الإيراد {rev_diff:,.0f} ر.س)."
        else:
            alert = ALERT_NORMAL
            explanation_ar = "الأداء الفعلي يسير ضمن الحدود المتوقعة لخطة العمل (انحراف أقل من 10%)."

    return {
        "period_label": actual_period.period_label,
        "period_order": actual_period.period_order,
        "projected": {
            "revenue": proj_rev,
            "opex": proj_opex,
            "capex": proj_capex,
            "net_cashflow": proj_net,
        },
        "actual": {
            "revenue": act_rev,
            "opex": act_opex,
            "capex": act_capex,
            "net_cashflow": act_net,
            "transactions_count": actual_period.transactions_count,
            "average_ticket_size": actual_period.average_ticket_size,
        },
        "variance": {
            "revenue_diff": rev_diff,
            "revenue_pct": rev_pct,
            "revenue_state": rev_state,
            "opex_diff": opex_diff,
            "opex_pct": opex_pct,
            "opex_state": opex_state,
            "net_diff": net_diff,
        },
        "alert": alert,
        "explanation_ar": explanation_ar,
    }


def evaluate_workspace_variances(
    ws: models.LaunchWorkspace,
) -> Dict[str, Any]:
    """Generates variance analysis comparing recorded actuals against frozen baseline."""
    snapshot = ws.baseline_snapshots[0] if ws.baseline_snapshots else None
    proj_map = {}
    if snapshot and snapshot.monthly_projections:
        for p in snapshot.monthly_projections:
            proj_map[p.get("month")] = p

    period_variances = []
    has_any_comparable = False
    worst_variance_found = 0.0

    for act in ws.actual_periods:
        baseline_p = proj_map.get(act.period_order)
        var_res = calculate_period_variance(baseline_p, act)
        period_variances.append(var_res)
        if var_res["alert"] != ALERT_NOT_AVAILABLE:
            has_any_comparable = True
            v = var_res["variance"]
            rev_pct = v.get("revenue_pct")
            opex_pct = v.get("opex_pct")
            current_worst = max(
                abs(rev_pct) if rev_pct is not None else 0,
                abs(opex_pct) if opex_pct is not None else 0,
            )
            worst_variance_found = max(worst_variance_found, current_worst)

    if not ws.actual_periods:
        overall_health = "PENDING_ACTUALS"
        summary_ar = "المشروع في مرحلة التخطيط / لم يتم إدخال بيانات فعلية بعد."
    elif not has_any_comparable:
        overall_health = ALERT_NOT_AVAILABLE
        summary_ar = "بيانات المقارنة غير مكتملة (خط الأساس أو الأداء الفعلي غير متوفرين للحساب)."
    elif worst_variance_found > 25.0:
        overall_health = ALERT_MATERIAL_VARIANCE
        summary_ar = "تنبيه: انحراف تراكمي جوهري يتجاوز 25% مقارنة بالتوقعات المعتمدة. يلزم إجراء إعادة تنبؤ."
    elif worst_variance_found > 10.0:
        overall_health = ALERT_WATCH
        summary_ar = "انحراف معتدل (بين 10% و 25%). الأداء قيد المتابعة والتحفظ."
    else:
        overall_health = ALERT_NORMAL
        summary_ar = "الأداء الميداني الفعلي متطابق ومستقر مع تقديرات خط الأساس المعتمد."

    return {
        "overall_health": overall_health,
        "summary_ar": summary_ar,
        "period_variances": period_variances,
    }


def generate_reforecast(
    db: Session,
    workspace_id: int,
    user: models.User,
    reforecast_title: str,
    adjustment_rationale: str,
    growth_rate_adjustment_pct: float = 0.0,
    opex_adjustment_pct: float = 0.0,
    explicit_cash_balance: Optional[float] = None,
) -> models.LaunchReforecast:
    """Generates an updated forward projection combining actual history with explicit user assumptions.

    Rules:
    - No fabricated fallbacks (no 50k revenue, 25k opex).
    - Total investment is NEVER equated to cash balance.
    - Cash runway requires an explicit known cash balance; otherwise NOT_AVAILABLE.
    - Burn rate represents negative cash consumption only.
    - First cash-flow-positive month is distinct from financial break-even.
    """
    ws = db.query(models.LaunchWorkspace).filter_by(id=workspace_id).first()
    if not ws or ws.user_id != user.id:
        raise PermissionError("Access denied to launch workspace")

    snapshot = ws.baseline_snapshots[0] if ws.baseline_snapshots else None
    latest_actual = ws.actual_periods[-1] if ws.actual_periods else None

    # Determine cash balance:
    # Must be explicitly provided or recorded in latest actual period closing_cash_balance.
    # NEVER fallback to total investment!
    current_cash: Optional[float] = None
    if explicit_cash_balance is not None:
        current_cash = float(explicit_cash_balance)
    elif latest_actual and latest_actual.closing_cash_balance is not None:
        current_cash = float(latest_actual.closing_cash_balance)

    # Burn rate: Represents actual negative net cash consumption
    # Periods where net_cashflow is negative
    monthly_burn: Optional[float] = None
    if ws.actual_periods:
        negative_cfs = [
            abs(p.net_cashflow)
            for p in ws.actual_periods
            if p.net_cashflow is not None and p.net_cashflow < 0
        ]
        if negative_cfs:
            monthly_burn = round(sum(negative_cfs) / len(negative_cfs), 2)
        elif any(p.net_cashflow is not None for p in ws.actual_periods):
            # Cash-flow positive or zero; burn rate is 0
            monthly_burn = 0.0

    # Runway calculation: Requires both known cash balance AND burn rate
    runway_months: Optional[float] = None
    if current_cash is not None and monthly_burn is not None:
        if monthly_burn > 0:
            runway_months = round(current_cash / monthly_burn, 1)
        elif monthly_burn == 0:
            runway_months = None  # Not burning cash

    # Forward 12-month projections
    # Uses existing approved baseline where available, or extrapolates from latest known actuals.
    # If required input is missing, values remain None (NEEDS_INFORMATION).
    rev_multiplier = 1.0 + (growth_rate_adjustment_pct / 100.0)
    opex_multiplier = 1.0 + (opex_adjustment_pct / 100.0)

    proj_map = {}
    if snapshot and snapshot.monthly_projections:
        for p in snapshot.monthly_projections:
            proj_map[p.get("month")] = p

    reforecast_months = []
    cash_flow_positive_month: Optional[int] = None
    financial_break_even_month: Optional[int] = None

    cum_net_cash = 0.0
    initial_inv = snapshot.total_investment if snapshot and snapshot.total_investment else None
    has_projections = False

    for m in range(1, 13):
        base_p = proj_map.get(m)
        base_rev = base_p.get("projected_revenue") if base_p else None
        base_opex = base_p.get("projected_opex") if base_p else None

        # Fallback to latest known actual if baseline is absent for this month
        if base_rev is None and latest_actual and latest_actual.actual_revenue is not None:
            base_rev = latest_actual.actual_revenue
        if base_opex is None and latest_actual and latest_actual.total_actual_opex is not None:
            base_opex = latest_actual.total_actual_opex

        if base_rev is not None and base_opex is not None:
            has_projections = True
            adj_rev = round(float(base_rev) * rev_multiplier, 2)
            adj_opex = round(float(base_opex) * opex_multiplier, 2)
            m_net_cf = round(adj_rev - adj_opex, 2)
            cum_net_cash += m_net_cf

            if m_net_cf > 0 and cash_flow_positive_month is None:
                cash_flow_positive_month = m

            if initial_inv and cum_net_cash >= initial_inv and financial_break_even_month is None:
                financial_break_even_month = m

            reforecast_months.append({
                "month": m,
                "period_label": f"M{m:02d}",
                "reforecast_revenue": adj_rev,
                "reforecast_opex": adj_opex,
                "reforecast_net_cashflow": m_net_cf,
                "cumulative_net_cashflow": round(cum_net_cash, 2),
            })
        else:
            reforecast_months.append({
                "month": m,
                "period_label": f"M{m:02d}",
                "reforecast_revenue": None,
                "reforecast_opex": None,
                "reforecast_net_cashflow": None,
                "status": "NEEDS_INFORMATION",
            })

    next_version = len(ws.reforecasts) + 1
    reforecast = models.LaunchReforecast(
        workspace_id=ws.id,
        version_number=next_version,
        reforecast_title=reforecast_title,
        adjustment_rationale=adjustment_rationale,
        growth_rate_adjustment_pct=growth_rate_adjustment_pct,
        opex_adjustment_pct=opex_adjustment_pct,
        monthly_burn_rate=monthly_burn,
        remaining_runway_months=runway_months,
        cash_flow_positive_month=cash_flow_positive_month,
        financial_break_even_month=financial_break_even_month,
        reforecast_payload={
            "created_at": datetime.now(timezone.utc).isoformat(),
            "actual_periods_included": len(ws.actual_periods),
            "current_cash_balance": current_cash,
            "assumptions": {
                "growth_rate_adjustment_pct": growth_rate_adjustment_pct,
                "opex_adjustment_pct": opex_adjustment_pct,
                "classification": "USER_ASSUMPTION",
                "is_indicative_scenario": True,
            },
            "status": "COMPLETED" if has_projections else "NEEDS_INFORMATION",
            "monthly_projections": reforecast_months,
        },
    )
    db.add(reforecast)
    db.commit()
    db.refresh(reforecast)
    return reforecast
