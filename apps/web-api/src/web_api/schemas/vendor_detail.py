"""One supplier as its detail page shows it: who it is, what was spent with it, and on what."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from .vendor_overview import VendorSpendRead


class VendorCategorySpendRead(BaseModel):
    """What the supplier's lines were categorized as, with their net spend in one base currency."""

    category_id: str | None = None
    category_name: str | None = None
    currency: str | None = None
    amount: Decimal
    line_count: int


class VendorInvoiceRead(BaseModel):
    """One of the supplier's invoices, in its own currency.

    `invoice_number` is the ERP's, else the one printed on the document; `voucher_number` is the
    ERP voucher it was posted on.
    """

    id: str
    invoice_number: str | None = None
    voucher_number: str | None = None
    invoice_date: date | None = None
    company_name: str
    currency: str | None = None
    total: Decimal | None = None
    status: str


class VendorDetailRead(BaseModel):
    """A supplier the organization buys from, with its figures, its categories and its latest invoices."""

    id: str
    name: str
    country_code: str | None = None
    vat_number: str | None = None
    description: str | None = None
    description_source: str | None = None
    website: str | None = None
    invoice_count: int
    first_invoice_date: date | None = None
    last_invoice_date: date | None = None
    spend: list[VendorSpendRead] = []
    categories: list[VendorCategorySpendRead] = []
    recent_invoices: list[VendorInvoiceRead] = []
