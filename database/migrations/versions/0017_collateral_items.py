"""collateral items (Wave 2: Funding Intelligence)

Additive migration. Adds collateral_items: structured collateral records
attached to a study, with verification and encumbrance tracked as explicit
states rather than assumed. No lender haircut / lendable-value conversion
is stored here -- see app/services/collateral.py.

Revision ID: 0017_collateral_items
Revises: 0016_study_decisions
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_collateral_items"
down_revision = "0016_study_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collateral_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("collateral_type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reported_value", sa.Float(), nullable=False),
        sa.Column("verified_value", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="SAR"),
        sa.Column("valuation_date", sa.DateTime(), nullable=True),
        sa.Column("valuation_source", sa.String(length=200), nullable=True),
        sa.Column("ownership_status", sa.String(length=100), nullable=True),
        sa.Column("encumbrance_status", sa.String(length=30), nullable=False, server_default="UNKNOWN"),
        sa.Column("encumbrance_amount", sa.Float(), nullable=True),
        sa.Column("lien_holder", sa.String(length=200), nullable=True),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="USER_REPORTED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_collateral_items_study_id", "collateral_items", ["study_id"])


def downgrade() -> None:
    op.drop_index("ix_collateral_items_study_id", table_name="collateral_items")
    op.drop_table("collateral_items")
