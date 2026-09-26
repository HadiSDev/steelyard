"""The Suppliers page's overview: the org's suppliers with their invoice count and spend."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, nulls_last, or_
from sqlmodel import Session, select

from web_api.db.models import Company, Invoice, Vendor
from ..auth.deps import TenantScope, get_session, resolve_company_ids, tenant_scope
from ..schemas import Page, VendorOverviewRead, VendorSpendRead

router = APIRouter(prefix="/api/v1", tags=["vendors"])

SupplierSort = Literal["name", "spend", "invoice_count", "last_invoice_date"]
SortOrder = Literal["asc", "desc"]

_NET = Invoice.base_total - func.coalesce(Invoice.base_tax, 0)
_INVOICE_COUNT = func.count(Invoice.id)
_LAST_INVOICE_DATE = func.max(Invoice.invoice_date)
_SPEND = func.coalesce(func.sum(_NET), 0)

_SORT_COLUMNS = {
    "name": Vendor.name,
    "spend": _SPEND,
    "invoice_count": _INVOICE_COUNT,
    "last_invoice_date": _LAST_INVOICE_DATE,
}


@router.get("/vendors/overview", response_model=Page[VendorOverviewRead])
def vendor_overview(
    q: str | None = Query(default=None, description="Substring match on name or VAT number"),
    company_id: str | None = Query(default=None),
    sort: SupplierSort | None = Query(default=None),
    order: SortOrder | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    scope: TenantScope = Depends(tenant_scope),
    session: Session = Depends(get_session),
) -> Page[VendorOverviewRead]:
    """The suppliers the caller's invoices name, each with its figures from those invoices."""
    company_ids = resolve_company_ids(scope, company_id)
    if not company_ids:
        return Page(items=[], page=page, page_size=page_size, total=0)

    shares_currency = len(_base_currencies(session, company_ids)) == 1
    if sort is None:
        sort = "spend" if shares_currency else "name"
    elif sort == "spend" and not shares_currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Spend cannot be sorted across companies with different base currencies.",
        )
    if order is None:
        order = "asc" if sort == "name" else "desc"

    conditions = [Invoice.company_id.in_(company_ids)]
    if q:
        like = f"%{q}%"
        conditions.append(or_(Vendor.name.ilike(like), Vendor.vat_number.ilike(like)))

    grouped = (
        select(Vendor, _INVOICE_COUNT, _LAST_INVOICE_DATE)
        .join(Invoice, Invoice.vendor_id == Vendor.id)
        .where(*conditions)
        .group_by(Vendor.id)
    )
    total = session.exec(select(func.count()).select_from(grouped.subquery())).one()

    column = _SORT_COLUMNS[sort]
    direction = column.asc() if order == "asc" else column.desc()
    rows = session.exec(
        grouped
        .order_by(nulls_last(direction), Vendor.name, Vendor.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    spend = _spend_by_vendor(session, company_ids, [vendor.id for vendor, _, _ in rows])
    items = [
        VendorOverviewRead(
            id=vendor.id,
            name=vendor.name,
            country_code=vendor.country_code,
            vat_number=vendor.vat_number,
            description=vendor.description,
            invoice_count=invoice_count,
            last_invoice_date=last_invoice_date,
            spend=spend.get(vendor.id, []),
        )
        for vendor, invoice_count, last_invoice_date in rows
    ]
    return Page(items=items, page=page, page_size=page_size, total=total)


def _base_currencies(session: Session, company_ids: list[str]) -> set[str]:
    """The distinct base currencies of the given companies."""
    return set(session.exec(
        select(Company.base_currency).where(Company.id.in_(company_ids)).distinct()
    ).all())


def _spend_by_vendor(
    session: Session, company_ids: list[str], vendor_ids: list[str]
) -> dict[str, list[VendorSpendRead]]:
    """`{vendor_id: [spend per base currency]}` over the caller's invoices, net of VAT."""
    if not vendor_ids:
        return {}
    unconverted = func.sum(case((Invoice.base_total.is_(None), 1), else_=0))
    rows = session.exec(
        select(Invoice.vendor_id, Company.base_currency, _SPEND, unconverted)
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
