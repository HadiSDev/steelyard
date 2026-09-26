"""A supplier's website: the one set on it, else the one its invoices print most often."""
from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from web_api.db.models import Invoice, Vendor


def known_website(session: Session, vendor: Vendor) -> str | None:
    """The supplier's website as set on it, else the one its invoices' documents print most often."""
    if vendor.website:
        return vendor.website
    return session.exec(
        select(Invoice.document_supplier_website)
        .where(Invoice.vendor_id == vendor.id, Invoice.document_supplier_website.is_not(None))
        .group_by(Invoice.document_supplier_website)
        .order_by(func.count().desc(), Invoice.document_supplier_website)
        .limit(1)
    ).first()
