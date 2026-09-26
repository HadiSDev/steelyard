"""Categorizing the uncategorized lines of one ERP integration's invoices."""
from __future__ import annotations

import logging
from collections.abc import Iterable
from decimal import Decimal

from sqlmodel import Session, select

from web_api.audit import LINE_AUDIT_FIELDS, diff_changes, record_audit
from web_api.db.models import (
    Company,
    ErpAccount,
    ErpEntry,
    Invoice,
    InvoiceLine,
    LineStatus,
    Vendor,
)
from web_api.db.models.audit_log import SYSTEM_ACTOR
from web_api.rollup import recompute_invoice_status

from .. import config as ai_config
from ..persistence import LineGroundTruth
from ..sync.cache import question_key
from ..sync.categorizer import Category, CategoryMatch, build_candidates_from_retrieval
from ..sync.llm_categorizer import CategorizerUnavailable, LineContext, categorize_line
from .cached import cached_answer, hash_for, match_from_cache, remember_answer
from .tree import retriever_for

logger = logging.getLogger("ai_api.categorization")


def empty_stats() -> dict:
    """The counters every categorization reports, all at zero."""
    return {"categorized": 0, "failed": 0, "invoices_completed": 0, "invoices_failed": 0}


def _integration_invoices(
    session: Session, integration_id: str, invoice_ids: Iterable[str] | None
) -> list[Invoice]:
    """The invoices this integration's postings point at, optionally narrowed."""
    statement = (
        select(ErpEntry.source_invoice_id)
        .join(ErpAccount, ErpEntry.erp_account_id == ErpAccount.id)
        .where(
            ErpAccount.erp_integration_id == integration_id,
            ErpEntry.source_invoice_id.is_not(None),  # type: ignore[union-attr]
        )
    )
    if invoice_ids is not None:
        statement = statement.where(ErpEntry.source_invoice_id.in_(list(invoice_ids)))  # type: ignore[union-attr]
    found = list(session.exec(statement.distinct()).all())
    if not found:
        return []
    return list(session.exec(select(Invoice).where(Invoice.id.in_(found))).all())  # type: ignore[union-attr]


def _account_names(session: Session, integration_id: str) -> dict[str, str | None]:
    return {
        code: name for code, name in session.exec(
            select(ErpAccount.erp_account_code, ErpAccount.erp_account_name)
            .where(ErpAccount.erp_integration_id == integration_id)
        ).all()
    }


class _VendorFacts:
    """Each invoice vendor's name and description, looked up once."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._known: dict[str, tuple[str, str | None]] = {}

    def of(self, vendor_id: str | None) -> tuple[str, str | None]:
        if not vendor_id:
            return ("", None)
        if vendor_id not in self._known:
            vendor = self._session.get(Vendor, vendor_id)
            self._known[vendor_id] = (vendor.name, vendor.description) if vendor else ("", None)
        return self._known[vendor_id]


def _record_ground_truth(session: Session, line: InvoiceLine, match: CategoryMatch) -> None:
    truth = session.exec(
        select(LineGroundTruth).where(LineGroundTruth.invoice_line_id == line.id)
    ).first()
    if truth is None:
        truth = LineGroundTruth(invoice_line_id=line.id)
        session.add(truth)
    truth.gt_level_1 = match.gt_level_1
    truth.gt_level_2 = match.gt_level_2
    truth.gt_level_3 = match.gt_level_3
    truth.gt_account_code = match.gt_account_code


def _apply_match(line: InvoiceLine, match: CategoryMatch) -> None:
    """Write the categorizer's answer, or its failure, onto the line."""
    if not match.matched:
        line.rationale = match.rationale
        line.status = LineStatus.AI_FAILED
        line.error_message = match.rationale
        return
    line.level_1 = match.level_1
    line.level_2 = match.level_2
    line.level_3 = match.level_3
    line.level_4 = match.level_4
    line.account_code = match.account_code
    line.account_name = match.account_name
    line.confidence = Decimal(str(match.confidence))
    line.rationale = match.rationale
    line.spend_category_id = match.spend_category_id
    line.status = LineStatus.AI_CATEGORIZED
    line.error_message = None


def _count(stats: dict, key: str) -> None:
    stats[key] = stats.get(key, 0) + 1


def _log_narrowing(tree_size: int, narrowed_total: int, lines_seen: int) -> None:
    if not lines_seen:
        return
    average = narrowed_total / lines_seen
    logger.info(
        "    candidates: tree=%d avg_offered=%.1f avg_reduction=%.0f%% lines=%d",
        tree_size,
        tree_size - average,
        100.0 * average / tree_size if tree_size else 0.0,
        lines_seen,
    )


def categorize_lines(
    session: Session,
    integration_id: str,
    company_id: str,
    candidates: list[Category],
    invoice_ids: Iterable[str] | None = None,
) -> dict:
    """Categorize every uncategorized line of the integration's invoices."""
    invoices = _integration_invoices(session, integration_id, invoice_ids)
    account_names = _account_names(session, integration_id)
    vendors = _VendorFacts(session)
    company = session.get(Company, company_id)
    buyer_name = company.name if company else None
    retrieve = retriever_for(company)
    narrowed_total = 0
    lines_seen = 0

    stats = empty_stats()
    for inv in invoices:
        lines = session.exec(select(InvoiceLine).where(InvoiceLine.invoice_id == inv.id)).all()
        pending = [ln for ln in lines if ln.status == LineStatus.UNCATEGORIZED]
        if not pending:
            continue

        any_failed = False
        for ln in pending:
            vendor_name, vendor_description = vendors.of(inv.vendor_id)
            offered = build_candidates_from_retrieval(
                " ".join(part for part in (ln.item_name, ln.description) if part),
                candidates,
                retrieve,
                top_k=ai_config.CATEGORY_RETRIEVAL_TOP_K,
            )
            narrowed_total += len(candidates) - len(offered)
            lines_seen += 1

            supplier_name = vendor_name or inv.supplier_name
            key = question_key(
                ln.item_name, ln.description, supplier_name, ln.native_account_code,
                vendor_description,
            )
            offered_hash = hash_for(tuple(offered))
            cached = cached_answer(session, key, offered_hash)
            context = LineContext(
                item_name=ln.item_name,
                description=ln.description,
                native_account_code=ln.native_account_code,
                native_account_name=account_names.get(ln.native_account_code or ""),
                supplier=supplier_name,
                supplier_description=vendor_description,
                buyer=buyer_name,
                amount=ln.amount,
                currency=inv.currency,
            )
            try:
                if cached is not None:
                    match = match_from_cache(cached, offered)
                else:
                    match = categorize_line(context, offered)
            except CategorizerUnavailable as exc:
                logger.warning("    categorizer unavailable, stopping: %s", exc)
                stats["unavailable"] = str(exc)
                session.commit()
                return stats

            before = {f: getattr(ln, f) for f in LINE_AUDIT_FIELDS}
            _record_ground_truth(session, ln, match)
            _apply_match(ln, match)
            if match.matched:
                stats["categorized"] += 1
                if cached is None:
                    _count(stats, "cache_misses")
                    remember_answer(
                        session, key, offered_hash, match,
                        item_name=ln.item_name, supplier_name=supplier_name,
                        native_account_code=ln.native_account_code,
                    )
                else:
                    _count(stats, "cache_hits")
            else:
                any_failed = True
                stats["failed"] += 1
            session.add(ln)

            after = {f: getattr(ln, f) for f in LINE_AUDIT_FIELDS}
            record_audit(
                session,
                entity_type="invoice_line",
                entity_id=ln.id,
                action="ai_categorize",
                actor=SYSTEM_ACTOR,
                changes=diff_changes(before, after, LINE_AUDIT_FIELDS),
            )

        recompute_invoice_status(session, inv.id)
        if any_failed:
            stats["invoices_failed"] += 1
        else:
            stats["invoices_completed"] += 1

    _log_narrowing(len(candidates), narrowed_total, lines_seen)
    session.commit()
    return stats
