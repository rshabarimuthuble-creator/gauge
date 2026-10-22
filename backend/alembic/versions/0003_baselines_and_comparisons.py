"""baselines_and_comparisons

Revision ID: 0003_baselines_and_comparisons
Revises: 0002_evaluation_engine
Create Date: 2026-10-10 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0003_baselines_and_comparisons'
down_revision: Union[str, None] = '0002_evaluation_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evaluation_baselines table
    op.create_table(
        'evaluation_baselines',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('dataset_id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('agent_version_id', sa.String(length=36), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['evaluation_datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_version_id'], ['agent_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evaluation_baselines_id'), 'evaluation_baselines', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_baselines_dataset_id'), 'evaluation_baselines', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_evaluation_baselines_run_id'), 'evaluation_baselines', ['run_id'], unique=False)
    op.create_index(op.f('ix_evaluation_baselines_agent_version_id'), 'evaluation_baselines', ['agent_version_id'], unique=False)
    op.create_index(op.f('ix_evaluation_baselines_is_active'), 'evaluation_baselines', ['is_active'], unique=False)
    op.create_index('ix_evaluation_baselines_dataset_active', 'evaluation_baselines', ['dataset_id', 'is_active'], unique=False)

    # 2. Create evaluation_comparisons table
    op.create_table(
        'evaluation_comparisons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('dataset_id', sa.String(length=36), nullable=False),
        sa.Column('baseline_run_id', sa.String(length=36), nullable=False),
        sa.Column('candidate_run_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('is_compatible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('compatibility_notes', sa.Text(), nullable=True),
        sa.Column('pass_rate_delta', sa.Float(), nullable=True),
        sa.Column('passed_cases_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_cases_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errored_cases_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unscored_cases_delta', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms_delta', sa.Float(), nullable=True),
        sa.Column('p95_latency_ms_delta', sa.Float(), nullable=True),
        sa.Column('newly_failing_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('newly_fixed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('newly_errored_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('newly_unscored_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cases_baseline', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cases_candidate', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reasons_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('thresholds_json', sa.Text(), nullable=True),
        sa.Column('case_comparisons_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['evaluation_datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['baseline_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evaluation_comparisons_id'), 'evaluation_comparisons', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_comparisons_dataset_id'), 'evaluation_comparisons', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_evaluation_comparisons_baseline_run_id'), 'evaluation_comparisons', ['baseline_run_id'], unique=False)
    op.create_index(op.f('ix_evaluation_comparisons_candidate_run_id'), 'evaluation_comparisons', ['candidate_run_id'], unique=False)
    op.create_index(op.f('ix_evaluation_comparisons_status'), 'evaluation_comparisons', ['status'], unique=False)
    op.create_index('ix_evaluation_comparisons_baseline_candidate', 'evaluation_comparisons', ['baseline_run_id', 'candidate_run_id'], unique=False)
    op.create_index('ix_evaluation_comparisons_dataset_created', 'evaluation_comparisons', ['dataset_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_evaluation_comparisons_dataset_created', table_name='evaluation_comparisons')
    op.drop_index('ix_evaluation_comparisons_baseline_candidate', table_name='evaluation_comparisons')
    op.drop_index(op.f('ix_evaluation_comparisons_status'), table_name='evaluation_comparisons')
    op.drop_index(op.f('ix_evaluation_comparisons_candidate_run_id'), table_name='evaluation_comparisons')
    op.drop_index(op.f('ix_evaluation_comparisons_baseline_run_id'), table_name='evaluation_comparisons')
    op.drop_index(op.f('ix_evaluation_comparisons_dataset_id'), table_name='evaluation_comparisons')
    op.drop_index(op.f('ix_evaluation_comparisons_id'), table_name='evaluation_comparisons')
    op.drop_table('evaluation_comparisons')

    op.drop_index('ix_evaluation_baselines_dataset_active', table_name='evaluation_baselines')
    op.drop_index(op.f('ix_evaluation_baselines_is_active'), table_name='evaluation_baselines')
    op.drop_index(op.f('ix_evaluation_baselines_agent_version_id'), table_name='evaluation_baselines')
    op.drop_index(op.f('ix_evaluation_baselines_run_id'), table_name='evaluation_baselines')
    op.drop_index(op.f('ix_evaluation_baselines_dataset_id'), table_name='evaluation_baselines')
    op.drop_index(op.f('ix_evaluation_baselines_id'), table_name='evaluation_baselines')
    op.drop_table('evaluation_baselines')
