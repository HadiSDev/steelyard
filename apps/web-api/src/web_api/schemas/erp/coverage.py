"""How much of the spend the ERP posted has been categorized."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class SpendCoverageRow(BaseModel):
    """The listed vouchers' posted spend and their lines' categorization, in one base currency."""

    currency: str
    voucher_count: int = 0
    unconverted_vouchers: int = 0
    posted_spend: Decimal = Decimal("0")
    categorized_spend: Decimal = Decimal("0")
    line_count: int = 0
    categorized_lines: int = 0
    verified_lines: int = 0
    needs_review_lines: int = 0
    uncategorized_lines: int = 0
    failed_lines: int = 0
