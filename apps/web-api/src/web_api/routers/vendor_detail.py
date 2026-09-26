"""A supplier's detail page: who it is, what the organization spent with it, and on what."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, nulls_last
from sqlmodel import Session, select

from web_api.db.models import Company, Invoice, InvoiceLine, SpendCategory, Vendor
from web_api.vendor_spend import spend_by_vendor
from ..auth.deps import TenantScope, get_session, resolve_company_ids, tenant_scope
from ..schemas import VendorCategorySpendRead, VendorDetailRead, VendorInvoiceRead

router = APIRouter(prefix="/api/v1", tags=["vendors"])

RECENT_INVOICE_LIMIT = 10


@router.get("/vendors/{vendor_id}/detail", response_model=VendorDetailRead)
def vendor_detail(
    vendor_id: str,
    company_id: str | None = Query(default=None),
    scope: TenantScope = Depends(tenant_scope),
    session: Session = Depends(get_session),
) -> VendorDetailRead:
    """The supplier with its figures over the caller's invoices; 404 when the caller has none from it."""
    company_ids = resolve_company_ids(scope, company_id)
    vendor = session.get(Vendor, vendor_id)
    if vendor is None or not company_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    invoice_count, first_date, last_date = session.exec(
        select(func.count(Invoice.id), func.min(Invoice.invoice_date), func.max(Invoice.invoice_date))
        .where(Invoice.vendor_id == vendor_id, Invoice.company_id.in_(company_ids))
    ).one()
    if not invoice_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    return VendorDetailRead(
        id=vendor.id,
        name=vendor.name,
        country_code=vendor.country_code,
        vat_number=vendor.vat_number,
        description=vendor.description,
        description_source=vendor.description_source,
        website=vendor.website,
        invoice_count=invoice_count,
        first_invoice_date=first_date,
        last_invoice_date=last_date,
        spend=spend_by_vendor(session, company_ids, [vendor_id]).get(vendor_id, []),
        categories=_category_spend(session, company_ids, vendor_id),
        recent_invoices=_recent_invoices(session, company_ids, vendor_id),
    )


def _category_spend(
    session: Session, company_ids: list[str], vendor_id: str
) -> list[VendorCategorySpendRead]:
    """The supplier's lines grouped by category and base currency, largest spend first."""
    amount = func.coalesce(func.sum(InvoiceLine.base_amount), 0)
    rows = session.exec(
        select(
            InvoiceLine.spend_category_id, SpendCategory.name, Company.base_currency,
            amount, func.count(InvoiceLine.id),
        )
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .join(Company, Company.id == Invoice.company_id)
        .outerjoin(SpendCategory, SpendCategory.id == InvoiceLine.spend_category_id)
        .where(Invoice.vendor_id == vendor_id, Invoice.company_id.in_(company_ids))
        .group_by(InvoiceLine.spend_category_id, SpendCategory.name, Company.base_currency)
        .order_by(amount.desc(), SpendCategory.name)
    ).all()
    return [
        VendorCategorySpendRead(
            category_id=category_id,
            category_name=category_name,
            currency=currency,
            amount=Decimal(str(total)),
            line_count=line_count,
        )
        for category_id, category_name, currency, total, line_count in rows
    ]


def _recent_invoices(
    session: Session, company_ids: list[str], vendor_id: str
) -> list[VendorInvoiceRead]:
    """The supplier's latest invoices to the caller's companies, newest first."""
    rows = session.exec(
        select(Invoice, Company.name)
        .join(Company, Company.id == Invoice.company_id)
        .where(Invoice.vendor_id == vendor_id, Invoice.company_id.in_(company_ids))
        .order_by(nulls_last(Invoice.invoice_date.desc()), Invoice.created_at.desc(), Invoice.id)
        .limit(RECENT_INVOICE_LIMIT)
    ).all()
    return [
        VendorInvoiceRead(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            company_name=company_name,
            currency=invoice.currency,
            total=invoice.total,
            status=invoice.status,
        )
        for invoice, company_name in rows
    ]
