"""Suppliers with the figures the Suppliers page lists them by."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class VendorSpendRead(BaseModel):
    """A supplier's net-of-VAT spend in one base currency."""

    currency: str | None = None
    amount: Decimal
    unconverted_count: int = 0


class VendorOverviewRead(BaseModel):
    """One supplier the organization buys from, with its invoice count and spend."""

    id: str
    name: str
    country_code: str | None = None
    vat_number: str | None = None
    description: str | None = None
    invoice_count: int
    last_invoice_date: date | None = None
    spend: list[VendorSpendRead] = []
