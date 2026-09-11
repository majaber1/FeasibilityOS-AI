"""Phase 6.1 — Knowledge Intelligence quality / similarity / influence columns.

Revision ID: 0029_knowledge_intel_learning
Revises: 0028_knowledge_intel
"""
from alembic import op
import sqlalchemy as sa

revision = "0029_knowledge_intel_learning"
down_revision = "0028_knowledge_intel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_documents", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("quality_breakdown", sa.JSON(), nullable=True))
    op.add_column(
        "knowledge_documents",
        sa.Column("reference_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("knowledge_documents", sa.Column("geography", sa.String(120), nullable=True))
    op.add_column("knowledge_documents", sa.Column("business_model", sa.String(120), nullable=True))

    op.add_column("knowledge_evidence", sa.Column("assumption_key", sa.String(120), nullable=True))
    op.add_column("knowledge_evidence", sa.Column("reason", sa.Text(), nullable=True))

    op.add_column("study_memories", sa.Column("conditions", sa.JSON(), nullable=True))
    op.add_column("study_memories", sa.Column("influence_summary", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("study_memories", "influence_summary")
    op.drop_column("study_memories", "conditions")
    op.drop_column("knowledge_evidence", "reason")
    op.drop_column("knowledge_evidence", "assumption_key")
    op.drop_column("knowledge_documents", "business_model")
    op.drop_column("knowledge_documents", "geography")
    op.drop_column("knowledge_documents", "reference_count")
    op.drop_column("knowledge_documents", "quality_breakdown")
    op.drop_column("knowledge_documents", "quality_score")
