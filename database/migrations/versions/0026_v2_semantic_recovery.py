"""V2 semantic recovery: gate_choice, evidence_status, workflow_meta

Revision ID: 0026_v2_semantic_recovery
Revises: 0025_v2_study_engine
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_v2_semantic_recovery"
down_revision = "0025_v2_study_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "study_states_v2",
        sa.Column("gate_choice", sa.String(32), nullable=True),
    )
    op.add_column(
        "study_states_v2",
        sa.Column(
            "evidence_status",
            sa.String(32),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.add_column(
        "study_states_v2",
        sa.Column(
            "workflow_meta_json",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("study_states_v2", "workflow_meta_json")
    op.drop_column("study_states_v2", "evidence_status")
    op.drop_column("study_states_v2", "gate_choice")
