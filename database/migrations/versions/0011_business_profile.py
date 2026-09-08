"""structured business profile (one per study)

Additive migration. Adds business_profiles, reused by both the feasibility
flow and the funding flow so a business's qualitative facts (activity,
description, city, capacity, legal entity type...) are entered once.

Revision ID: 0011_business_profile
Revises: 0010_evidence_and_assumptions
"""
from alembic import op
import sqlalchemy as sa


revision = "0011_business_profile"
down_revision = "0010_evidence_and_assumptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("study_id", sa.Integer(), sa.ForeignKey("feasibility_studies.id"), nullable=False),
        sa.Column("business_activity", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("customer_segment", sa.String(length=200), nullable=True),
        sa.Column("capacity_value", sa.Float(), nullable=True),
        sa.Column("capacity_unit", sa.String(length=50), nullable=True),
        sa.Column("legal_entity_type", sa.String(length=50), nullable=True),
        sa.Column("ownership_notes", sa.Text(), nullable=True),
        sa.Column("is_existing_business", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("company_age_years", sa.Float(), nullable=True),
        sa.Column("current_revenue", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_business_profiles_study_id", "business_profiles", ["study_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_business_profiles_study_id", table_name="business_profiles")
    op.drop_table("business_profiles")
