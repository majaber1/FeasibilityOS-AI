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


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    # Dialect-safe + idempotent additive columns (SQLite and Postgres).
    existing = _existing_columns("study_states_v2")
    if "gate_choice" not in existing:
        op.add_column(
            "study_states_v2",
            sa.Column("gate_choice", sa.String(length=32), nullable=True),
        )
    if "evidence_status" not in existing:
        op.add_column(
            "study_states_v2",
            sa.Column(
                "evidence_status",
                sa.String(length=32),
                server_default="not_started",
                nullable=False,
            ),
        )
    if "workflow_meta_json" not in existing:
        op.add_column(
            "study_states_v2",
            sa.Column(
                "workflow_meta_json",
                sa.JSON(),
                server_default=sa.text("'{}'"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    existing = _existing_columns("study_states_v2")
    if "workflow_meta_json" in existing:
        op.drop_column("study_states_v2", "workflow_meta_json")
    if "evidence_status" in existing:
        op.drop_column("study_states_v2", "evidence_status")
    if "gate_choice" in existing:
        op.drop_column("study_states_v2", "gate_choice")
