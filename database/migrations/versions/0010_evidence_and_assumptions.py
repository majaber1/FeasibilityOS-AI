"""evidence layer: evidence_items + study_assumptions

Explicit, incremental migration adding the evidence/provenance layer on top
of the persistent study workspace. Additive only -- no existing table is
touched, so existing production rows are preserved.

Tables:
  - evidence_items      sourced facts attached to a study, with provenance
  - study_assumptions   versioned, provenance-tagged assumptions

Revision ID: 0010_evidence_and_assumptions
Revises: 0009_study_revision
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_evidence_and_assumptions"
down_revision = "0009_study_revision"
branch_labels = None
depends_on = None


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("publisher", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("value_number", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=300), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("geography", sa.String(length=100), nullable=True),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), sa.ForeignKey("evidence_items.id"), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="unverified"),
        sa.Column("authority_level", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("snapshot_text", sa.Text(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=True),
        *_ts(),
    )
    op.create_index("ix_evidence_items_study_id", "evidence_items", ["study_id"])

    op.create_table(
        "study_assumptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id"), nullable=True),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("label_en", sa.String(length=200), nullable=False),
        sa.Column("label_ar", sa.String(length=200), nullable=False),
        sa.Column("value_number", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=300), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
    )
    op.create_index("ix_study_assumptions_study_id", "study_assumptions", ["study_id"])
    op.create_index("ix_study_assumptions_key", "study_assumptions", ["key"])


def downgrade() -> None:
    op.drop_index("ix_study_assumptions_key", table_name="study_assumptions")
    op.drop_index("ix_study_assumptions_study_id", table_name="study_assumptions")
    op.drop_table("study_assumptions")

    op.drop_index("ix_evidence_items_study_id", table_name="evidence_items")
    op.drop_table("evidence_items")
