"""explainable decision snapshots

Additive migration. Adds study_decisions: immutable GO/CONDITIONAL_GO/
NO_GO/INSUFFICIENT_EVIDENCE snapshots derived deterministically from
evidence + scenario data (see app.services.decision_engine).

Revision ID: 0016_study_decisions
Revises: 0015_scenario_runs
"""
from alembic import op
import sqlalchemy as sa


revision = "0016_study_decisions"
down_revision = "0015_scenario_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("key_drivers", sa.JSON(), nullable=True),
        sa.Column("key_risks", sa.JSON(), nullable=True),
        sa.Column("evidence_references", sa.JSON(), nullable=True),
        sa.Column("scenario_references", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_study_decisions_study_id", "study_decisions", ["study_id"])


def downgrade() -> None:
    op.drop_index("ix_study_decisions_study_id", table_name="study_decisions")
    op.drop_table("study_decisions")
