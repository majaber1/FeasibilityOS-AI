"""Service architecture: entitlements, proposals, notifications, analytics

Revision ID: 0007_service_architecture
Revises: 0006_account_security
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_service_architecture"
down_revision = "0006_account_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_entitlements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id"), index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("service_key", sa.String(50), index=True, nullable=False),
        sa.Column("enabled", sa.Boolean, default=True),
        sa.Column("plan", sa.String(30), default="starter"),
        sa.Column("quota", sa.Integer, nullable=True),
        sa.Column("used", sa.Integer, default=0),
        sa.Column("reset_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("proposal_type", sa.String(50), default="commercial"),
        sa.Column("status", sa.String(30), default="draft"),
        sa.Column("locale", sa.String(5), default="ar"),
        sa.Column("payload", sa.JSON, default=dict),
        sa.Column("version", sa.String(20), default="1.0"),
        sa.Column("feasibility_study_id", sa.Integer, sa.ForeignKey("feasibility_studies.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("title_ar", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("entity", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("is_read", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("service_key", sa.String(50), index=True),
        sa.Column("entity", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("meta", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("notifications")
    op.drop_table("proposals")
    op.drop_table("service_entitlements")
