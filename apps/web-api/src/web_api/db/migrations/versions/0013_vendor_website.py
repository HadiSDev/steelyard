"""A supplier carries the website its description was researched from

Revision ID: 0013_vendor_website
Revises: 0012_pipeline_runs
Create Date: 2026-09-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0013_vendor_website'
down_revision = '0012_pipeline_runs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('vendors', sa.Column('website', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('vendors', 'website')
