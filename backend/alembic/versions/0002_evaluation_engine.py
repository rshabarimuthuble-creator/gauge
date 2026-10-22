"""evaluation_engine

Revision ID: 0002_evaluation_engine
Revises: 0001_initial_schema
Create Date: 2026-10-10 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_evaluation_engine'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evaluation_test_cases table
    op.create_table(
        'evaluation_test_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('dataset_id', sa.String(length=36), nullable=False),
        sa.Column('case_identifier', sa.String(length=128), nullable=False),
        sa.Column('input_prompt', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=True),
        sa.Column('criteria', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['evaluation_datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evaluation_test_cases_id'), 'evaluation_test_cases', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_test_cases_dataset_id'), 'evaluation_test_cases', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_evaluation_test_cases_case_identifier'), 'evaluation_test_cases', ['case_identifier'], unique=False)
    op.create_index('ix_evaluation_test_cases_dataset_case', 'evaluation_test_cases', ['dataset_id', 'case_identifier'], unique=False)

    # 2. Add aggregate metric columns to evaluation_runs table
    op.add_column('evaluation_runs', sa.Column('total_cases', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('passed_cases', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('failed_cases', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('errored_cases', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('unscored_cases', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('pass_rate', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('avg_latency_ms', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('min_latency_ms', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('max_latency_ms', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('p95_latency_ms', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('error_message', sa.Text(), nullable=True))

    # 3. Create evaluation_results table
    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('test_case_id', sa.String(length=36), nullable=True),
        sa.Column('case_identifier', sa.String(length=128), nullable=False),
        sa.Column('input_prompt', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=True),
        sa.Column('actual_output', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('token_usage', sa.Integer(), nullable=True),
        sa.Column('tokens_estimated', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('is_mock', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_case_id'], ['evaluation_test_cases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evaluation_results_id'), 'evaluation_results', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_results_run_id'), 'evaluation_results', ['run_id'], unique=False)
    op.create_index(op.f('ix_evaluation_results_test_case_id'), 'evaluation_results', ['test_case_id'], unique=False)
    op.create_index(op.f('ix_evaluation_results_case_identifier'), 'evaluation_results', ['case_identifier'], unique=False)
    op.create_index(op.f('ix_evaluation_results_status'), 'evaluation_results', ['status'], unique=False)
    op.create_index('ix_evaluation_results_run_status', 'evaluation_results', ['run_id', 'status'], unique=False)


def downgrade() -> None:
    # 1. Drop evaluation_results table
    op.drop_index('ix_evaluation_results_run_status', table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_status'), table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_case_identifier'), table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_test_case_id'), table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_run_id'), table_name='evaluation_results')
    op.drop_index(op.f('ix_evaluation_results_id'), table_name='evaluation_results')
    op.drop_table('evaluation_results')

    # 2. Drop aggregate columns from evaluation_runs table
    op.drop_column('evaluation_runs', 'error_message')
    op.drop_column('evaluation_runs', 'p95_latency_ms')
    op.drop_column('evaluation_runs', 'max_latency_ms')
    op.drop_column('evaluation_runs', 'min_latency_ms')
    op.drop_column('evaluation_runs', 'avg_latency_ms')
    op.drop_column('evaluation_runs', 'pass_rate')
    op.drop_column('evaluation_runs', 'unscored_cases')
    op.drop_column('evaluation_runs', 'errored_cases')
    op.drop_column('evaluation_runs', 'failed_cases')
    op.drop_column('evaluation_runs', 'passed_cases')
    op.drop_column('evaluation_runs', 'total_cases')

    # 3. Drop evaluation_test_cases table
    op.drop_index('ix_evaluation_test_cases_dataset_case', table_name='evaluation_test_cases')
    op.drop_index(op.f('ix_evaluation_test_cases_case_identifier'), table_name='evaluation_test_cases')
    op.drop_index(op.f('ix_evaluation_test_cases_dataset_id'), table_name='evaluation_test_cases')
    op.drop_index(op.f('ix_evaluation_test_cases_id'), table_name='evaluation_test_cases')
    op.drop_table('evaluation_test_cases')
