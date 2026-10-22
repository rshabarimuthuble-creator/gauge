"""initial_schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-09 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evaluation_datasets table
    op.create_table(
        'evaluation_datasets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_datasets_id'), 'evaluation_datasets', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_datasets_name'), 'evaluation_datasets', ['name'], unique=False)

    # 2. Create agent_versions table
    op.create_table(
        'agent_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('model_provider', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_versions_id'), 'agent_versions', ['id'], unique=False)
    op.create_index(op.f('ix_agent_versions_name'), 'agent_versions', ['name'], unique=False)
    op.create_index(op.f('ix_agent_versions_version'), 'agent_versions', ['version'], unique=False)

    # 3. Create evaluation_runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('dataset_id', sa.String(length=36), nullable=False),
        sa.Column('agent_version_id', sa.String(length=36), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_version_id'], ['agent_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dataset_id'], ['evaluation_datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_runs_id'), 'evaluation_runs', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_status'), 'evaluation_runs', ['status'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_dataset_id'), 'evaluation_runs', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_agent_version_id'), 'evaluation_runs', ['agent_version_id'], unique=False)
    op.create_index('ix_evaluation_runs_dataset_agent', 'evaluation_runs', ['dataset_id', 'agent_version_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_evaluation_runs_dataset_agent', table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_agent_version_id'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_dataset_id'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_status'), table_name='evaluation_runs')
    op.drop_index(op.f('ix_evaluation_runs_id'), table_name='evaluation_runs')
    op.drop_table('evaluation_runs')

    op.drop_index(op.f('ix_agent_versions_version'), table_name='agent_versions')
    op.drop_index(op.f('ix_agent_versions_name'), table_name='agent_versions')
    op.drop_index(op.f('ix_agent_versions_id'), table_name='agent_versions')
    op.drop_table('agent_versions')

    op.drop_index(op.f('ix_evaluation_datasets_name'), table_name='evaluation_datasets')
    op.drop_index(op.f('ix_evaluation_datasets_id'), table_name='evaluation_datasets')
    op.drop_table('evaluation_datasets')
