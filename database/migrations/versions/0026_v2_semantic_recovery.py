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
    # Idempotent additive columns for preview/local DBs that may already have them.
    op.execute("ALTER TABLE study_states_v2 ADD COLUMN IF NOT EXISTS gate_choice VARCHAR(32)")
    op.execute(
        "ALTER TABLE study_states_v2 ADD COLUMN IF NOT EXISTS evidence_status "
        "VARCHAR(32) DEFAULT 'not_started' NOT NULL"
    )
    op.execute(
        "ALTER TABLE study_states_v2 ADD COLUMN IF NOT EXISTS workflow_meta_json "
        "JSON DEFAULT '{}' NOT NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE study_states_v2 DROP COLUMN IF EXISTS workflow_meta_json")
    op.execute("ALTER TABLE study_states_v2 DROP COLUMN IF EXISTS evidence_status")
    op.execute("ALTER TABLE study_states_v2 DROP COLUMN IF EXISTS gate_choice")
