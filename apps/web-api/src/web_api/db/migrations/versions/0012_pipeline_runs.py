"""Pipeline runs record requested and automatic stage runs per company

Revision ID: 0012_pipeline_runs
Revises: 0011_entry_voucher_number
Create Date: 2026-09-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0012_pipeline_runs'
down_revision = '0011_entry_voucher_number'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('company_id', sa.String(), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('requested_by', sa.String(), nullable=False),
        sa.Column(
            'requested_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
    )
    op.create_index(
        'ix_pipeline_runs_company_requested', 'pipeline_runs', ['company_id', 'requested_at']
    )
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_pipeline_runs_status', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_company_requested', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')
