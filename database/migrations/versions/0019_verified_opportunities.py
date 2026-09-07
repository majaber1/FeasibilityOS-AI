"""verified opportunities and franchise registry (Wave 3: Opportunities & Franchise)

Additive migration. Adds verified_opportunities and opportunity_version_history tables.
Adds source opportunity lineage columns to feasibility_studies.

Revision ID: 0019_verified_opportunities
Revises: 0018_funding_programs
"""
from alembic import op
import sqlalchemy as sa


revision = "0019_verified_opportunities"
down_revision = "0018_funding_programs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "verified_opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title_ar", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=False),
        sa.Column("opportunity_type", sa.String(length=50), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=False),
        sa.Column("subsector", sa.String(length=150), nullable=True),
        sa.Column("business_model", sa.String(length=100), nullable=True),
        sa.Column("target_customer", sa.String(length=100), nullable=True),
        sa.Column("geography", sa.String(length=100), server_default="KSA_NATIONAL", nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("investment_min", sa.Float(), nullable=True),
        sa.Column("investment_max", sa.Float(), nullable=True),
        sa.Column("franchise_fee", sa.Float(), nullable=True),
        sa.Column("royalty_model", sa.String(length=200), nullable=True),
        sa.Column("required_space", sa.String(length=100), nullable=True),
        sa.Column("business_stage", sa.String(length=50), server_default="STARTUP", nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("brand_name", sa.String(length=200), nullable=True),
        sa.Column("official_source_url", sa.String(length=500), nullable=False),
        sa.Column("source_owner", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=50), server_default="OFFICIAL_GOVERNMENT", nullable=False),
        sa.Column("source_evidence", sa.JSON(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("effective_from", sa.String(length=50), nullable=True),
        sa.Column("effective_to", sa.String(length=50), nullable=True),
        sa.Column("source_last_modified", sa.String(length=50), nullable=True),
        sa.Column("verification_status", sa.String(length=30), server_default="UNVERIFIED", nullable=False),
        sa.Column("data_version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("facts_breakdown", sa.JSON(), nullable=True),
        sa.Column("field_provenance", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_verified_opportunities_slug", "verified_opportunities", ["slug"], unique=True)
    op.create_index("ix_verified_opportunities_opportunity_type", "verified_opportunities", ["opportunity_type"])
    op.create_index("ix_verified_opportunities_sector", "verified_opportunities", ["sector"])
    op.create_index("ix_verified_opportunities_verification_status", "verified_opportunities", ["verification_status"])

    op.create_table(
        "opportunity_version_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("verified_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_version", sa.String(length=20), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("change_reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_opportunity_version_history_opportunity_id", "opportunity_version_history", ["opportunity_id"])

    with op.batch_alter_table("feasibility_studies") as batch_op:
        batch_op.add_column(sa.Column("source_opportunity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_opportunity_version", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("source_opportunity_lineage", sa.JSON(), nullable=True))
        batch_op.create_index("ix_feasibility_studies_source_opportunity_id", ["source_opportunity_id"])
        batch_op.create_foreign_key(
            "fk_feasibility_studies_source_opportunity",
            "verified_opportunities",
            ["source_opportunity_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("feasibility_studies") as batch_op:
        batch_op.drop_constraint("fk_feasibility_studies_source_opportunity", type_="foreignkey")
        batch_op.drop_index("ix_feasibility_studies_source_opportunity_id")
        batch_op.drop_column("source_opportunity_lineage")
        batch_op.drop_column("source_opportunity_version")
        batch_op.drop_column("source_opportunity_id")

    op.drop_index("ix_opportunity_version_history_opportunity_id", table_name="opportunity_version_history")
    op.drop_table("opportunity_version_history")

    op.drop_index("ix_verified_opportunities_verification_status", table_name="verified_opportunities")
    op.drop_index("ix_verified_opportunities_sector", table_name="verified_opportunities")
    op.drop_index("ix_verified_opportunities_opportunity_type", table_name="verified_opportunities")
    op.drop_index("ix_verified_opportunities_slug", table_name="verified_opportunities")
    op.drop_table("verified_opportunities")
