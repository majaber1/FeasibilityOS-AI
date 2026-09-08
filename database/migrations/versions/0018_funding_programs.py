"""verified funding programs and rule provenance (Wave 2: Funding Intelligence)

Additive migration. Adds funding_programs and funding_program_rules tables.
Persists official Saudi funding programs with rule-level provenance traceable
to verified official portals (.gov.sa).

Revision ID: 0018_funding_programs
Revises: 0017_collateral_items
"""
from alembic import op
import sqlalchemy as sa


revision = "0018_funding_programs"
down_revision = "0017_collateral_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop legacy unverified funding tables from initial schema if present
    op.execute("DROP TABLE IF EXISTS funding_matches")
    op.execute("DROP TABLE IF EXISTS funding_programs")

    op.create_table(
        "funding_programs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=150), nullable=False),
        sa.Column("provider_ar", sa.String(length=150), nullable=False),
        sa.Column("program_name_ar", sa.String(length=255), nullable=False),
        sa.Column("program_name_en", sa.String(length=255), nullable=False),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("program_type", sa.String(length=50), nullable=False),
        sa.Column("target_business_stage", sa.String(length=50), server_default="ALL", nullable=False),
        sa.Column("target_sectors", sa.JSON(), nullable=False),
        sa.Column("financing_min", sa.Float(), nullable=True),
        sa.Column("financing_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), server_default="SAR", nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=True),
        sa.Column("grace_period_months", sa.Integer(), nullable=True),
        sa.Column("owner_contribution_rule", sa.JSON(), nullable=True),
        sa.Column("collateral_rule", sa.JSON(), nullable=True),
        sa.Column("guarantee_rule", sa.JSON(), nullable=True),
        sa.Column("revenue_rule", sa.JSON(), nullable=True),
        sa.Column("business_age_rule", sa.JSON(), nullable=True),
        sa.Column("other_eligibility_rules", sa.JSON(), nullable=True),
        sa.Column("official_source_url", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=50), server_default="OFFICIAL_PROVIDER", nullable=False),
        sa.Column("source_owner", sa.String(length=200), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("effective_from", sa.String(length=50), nullable=True),
        sa.Column("effective_to", sa.String(length=50), nullable=True),
        sa.Column("verification_status", sa.String(length=30), server_default="VERIFIED_CURRENT", nullable=False),
        sa.Column("rule_version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_funding_programs_slug", "funding_programs", ["slug"], unique=True)
    op.create_index("ix_funding_programs_provider", "funding_programs", ["provider"])
    op.create_index("ix_funding_programs_program_type", "funding_programs", ["program_type"])
    op.create_index("ix_funding_programs_verification_status", "funding_programs", ["verification_status"])

    op.create_table(
        "funding_program_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("funding_programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_key", sa.String(length=100), nullable=False),
        sa.Column("rule_type", sa.String(length=50), server_default="ELIGIBILITY", nullable=False),
        sa.Column("structured_value", sa.JSON(), nullable=False),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("source_authority", sa.String(length=100), server_default="OFFICIAL_PROVIDER", nullable=False),
        sa.Column("verified_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("verified_by", sa.String(length=100), server_default="OFFICIAL_REGISTRY", nullable=True),
        sa.Column("rule_version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_funding_program_rules_program_id", "funding_program_rules", ["program_id"])
    op.create_index("ix_funding_program_rules_rule_key", "funding_program_rules", ["rule_key"])


def downgrade() -> None:
    op.drop_index("ix_funding_program_rules_rule_key", table_name="funding_program_rules")
    op.drop_index("ix_funding_program_rules_program_id", table_name="funding_program_rules")
    op.drop_table("funding_program_rules")

    op.drop_index("ix_funding_programs_verification_status", table_name="funding_programs")
    op.drop_index("ix_funding_programs_program_type", table_name="funding_programs")
    op.drop_index("ix_funding_programs_provider", table_name="funding_programs")
    op.drop_index("ix_funding_programs_slug", table_name="funding_programs")
    op.drop_table("funding_programs")
