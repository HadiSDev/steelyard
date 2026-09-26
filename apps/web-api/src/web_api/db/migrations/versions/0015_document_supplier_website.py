"""An invoice keeps the website its document prints for the supplier

Revision ID: 0015_document_supplier_website
Revises: 0014_international_vat_numbers
Create Date: 2026-09-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0015_document_supplier_website'
down_revision = '0014_international_vat_numbers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('invoices', sa.Column('document_supplier_website', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('invoices', 'document_supplier_website')
