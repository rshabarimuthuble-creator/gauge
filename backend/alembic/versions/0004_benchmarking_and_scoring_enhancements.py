"""benchmarking_and_scoring_enhancements

Revision ID: 0004_benchmarking_enhancements
Revises: 0003_baselines_and_comparisons
Create Date: 2026-10-16 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0004_benchmarking_enhancements'
down_revision: Union[str, None] = '0003_baselines_and_comparisons'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. evaluation_datasets
    op.add_column('evaluation_datasets', sa.Column('version', sa.String(length=32), nullable=False, server_default='v1.0.0'))

    # 2. evaluation_test_cases
    op.add_column('evaluation_test_cases', sa.Column('category', sa.String(length=64), nullable=True))
    op.add_column('evaluation_test_cases', sa.Column('difficulty', sa.String(length=32), nullable=True))
    op.add_column('evaluation_test_cases', sa.Column('scoring_method', sa.String(length=64), nullable=True, server_default='exact_match'))

    # 3. evaluation_runs
    op.add_column('evaluation_runs', sa.Column('dataset_version', sa.String(length=32), nullable=True))
    op.add_column('evaluation_runs', sa.Column('dataset_snapshot_json', sa.Text(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('scoring_config', sa.Text(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('model_provider', sa.String(length=64), nullable=True))
    op.add_column('evaluation_runs', sa.Column('model_name', sa.String(length=128), nullable=True))
    op.add_column('evaluation_runs', sa.Column('accuracy', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('error_rate', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('dataset_coverage', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('total_cost_usd', sa.Float(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('total_tokens', sa.Integer(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('prompt_tokens', sa.Integer(), nullable=True))
    op.add_column('evaluation_runs', sa.Column('completion_tokens', sa.Integer(), nullable=True))

    # 4. evaluation_results
    op.add_column('evaluation_results', sa.Column('score', sa.Float(), nullable=True))
    op.add_column('evaluation_results', sa.Column('scoring_method', sa.String(length=64), nullable=True, server_default='exact_match'))
    op.add_column('evaluation_results', sa.Column('cost_usd', sa.Float(), nullable=True))
    op.add_column('evaluation_results', sa.Column('prompt_tokens', sa.Integer(), nullable=True))
    op.add_column('evaluation_results', sa.Column('completion_tokens', sa.Integer(), nullable=True))
    op.add_column('evaluation_results', sa.Column('model_provider', sa.String(length=64), nullable=True))
    op.add_column('evaluation_results', sa.Column('model_name', sa.String(length=128), nullable=True))

    # 5. evaluation_comparisons
    op.add_column('evaluation_comparisons', sa.Column('accuracy_delta', sa.Float(), nullable=True))
    op.add_column('evaluation_comparisons', sa.Column('cost_usd_delta', sa.Float(), nullable=True))
    op.add_column('evaluation_comparisons', sa.Column('tokens_delta', sa.Integer(), nullable=True))


def downgrade() -> None:
    # 5. evaluation_comparisons
    op.drop_column('evaluation_comparisons', 'tokens_delta')
    op.drop_column('evaluation_comparisons', 'cost_usd_delta')
    op.drop_column('evaluation_comparisons', 'accuracy_delta')

    # 4. evaluation_results
    op.drop_column('evaluation_results', 'model_name')
    op.drop_column('evaluation_results', 'model_provider')
    op.drop_column('evaluation_results', 'completion_tokens')
    op.drop_column('evaluation_results', 'prompt_tokens')
    op.drop_column('evaluation_results', 'cost_usd')
    op.drop_column('evaluation_results', 'scoring_method')
    op.drop_column('evaluation_results', 'score')

    # 3. evaluation_runs
    op.drop_column('evaluation_runs', 'completion_tokens')
    op.drop_column('evaluation_runs', 'prompt_tokens')
    op.drop_column('evaluation_runs', 'total_tokens')
    op.drop_column('evaluation_runs', 'total_cost_usd')
    op.drop_column('evaluation_runs', 'dataset_coverage')
    op.drop_column('evaluation_runs', 'error_rate')
    op.drop_column('evaluation_runs', 'accuracy')
    op.drop_column('evaluation_runs', 'model_name')
    op.drop_column('evaluation_runs', 'model_provider')
    op.drop_column('evaluation_runs', 'scoring_config')
    op.drop_column('evaluation_runs', 'dataset_snapshot_json')
    op.drop_column('evaluation_runs', 'dataset_version')

    # 2. evaluation_test_cases
    op.drop_column('evaluation_test_cases', 'scoring_method')
    op.drop_column('evaluation_test_cases', 'difficulty')
    op.drop_column('evaluation_test_cases', 'category')

    # 1. evaluation_datasets
    op.drop_column('evaluation_datasets', 'version')
