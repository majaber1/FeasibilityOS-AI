"""launch actuals os (Wave 5: Launch & Actuals OS)

Additive migration. Adds launch_workspaces, launch_milestones, launch_tasks,
launch_baseline_snapshots, launch_actual_periods, and launch_reforecasts tables.

Revision ID: 0022_launch_actuals_os
Revises: 0021_validation_os
"""
from alembic import op
import sqlalchemy as sa


revision = "0022_launch_actuals_os"
down_revision = "0021_validation_os"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. launch_workspaces
    op.create_table(
        "launch_workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "study_id",
            sa.Integer(),
            sa.ForeignKey("feasibility_studies.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="PLANNED", nullable=False),
        sa.Column("target_launch_date", sa.String(length=50), nullable=True),
        sa.Column("actual_launch_date", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_launch_workspaces_study_id", "launch_workspaces", ["study_id"], unique=True)
    op.create_index("ix_launch_workspaces_project_id", "launch_workspaces", ["project_id"])
    op.create_index("ix_launch_workspaces_user_id", "launch_workspaces", ["user_id"])

    # 2. launch_milestones
    op.create_table(
        "launch_milestones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("launch_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.String(length=50), nullable=True),
        sa.Column("completed_date", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="PENDING", nullable=False),
        sa.Column("budget_allocated", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("dependency_milestone_id", sa.Integer(), sa.ForeignKey("launch_milestones.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_suggested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_launch_milestones_workspace_id", "launch_milestones", ["workspace_id"])

    # 3. launch_tasks
    op.create_table(
        "launch_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("launch_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("milestone_id", sa.Integer(), sa.ForeignKey("launch_milestones.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("due_date", sa.String(length=50), nullable=True),
        sa.Column("completed_date", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("dependency_task_id", sa.Integer(), sa.ForeignKey("launch_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_critical", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_launch_tasks_workspace_id", "launch_tasks", ["workspace_id"])
    op.create_index("ix_launch_tasks_milestone_id", "launch_tasks", ["milestone_id"])

    # 4. launch_baseline_snapshots
    op.create_table(
        "launch_baseline_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("launch_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("total_investment", sa.Float(), nullable=True),
        sa.Column("monthly_projections", sa.JSON(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("source_study_revision", sa.Integer(), nullable=True),
        sa.Column("validation_decision_id", sa.Integer(), sa.ForeignKey("validation_decisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("validation_decision_version", sa.Integer(), nullable=True),
        sa.Column("source_opportunity_id", sa.Integer(), nullable=True),
        sa.Column("source_opportunity_version", sa.String(length=30), nullable=True),
        sa.Column("funding_context", sa.JSON(), nullable=True),
        sa.Column("calculation_version", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_launch_baseline_snapshots_workspace_id", "launch_baseline_snapshots", ["workspace_id"])

    # 5. launch_actual_periods
    op.create_table(
        "launch_actual_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("launch_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_label", sa.String(length=50), nullable=False),
        sa.Column("period_order", sa.Integer(), nullable=False),
        sa.Column("actual_revenue", sa.Float(), nullable=True),
        sa.Column("transactions_count", sa.Integer(), nullable=True),
        sa.Column("average_ticket_size", sa.Float(), nullable=True),
        sa.Column("actual_capex", sa.Float(), nullable=True),
        sa.Column("actual_opex_salaries", sa.Float(), nullable=True),
        sa.Column("actual_opex_rent", sa.Float(), nullable=True),
        sa.Column("actual_opex_utilities", sa.Float(), nullable=True),
        sa.Column("actual_opex_marketing", sa.Float(), nullable=True),
        sa.Column("actual_opex_cogs", sa.Float(), nullable=True),
        sa.Column("actual_opex_other", sa.Float(), nullable=True),
        sa.Column("total_actual_opex", sa.Float(), nullable=True),
        sa.Column("net_cashflow", sa.Float(), nullable=True),
        sa.Column("closing_cash_balance", sa.Float(), nullable=True),
        sa.Column("source_type", sa.String(length=50), server_default="USER_ENTERED", nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_launch_actual_periods_workspace_id", "launch_actual_periods", ["workspace_id"])

    # 6. launch_reforecasts
    op.create_table(
        "launch_reforecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("launch_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("reforecast_title", sa.String(length=255), nullable=False),
        sa.Column("adjustment_rationale", sa.Text(), nullable=False),
        sa.Column("growth_rate_adjustment_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("opex_adjustment_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("monthly_burn_rate", sa.Float(), nullable=True),
        sa.Column("remaining_runway_months", sa.Float(), nullable=True),
        sa.Column("cash_flow_positive_month", sa.Integer(), nullable=True),
        sa.Column("financial_break_even_month", sa.Integer(), nullable=True),
        sa.Column("reforecast_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_launch_reforecasts_workspace_id", "launch_reforecasts", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("launch_reforecasts")
    op.drop_table("launch_actual_periods")
    op.drop_table("launch_baseline_snapshots")
    op.drop_table("launch_tasks")
    op.drop_table("launch_milestones")
    op.drop_table("launch_workspaces")
