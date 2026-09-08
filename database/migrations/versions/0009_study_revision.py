"""Add optimistic concurrency revision to feasibility studies.

Revision ID: 0009_study_revision
Revises: 0008_remove_auctions
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_study_revision"
down_revision = "0008_remove_auctions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feasibility_studies",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("feasibility_studies", "revision")
