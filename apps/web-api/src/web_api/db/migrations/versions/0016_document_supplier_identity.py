"""An invoice keeps the supplier country and VAT number its document prints

Revision ID: 0016_document_supplier_identity
Revises: 0015_document_supplier_website
Create Date: 2026-09-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0016_document_supplier_identity'
down_revision = '0015_document_supplier_website'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('invoices', sa.Column('document_supplier_country_code', sa.String(length=2), nullable=True))
    op.add_column('invoices', sa.Column('document_supplier_vat_number', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('invoices', 'document_supplier_vat_number')
    op.drop_column('invoices', 'document_supplier_country_code')
