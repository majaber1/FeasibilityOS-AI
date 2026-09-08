"""V2 AI study engine tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_states_v2",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("study_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("project_id", sa.String(64), nullable=False, index=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("language", sa.String(5), nullable=False, server_default="ar"),
        sa.Column("phase", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("phase_history", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("profile_json", sa.JSON, nullable=True),
        sa.Column("profile_confirmed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("claims_json", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("evidence_approved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("assumptions_json", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("assumptions_approved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("financial_results_json", sa.JSON, nullable=True),
        sa.Column("verdict", sa.String(32), nullable=True),
        sa.Column("decision_rationale", sa.Text, nullable=True),
        sa.Column("decision_conditions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("decision_risks", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("decision_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("messages_json", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "study_state_versions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("study_id", sa.String(64), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("snapshot_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("study_id", "version", name="uq_study_version"),
    )


def downgrade() -> None:
    op.drop_table("study_state_versions")
    op.drop_table("study_states_v2")
