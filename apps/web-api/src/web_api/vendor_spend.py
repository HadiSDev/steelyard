"""What the organization spent with its suppliers, net of VAT, in each company's base currency."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func
from sqlmodel import Session, select

from web_api.db.models import Company, Invoice
from web_api.schemas import VendorSpendRead

NET_SPEND = Invoice.base_total - func.coalesce(Invoice.base_tax, 0)
TOTAL_NET_SPEND = func.coalesce(func.sum(NET_SPEND), 0)


def base_currencies(session: Session, company_ids: list[str]) -> set[str]:
    """The distinct base currencies of the given companies."""
    return set(session.exec(
        select(Company.base_currency).where(Company.id.in_(company_ids)).distinct()
    ).all())


def spend_by_vendor(
    session: Session, company_ids: list[str], vendor_ids: list[str]
) -> dict[str, list[VendorSpendRead]]:
    """`{vendor_id: [spend per base currency]}` over the given companies' invoices."""
    if not vendor_ids:
        return {}
    unconverted = func.sum(case((Invoice.base_total.is_(None), 1), else_=0))
    rows = session.exec(
        select(Invoice.vendor_id, Company.base_currency, TOTAL_NET_SPEND, unconverted)
        .join(Company, Company.id == Invoice.company_id)
        .where(Invoice.company_id.in_(company_ids), Invoice.vendor_id.in_(vendor_ids))
        .group_by(Invoice.vendor_id, Company.base_currency)
        .order_by(Company.base_currency)
    ).all()
    by_vendor: dict[str, list[VendorSpendRead]] = {}
    for vendor_id, currency, amount, unconverted_count in rows:
        by_vendor.setdefault(vendor_id, []).append(VendorSpendRead(
            currency=currency,
            amount=Decimal(str(amount)),
            unconverted_count=int(unconverted_count or 0),
        ))
    return by_vendor
