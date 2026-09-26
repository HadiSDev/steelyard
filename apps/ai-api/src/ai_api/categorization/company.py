"""Categorizing a company's uncategorized lines, per integration or across all of them."""
from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlmodel import Session

from ..sync.integrations import connected_integrations
from .lines import categorize_lines, empty_stats
from .tree import index_tree, tree_candidates

logger = logging.getLogger("ai_api.categorization")

NO_TREE = "no spend tree assigned to this company; lines were left uncategorized"
NO_INTEGRATION = "no connected ERP integration for this company; lines were left uncategorized"


def _skipped(reason: str) -> dict:
    stats = empty_stats()
    stats["skipped"] = reason
    return stats


def categorize_integration(
    session: Session,
    integration_id: str,
    company_id: str,
    invoice_ids: Iterable[str] | None = None,
) -> dict:
    """Categorize the integration's uncategorized lines against the company's tree."""
    candidates = tree_candidates(session, company_id)
    index_tree(session, company_id)
    if candidates is None:
        logger.warning("    skipped: %s", NO_TREE)
        return _skipped(NO_TREE)

    stats = categorize_lines(session, integration_id, company_id, candidates, invoice_ids)
    logger.info(
        "    categorized=%d failed=%d (invoices: %d completed, %d failed)",
        stats["categorized"], stats["failed"],
        stats["invoices_completed"], stats["invoices_failed"],
    )
    return stats


def _add_into(total: dict, stats: dict) -> None:
    """Sum the counters and keep the first reason seen for any text entry."""
    for key, value in stats.items():
        if isinstance(value, int):
            total[key] = total.get(key, 0) + value
        else:
            total.setdefault(key, value)


def categorize_company(
    session: Session, company_id: str, invoice_ids: Iterable[str] | None = None
) -> dict:
    """Categorize the company's uncategorized lines across its connected integrations."""
    integrations = connected_integrations(session, company_id=company_id)
    if not integrations:
        logger.warning("    skipped: %s", NO_INTEGRATION)
        return _skipped(NO_INTEGRATION)

    wanted = list(invoice_ids) if invoice_ids is not None else None
    total = empty_stats()
    for integration in integrations:
        stats = categorize_integration(session, integration.id, company_id, wanted)
        _add_into(total, stats)
        if "unavailable" in stats or "skipped" in stats:
            break
    return total
