"""A supplier's website: the one set on it, else the one its invoices print most often that names it."""
from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from web_api.db.models import Invoice, Vendor
from web_api.website import website_names_supplier


def known_website(session: Session, vendor: Vendor) -> str | None:
    """The supplier's website as set on it, else the most printed one on its invoices whose domain names it.

    A document can print other organizations' addresses, such as a deposit guarantee scheme in a
    bank's footer, so a printed website counts only when its domain carries the supplier's name.
    """
    if vendor.website:
        return vendor.website
    printed = session.exec(
        select(Invoice.document_supplier_website)
        .where(Invoice.vendor_id == vendor.id, Invoice.document_supplier_website.is_not(None))
        .group_by(Invoice.document_supplier_website)
        .order_by(func.count().desc(), Invoice.document_supplier_website)
    ).all()
    return next((site for site in printed if website_names_supplier(site, vendor.name)), None)
