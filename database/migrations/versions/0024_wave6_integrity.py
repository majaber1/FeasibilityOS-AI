"""wave6 integrity (Wave 6: Strategic Decision Scenario Linkage)

Additive migration. Adds growth_scenario_id foreign key column to growth_decisions table.

Revision ID: 0024_wave6_integrity
Revises: 0023_growth_os
"""
from alembic import op
import sqlalchemy as sa


revision = '0024_wave6_integrity'
down_revision = '0023_growth_os'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('growth_decisions') as batch_op:
        batch_op.add_column(sa.Column('growth_scenario_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_growth_decisions_growth_scenario_id', ['growth_scenario_id'])
        batch_op.create_foreign_key(
            'fk_growth_decisions_growth_scenario_id',
            'growth_scenarios',
            ['growth_scenario_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('growth_decisions') as batch_op:
        batch_op.drop_constraint('fk_growth_decisions_growth_scenario_id', type_='foreignkey')
        batch_op.drop_index('ix_growth_decisions_growth_scenario_id')
        batch_op.drop_column('growth_scenario_id')
