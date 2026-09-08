"""validation os (Wave 4: Validation OS)

Additive migration. Adds validation_workspaces, validation_hypotheses,
validation_experiments, validation_evidence, and validation_decisions tables.

Revision ID: 0021_validation_os
Revises: 0020_opportunity_fit_matching
"""
from alembic import op
import sqlalchemy as sa


revision = "0021_validation_os"
down_revision = "0020_opportunity_fit_matching"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. validation_workspaces
    op.create_table(
        "validation_workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="NEEDS_EVIDENCE", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_validation_workspaces_project_id", "validation_workspaces", ["project_id"])
    op.create_index("ix_validation_workspaces_study_id", "validation_workspaces", ["study_id"])
    op.create_index("ix_validation_workspaces_user_id", "validation_workspaces", ["user_id"])

    # 2. validation_hypotheses
    op.create_table(
        "validation_hypotheses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("validation_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hypothesis_type", sa.String(length=50), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=20), server_default="HIGH", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="NOT_TESTED", nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_validation_hypotheses_workspace_id", "validation_hypotheses", ["workspace_id"])

    # 3. validation_experiments
    op.create_table(
        "validation_experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("validation_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hypothesis_id", sa.Integer(), sa.ForeignKey("validation_hypotheses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("experiment_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("planned_sample_size", sa.Integer(), nullable=True),
        sa.Column("success_criteria", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="PLANNED", nullable=False),
        sa.Column("start_date", sa.String(length=50), nullable=True),
        sa.Column("end_date", sa.String(length=50), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_validation_experiments_workspace_id", "validation_experiments", ["workspace_id"])
    op.create_index("ix_validation_experiments_hypothesis_id", "validation_experiments", ["hypothesis_id"])

    # 4. validation_evidence
    op.create_table(
        "validation_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("validation_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hypothesis_id", sa.Integer(), sa.ForeignKey("validation_hypotheses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("validation_experiments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=50), server_default="USER_RECORDED", nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_owner", sa.String(length=200), nullable=True),
        sa.Column("raw_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("captured_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("evidence_strength", sa.String(length=20), server_default="MODERATE", nullable=False),
        # Evidence direction defaults strictly to NEUTRAL (never SUPPORTING)
        sa.Column("evidence_direction", sa.String(length=20), server_default="NEUTRAL", nullable=False),
        sa.Column("is_simulated", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("structured_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_validation_evidence_workspace_id", "validation_evidence", ["workspace_id"])
    op.create_index("ix_validation_evidence_hypothesis_id", "validation_evidence", ["hypothesis_id"])
    op.create_index("ix_validation_evidence_experiment_id", "validation_evidence", ["experiment_id"])

    # 5. validation_decisions
    op.create_table(
        "validation_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("validation_workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("decision_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_validation_decisions_workspace_id", "validation_decisions", ["workspace_id"])


def downgrade() -> None:
    # Drop tables in reverse foreign key order
    op.drop_table("validation_decisions")
    op.drop_table("validation_evidence")
    op.drop_table("validation_experiments")
    op.drop_table("validation_hypotheses")
    op.drop_table("validation_workspaces")
