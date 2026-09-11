"""Add archetype workflow fields to study_states_v2

Revision ID: 0026_archetype_schemas
Revises: 0025_v2_study_engine
Create Date: 2026-09-11

Note: shortened from 0026_archetype_assumption_schemas (33 chars) because
alembic_version.version_num is VARCHAR(32).
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_archetype_schemas"
down_revision = "0025_v2_study_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "study_states_v2",
        sa.Column("discovery_questions_json", sa.JSON, nullable=False, server_default="[]"),
    )
    op.add_column(
        "study_states_v2",
        sa.Column("structured_answers_json", sa.JSON, nullable=False, server_default="{}"),
    )
    op.add_column(
        "study_states_v2",
        sa.Column("assumptions_version", sa.Integer, nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("study_states_v2", "assumptions_version")
    op.drop_column("study_states_v2", "structured_answers_json")
    op.drop_column("study_states_v2", "discovery_questions_json")
