"""document intake foundation: study linkage + extracted financial facts

Additive migration. Adds documents.study_id and documents.document_type
(nullable -- existing project-only documents are unaffected), plus
extracted_financial_facts for provenance-traced facts pulled from a
specific uploaded document. No automated extraction pipeline is wired up
yet (see model docstring in app/models.py); this only adds the schema
boundary so facts entered by a human reviewing a document are traceable.

Revision ID: 0012_document_intake
Revises: 0011_business_profile
"""
from alembic import op
import sqlalchemy as sa


revision = "0012_document_intake"
down_revision = "0011_business_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch_alter_table: SQLite cannot ALTER TABLE ADD COLUMN with an inline
    # FK constraint directly: it needs the copy-and-move strategy batch mode
    # provides. On Postgres/other dialects this still emits a plain ALTER.
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("study_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("document_type", sa.String(length=40), nullable=True))
        batch_op.create_foreign_key(
            "fk_documents_study_id_feasibility_studies", "feasibility_studies", ["study_id"], ["id"]
        )
    op.create_index("ix_documents_study_id", "documents", ["study_id"])

    op.create_table(
        "extracted_financial_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("value_number", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=300), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("period", sa.String(length=50), nullable=True),
        sa.Column("source_location", sa.String(length=200), nullable=True),
        sa.Column("extraction_status", sa.String(length=30), nullable=False, server_default="user_entered"),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="high"),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="confirmed"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extracted_financial_facts_study_id", "extracted_financial_facts", ["study_id"])
    op.create_index("ix_extracted_financial_facts_document_id", "extracted_financial_facts", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_extracted_financial_facts_document_id", table_name="extracted_financial_facts")
    op.drop_index("ix_extracted_financial_facts_study_id", table_name="extracted_financial_facts")
    op.drop_table("extracted_financial_facts")

    op.drop_index("ix_documents_study_id", table_name="documents")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("fk_documents_study_id_feasibility_studies", type_="foreignkey")
        batch_op.drop_column("document_type")
        batch_op.drop_column("study_id")
