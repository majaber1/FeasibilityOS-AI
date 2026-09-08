"""deterministic scenario runs (Conservative/Base/Optimistic)

Additive migration. Adds scenario_runs: immutable, deterministic scenario
snapshots computed from a study's assumptions plus explicit overrides (see
app.api.scenarios) -- replaces the legacy blanket +/-% approach the
now-unused sensitivity_scenarios table represented (that table is left in
place; nothing currently writes to it, but dropping it is out of scope for
this additive migration).

Revision ID: 0015_scenario_runs
Revises: 0014_interest_expense
"""
from alembic import op
import sqlalchemy as sa


revision = "0015_scenario_runs"
down_revision = "0014_interest_expense"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenario_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("scenario_type", sa.String(length=20), nullable=False),
        sa.Column("scenario_name", sa.String(length=200), nullable=False),
        sa.Column("assumption_overrides", sa.JSON(), nullable=True),
        sa.Column("source_assumption_values", sa.JSON(), nullable=True),
        sa.Column("financial_result_snapshot", sa.JSON(), nullable=True),
        sa.Column("calculation_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scenario_runs_study_id", "scenario_runs", ["study_id"])


def downgrade() -> None:
    op.drop_index("ix_scenario_runs_study_id", table_name="scenario_runs")
    op.drop_table("scenario_runs")
