"""Independent financial analyses (service-architecture completion)

Revision ID: 0025_independent_financial_analyses
Revises: 0024_wave6_integrity
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_independent_financial_analyses"
down_revision = "0024_wave6_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_analyses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=True, index=True),
        sa.Column("feasibility_study_id", sa.Integer, sa.ForeignKey("feasibility_studies.id"), nullable=True, index=True),
        sa.Column("title", sa.String(255), nullable=False, server_default="Financial analysis"),
        sa.Column("investment", sa.Float, nullable=False),
        sa.Column("annual_cash_flows", sa.JSON, nullable=True),
        sa.Column("discount_rate", sa.Float, server_default="0.1"),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("import_meta", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("financial_analyses")
