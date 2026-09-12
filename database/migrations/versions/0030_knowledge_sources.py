"""Phase 7A — Governed knowledge_sources registry table.

Revision ID: 0030_knowledge_sources
Revises: 0029_knowledge_intel_learning
"""
from alembic import op
import sqlalchemy as sa

revision = "0030_knowledge_sources"
down_revision = "0029_knowledge_intel_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(80), nullable=False, server_default="UNKNOWN"),
        sa.Column("authority_type", sa.String(80), nullable=False, server_default="UNKNOWN"),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("country", sa.String(8), nullable=False, server_default="SA"),
        sa.Column("geography", sa.String(120), nullable=True),
        sa.Column("sectors", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("languages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("refresh_policy", sa.String(80), nullable=True),
        sa.Column("refresh_interval_hours", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("connector_type", sa.String(80), nullable=False, server_default="registry_only"),
        sa.Column("connector_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("key", name="uq_knowledge_sources_key"),
    )
    op.create_index("ix_knowledge_sources_key", "knowledge_sources", ["key"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_sources_key", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
