"""Finding the website of a supplier that is already described, leaving its description as it is."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from sqlmodel import Session, select

from web_api.db.models import Invoice, Vendor
from web_api.vendor_website import known_website

from .. import config
from .supplier_profile import locate_website

logger = logging.getLogger("ai_api.enrichment")


@dataclass(frozen=True)
class WebsiteResult:
    considered: int
    found: int
    not_found: int
    skipped: int

    @property
    def as_dict(self) -> dict[str, int]:
        return {
            "considered": self.considered,
            "found": self.found,
            "not_found": self.not_found,
            "skipped": self.skipped,
        }


def vendors_needing_website(
    session: Session, *, company_id: str | None = None, limit: int | None = None
) -> list[Vendor]:
    """Described vendors with no website yet, ordered by name."""
    statement = select(Vendor).where(
        Vendor.website.is_(None),  # type: ignore[union-attr]
        Vendor.description.is_not(None),  # type: ignore[union-attr]
        Vendor.description != "",
    )
    if company_id is not None:
        referenced = select(Invoice.vendor_id).where(
            Invoice.company_id == company_id,
            Invoice.vendor_id.is_not(None),  # type: ignore[union-attr]
        )
        statement = statement.where(Vendor.id.in_(referenced))  # type: ignore[union-attr]
    statement = statement.order_by(Vendor.name)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.exec(statement).all())


def find_vendor_websites(
    session: Session,
    *,
    company_id: str | None = None,
    limit: int | None = None,
    enabled: bool | None = None,
    locate: Callable[[str, str | None, str | None], str | None] | None = None,
) -> WebsiteResult:
    """Store a website for every described vendor that has none, never touching its description."""
    if enabled is None:
        enabled = config.VENDOR_ENRICHMENT_ENABLED
    if not enabled:
        logger.info("vendor enrichment is disabled; nothing was requested")
        return WebsiteResult(0, 0, 0, 0)
    if locate is None:
        locate = locate_website

    pending = vendors_needing_website(session, company_id=company_id, limit=limit)
    found = not_found = skipped = 0

    for vendor in pending:
        try:
            website = locate(vendor.name, vendor.country_code, known_website(session, vendor))
        except Exception as exc:  # noqa: BLE001
            logger.warning("could not find a website for %s: %s", vendor.name, exc)
            not_found += 1
            continue

        if not website:
            not_found += 1
            continue

        session.refresh(vendor)
        if vendor.website:
            skipped += 1
            continue

        vendor.website = website
        session.add(vendor)
        found += 1
        logger.info("found %s for %s", website, vendor.name)

    session.commit()
    return WebsiteResult(
        considered=len(pending), found=found, not_found=not_found, skipped=skipped,
    )
