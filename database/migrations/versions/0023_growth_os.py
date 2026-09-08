"""growth os (Wave 6: Business Growth & Scaling OS)

Additive migration. Adds growth_workspaces, growth_scenarios,
growth_what_if_models, growth_monthly_reviews, growth_decisions,
and growth_actions tables.

Revision ID: 0023_growth_os
Revises: 0022_launch_actuals_os
"""
from alembic import op
import sqlalchemy as sa


revision = '0023_growth_os'
down_revision = '0022_launch_actuals_os'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. growth_workspaces
    op.create_table(
        'growth_workspaces',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'study_id',
            sa.Integer(),
            sa.ForeignKey('feasibility_studies.id', ondelete='CASCADE'),
            unique=True,
            nullable=False,
        ),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_growth_workspaces_study_id', 'growth_workspaces', ['study_id'], unique=True)
    op.create_index('ix_growth_workspaces_project_id', 'growth_workspaces', ['project_id'])
    op.create_index('ix_growth_workspaces_user_id', 'growth_workspaces', ['user_id'])

    # 2. growth_scenarios
    op.create_table(
        'growth_scenarios',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('growth_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scenario_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('location_region', sa.String(length=100), nullable=True),
        sa.Column('investment_required', sa.Float(), nullable=True),
        sa.Column('capacity_assumptions', sa.JSON(), nullable=False),
        sa.Column('revenue_assumptions', sa.JSON(), nullable=False),
        sa.Column('cost_assumptions', sa.JSON(), nullable=False),
        sa.Column('dependencies', sa.JSON(), nullable=False),
        sa.Column('risks', sa.JSON(), nullable=False),
        sa.Column('evidence_references', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PROPOSED', nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_growth_scenarios_workspace_id', 'growth_scenarios', ['workspace_id'])

    # 3. growth_what_if_models
    op.create_table(
        'growth_what_if_models',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('growth_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scenario_id', sa.Integer(), sa.ForeignKey('growth_scenarios.id', ondelete='SET NULL'), nullable=True),
        sa.Column('model_type', sa.String(length=50), server_default='CUSTOM', nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('user_assumptions', sa.JSON(), nullable=False),
        sa.Column('baseline_inputs', sa.JSON(), nullable=False),
        sa.Column('actual_inputs', sa.JSON(), nullable=False),
        sa.Column('derived_outputs', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_growth_what_if_models_workspace_id', 'growth_what_if_models', ['workspace_id'])
    op.create_index('ix_growth_what_if_models_scenario_id', 'growth_what_if_models', ['scenario_id'])

    # 4. growth_monthly_reviews
    op.create_table(
        'growth_monthly_reviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('growth_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('review_period', sa.String(length=50), nullable=False),
        sa.Column('version_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('actual_periods_covered', sa.JSON(), nullable=False),
        sa.Column('health_state', sa.String(length=50), nullable=False),
        sa.Column('health_snapshot', sa.JSON(), nullable=False),
        sa.Column('trend_summary', sa.JSON(), nullable=False),
        sa.Column('unit_economics_snapshot', sa.JSON(), nullable=False),
        sa.Column('risks_snapshot', sa.JSON(), nullable=False),
        sa.Column('variances_snapshot', sa.JSON(), nullable=False),
        sa.Column('cash_runway_snapshot', sa.JSON(), nullable=False),
        sa.Column('open_actions', sa.JSON(), nullable=False),
        sa.Column('scenarios_evaluated', sa.JSON(), nullable=False),
        sa.Column('missing_information', sa.JSON(), nullable=False),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_growth_monthly_reviews_workspace_id', 'growth_monthly_reviews', ['workspace_id'])

    # 5. growth_decisions
    op.create_table(
        'growth_decisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('growth_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('decision_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('decision_reason', sa.Text(), nullable=False),
        sa.Column('supporting_facts', sa.JSON(), nullable=False),
        sa.Column('contradicting_facts', sa.JSON(), nullable=False),
        sa.Column('unknowns', sa.JSON(), nullable=False),
        sa.Column('user_assumptions', sa.JSON(), nullable=False),
        sa.Column('risks', sa.JSON(), nullable=False),
        sa.Column('conditions', sa.JSON(), nullable=False),
        sa.Column('recommended_next_actions', sa.JSON(), nullable=False),
        sa.Column('pivot_validation_workspace_id', sa.Integer(), sa.ForeignKey('validation_workspaces.id', ondelete='SET NULL'), nullable=True),
        sa.Column('re_evaluation_date', sa.String(length=50), nullable=True),
        sa.Column('decided_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('decided_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_growth_decisions_workspace_id', 'growth_decisions', ['workspace_id'])

    # 6. growth_actions
    op.create_table(
        'growth_actions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('growth_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision_id', sa.Integer(), sa.ForeignKey('growth_decisions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('action_type', sa.String(length=50), server_default='REMEDIATION', nullable=False),
        sa.Column('category', sa.String(length=50), server_default='OPERATIONS', nullable=False),
        sa.Column('owner_name', sa.String(length=100), nullable=True),
        sa.Column('due_date', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.String(length=50), server_default='MEDIUM', nullable=True),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_growth_actions_workspace_id', 'growth_actions', ['workspace_id'])
    op.create_index('ix_growth_actions_decision_id', 'growth_actions', ['decision_id'])

    # 7. Add acquired_customers_count to launch_actual_periods for unit economics
    op.add_column('launch_actual_periods', sa.Column('acquired_customers_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('launch_actual_periods', 'acquired_customers_count')
    op.drop_table('growth_actions')
    op.drop_table('growth_decisions')
    op.drop_table('growth_monthly_reviews')
    op.drop_table('growth_what_if_models')
    op.drop_table('growth_scenarios')
    op.drop_table('growth_workspaces')
