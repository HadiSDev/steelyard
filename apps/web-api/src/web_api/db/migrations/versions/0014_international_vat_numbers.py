"""A supplier's VAT number is stated internationally, with its country's prefix

Revision ID: 0014_international_vat_numbers
Revises: 0013_vendor_website
Create Date: 2026-09-26

"""
from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa

revision = '0014_international_vat_numbers'
down_revision = '0013_vendor_website'
branch_labels = None
depends_on = None

_VAT_PREFIXES = {"GR": "EL"}
_SEPARATORS = re.compile(r"[\s.\-]")


def _international(vat_number: str | None, country_code: str | None) -> str | None:
    compact = _SEPARATORS.sub("", vat_number or "").upper()
    if not compact:
        return None
    if compact[:2].isalpha() or not country_code:
        return compact
    country = country_code.strip().upper()
    return f"{_VAT_PREFIXES.get(country, country)}{compact}"


def _restate(conn, table: str, vat_column: str, country_column: str) -> None:
    rows = conn.execute(sa.text(
        f"SELECT id, {vat_column} AS vat, {country_column} AS country "
        f"FROM {table} WHERE {vat_column} IS NOT NULL"
    )).fetchall()
    for row in rows:
        stated = _international(row.vat, row.country)
        if stated != row.vat:
            conn.execute(
                sa.text(f"UPDATE {table} SET {vat_column} = :vat WHERE id = :id"),
                {"vat": stated, "id": row.id},
            )


def upgrade() -> None:
    conn = op.get_bind()
    _restate(conn, "vendors", "vat_number", "country_code")
    _restate(conn, "invoices", "supplier_vat_number", "supplier_country_code")


def downgrade() -> None:
    """The prefixed numbers are the same numbers stated in full, so there is nothing to undo."""
