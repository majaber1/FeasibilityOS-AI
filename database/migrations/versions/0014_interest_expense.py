"""add interest_expense to company_financial_periods

Additive migration. Interest Coverage (Phase 11's financial health engine)
needs operating_profit / interest_expense; annual_debt_service (already
present) is principal + interest together and is used for DSCR instead --
conflating the two would mislabel the metric, so this adds the missing
input rather than approximating it from a field that means something else.

Revision ID: 0014_interest_expense
Revises: 0013_company_financial_profile
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_interest_expense"
down_revision = "0013_company_financial_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("company_financial_periods", sa.Column("interest_expense", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("company_financial_periods", "interest_expense")
