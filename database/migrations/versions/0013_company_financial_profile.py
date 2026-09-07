"""structured company financial profile (period financial statements)

Additive migration. Adds company_financial_periods: one row per (study,
period) holding an existing business's financial-statement metrics, each
nullable (never defaulted/invented) and classified by source trust level.

Revision ID: 0013_company_financial_profile
Revises: 0012_document_intake
"""
from alembic import op
import sqlalchemy as sa


revision = "0013_company_financial_profile"
down_revision = "0012_document_intake"
branch_labels = None
depends_on = None

_METRIC_COLUMNS = (
    "revenue", "gross_profit", "ebitda", "operating_profit", "net_profit", "cash",
    "current_assets", "current_liabilities", "total_assets", "total_liabilities",
    "equity", "existing_debt", "annual_debt_service", "accounts_receivable",
    "inventory", "capital_expenditure",
)


def upgrade() -> None:
    op.create_table(
        "company_financial_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("period", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="unverified"),
        *(sa.Column(name, sa.Float(), nullable=True) for name in _METRIC_COLUMNS),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        # Declared inline (not via a separate create_unique_constraint call
        # after create_table) because SQLite cannot ALTER TABLE ADD
        # CONSTRAINT without batch mode; inline works on every dialect.
        sa.UniqueConstraint("study_id", "period", name="uq_company_financial_period"),
    )
    op.create_index("ix_company_financial_periods_study_id", "company_financial_periods", ["study_id"])


def downgrade() -> None:
    op.drop_index("ix_company_financial_periods_study_id", table_name="company_financial_periods")
    op.drop_table("company_financial_periods")
