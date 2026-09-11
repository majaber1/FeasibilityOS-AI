"""Knowledge Intelligence Layer tables (Phase 6 MVP)

Revision ID: 0028_knowledge_intel
Revises: 0026_archetype_schemas
Create Date: 2026-09-11

Adds tenant-scoped knowledge documents, chunks (with embeddings),
evidence records, and study memory — same Postgres, no duplicate DB.
"""
from alembic import op
import sqlalchemy as sa

revision = "0028_knowledge_intel"
down_revision = "0027_funding_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(100), nullable=False, server_default="upload"),
        sa.Column("sector", sa.String(120), nullable=True),
        sa.Column("country", sa.String(8), nullable=False, server_default="SA"),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("document_type", sa.String(80), nullable=False, server_default="feasibility_study"),
        sa.Column("project_type", sa.String(80), nullable=True, index=True),
        sa.Column("capex", sa.JSON, nullable=True),
        sa.Column("opex", sa.JSON, nullable=True),
        sa.Column("revenue_model", sa.JSON, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("outcome", sa.JSON, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
        sa.Column("extraction_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("storage_ref", sa.String(500), nullable=True),
        sa.Column("content_type", sa.String(120), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("raw_text_excerpt", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("chunk_metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("importance", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "knowledge_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("study_id", sa.String(64), nullable=True, index=True),
        sa.Column("claim", sa.Text, nullable=False),
        sa.Column("source_document_id", sa.String(36), sa.ForeignKey("knowledge_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_chunk_id", sa.String(36), sa.ForeignKey("knowledge_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_study_memory_id", sa.String(36), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("related_project", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "study_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id"), nullable=True, index=True),
        sa.Column("source_study_id", sa.String(64), nullable=False, index=True),
        sa.Column("archetype", sa.String(80), nullable=True, index=True),
        sa.Column("project_type", sa.String(80), nullable=True),
        sa.Column("sector", sa.String(120), nullable=True),
        sa.Column("country", sa.String(8), nullable=False, server_default="SA"),
        sa.Column("assumptions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("financial_outcome", sa.JSON, nullable=True),
        sa.Column("decision", sa.JSON, nullable=True),
        sa.Column("risks", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("lessons_learned", sa.Text, nullable=True),
        sa.Column("summary_text", sa.Text, nullable=True),
        sa.Column("embedding", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "source_study_id", name="uq_study_memory_owner_study"),
    )


def downgrade() -> None:
    op.drop_table("study_memories")
    op.drop_table("knowledge_evidence")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
