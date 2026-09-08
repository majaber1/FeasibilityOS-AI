"""Remove the discontinued auctions feature and its stored data.

Revision ID: 0008_remove_auctions
Revises: 0007_service_architecture
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_remove_auctions"
down_revision = "0007_service_architecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auction_bids")
    op.execute("DROP TABLE IF EXISTS auctions")


def downgrade() -> None:
    op.create_table(
        "auctions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80)),
        sa.Column("description", sa.Text),
        sa.Column("seller_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("asking_price", sa.Float),
        sa.Column("reserve_price", sa.Float),
        sa.Column("starts_at", sa.DateTime),
        sa.Column("ends_at", sa.DateTime),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "auction_bids",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("auction_id", sa.Integer, sa.ForeignKey("auctions.id"), nullable=False),
        sa.Column("bidder_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("amount", sa.Float),
        sa.Column("kind", sa.String(30), default="expression_of_interest"),
        sa.Column("message", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
