"""opportunity fit matching (Wave 3B: Opportunity Fit & Matching)

Additive migration. Adds opportunity_fit_profiles, opportunity_match_runs,
and opportunity_match_results tables.

Revision ID: 0020_opportunity_fit_matching
Revises: 0019_verified_opportunities
"""
from alembic import op
import sqlalchemy as sa


revision = "0020_opportunity_fit_matching"
down_revision = "0019_verified_opportunities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunity_fit_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("available_capital", sa.Float(), nullable=True),
        sa.Column("capital_constraint_type", sa.String(length=20), server_default="HARD", nullable=False),
        sa.Column("preferred_sectors", sa.JSON(), nullable=True),
        sa.Column("excluded_sectors", sa.JSON(), nullable=True),
        sa.Column("preferred_opportunity_types", sa.JSON(), nullable=True),
        sa.Column("opportunity_type_constraint", sa.String(length=20), server_default="PREFERENCE", nullable=False),
        sa.Column("target_region", sa.String(length=100), nullable=True),
        sa.Column("target_city", sa.String(length=100), nullable=True),
        sa.Column("preferred_business_models", sa.JSON(), nullable=True),
        sa.Column("target_customer", sa.String(length=50), nullable=True),
        sa.Column("experience_sectors", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_opportunity_fit_profiles_user_id", "opportunity_fit_profiles", ["user_id"])

    op.create_table(
        "opportunity_match_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fit_profile_id", sa.Integer(), sa.ForeignKey("opportunity_fit_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fit_profile_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("fit_profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("calculation_version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_opportunity_match_runs_user_id", "opportunity_match_runs", ["user_id"])
    op.create_index("ix_opportunity_match_runs_fit_profile_id", "opportunity_match_runs", ["fit_profile_id"])

    op.create_table(
        "opportunity_match_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_run_id", sa.Integer(), sa.ForeignKey("opportunity_match_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("verified_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_version", sa.String(length=20), nullable=False),
        sa.Column("verification_status_at_eval", sa.String(length=30), nullable=False),
        sa.Column("match_state", sa.String(length=30), nullable=False),
        sa.Column("criteria_evaluations", sa.JSON(), nullable=True),
        sa.Column("summary_reason", sa.Text(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_opportunity_match_results_match_run_id", "opportunity_match_results", ["match_run_id"])
    op.create_index("ix_opportunity_match_results_opportunity_id", "opportunity_match_results", ["opportunity_id"])
    op.create_index("ix_opportunity_match_results_match_state", "opportunity_match_results", ["match_state"])


def downgrade() -> None:
    op.drop_table("opportunity_match_results")
    op.drop_table("opportunity_match_runs")
    op.drop_table("opportunity_fit_profiles")
