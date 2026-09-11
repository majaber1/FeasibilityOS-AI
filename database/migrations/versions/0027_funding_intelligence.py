"""Placeholder revision matching DB stamp from parallel funding work.

Revision ID: 0027_funding_intelligence
Revises: 0026_archetype_schemas
Create Date: 2026-09-11

This environment's alembic_version was already stamped at
0027_funding_intelligence without the migration file present on this branch.
This no-op revision restores a linear history so Phase 6 can continue.
"""
from alembic import op

revision = "0027_funding_intelligence"
down_revision = "0026_archetype_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: tables/objects for this stamp are not required by Knowledge MVP.
    pass


def downgrade() -> None:
    pass
