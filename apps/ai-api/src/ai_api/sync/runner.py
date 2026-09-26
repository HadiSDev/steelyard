"""Sync runner — Steelyard's batch pipeline."""
from __future__ import annotations

import argparse
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlmodel import Session, SQLModel, select

from web_api.audit import (
    LINE_AUDIT_FIELDS,
    LINE_VALUE_AUDIT_FIELDS,
    diff_changes,
    record_audit,
)
from web_api.connectors import get_connector
from web_api.connectors.base import (
    ErpAccountData,
    ErpConnector,
    ErpEntryData,
    ErpInvoiceData,
    ErpVendorData,
)
from web_api.db.models import (
    Company,
    DocStatus,
    ErpAccount,
    ErpEntry,
    ErpIntegration,
    File,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    LineOrigin,
    LineStatus,
    SyncState,
    Vendor,
)
from web_api.db.models.audit_log import SYSTEM_ACTOR
from web_api.db.models.enums import EXPENSE_ACCOUNT_TYPE
from web_api.db.session import engine
from web_api.fx import CONVERTED, UNCHANGED, UNCONVERTED, FxService
from web_api.integrations import connector_config as _connector_config
from web_api.rollup import recompute_invoice_status
from web_api.vat import international_vat
from web_api.verified import clear_verified, is_verified

from ..aggregation import engine as aggregation
from ..categorization.company import categorize_integration
from ..procurement_agent import recommender
from ..redundancy import detector as redundancy
from .integrations import connected_integrations

logger = logging.getLogger("ai_api.sync")

_NS = uuid.UUID("5f4d6c3b-2a1e-4f8d-9c7b-0a1b2c3d4e5f")

_ZERO = Decimal("0")

WITHDRAWN_ACTION = "withdrawn_by_erp"

VOIDED_ACTION = "voucher_voided_in_erp"

_VOIDED_ENTRY_FIELDS = (
    "voucher_id", "entry_type", "accounting_date", "description",
    "debit_amount", "credit_amount", "currency", "erp_entry_id",
    "source_invoice_id", "source_invoice_line_id",
)

_WITHDRAWN_FIELDS = (
    *LINE_VALUE_AUDIT_FIELDS,
    "native_account_code", "origin", "sequence", "verified_fields",
    *LINE_AUDIT_FIELDS,
)

_HUMAN_DESCRIPTION = "human"
_ERP_DESCRIPTION = "erp"


def _det_id(*parts: str) -> str:
    return str(uuid.uuid5(_NS, ":".join(parts)))


def _dec(value) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def _fx_counts() -> dict[str, int]:
    return {CONVERTED: 0, UNCONVERTED: 0, UNCHANGED: 0}


def _safe_convert(counts: dict[str, int], convert) -> None:
    """Convert one row, absorbing any failure into an unconverted count."""
    try:
        counts[convert()] += 1
    except Exception as exc:
        logger.warning("    FX: conversion failed, storing unconverted: %s", exc)
        counts[UNCONVERTED] += 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_since(state: SyncState, override: date | None) -> date | None:
    """Where this integration's fetch starts."""
    if override is not None:
        return override
    return state.last_invoice_date


def _persist_accounts(
    session: Session, integration_id: str, accounts: list[ErpAccountData]
) -> dict[str, str]:
    """Upsert ERP accounts."""
    mapping: dict[str, str] = {}
    existing = {
        row.erp_account_code: row
        for row in session.exec(
            select(ErpAccount).where(ErpAccount.erp_integration_id == integration_id)
        ).all()
    }
    for acc in accounts:
        row = existing.get(acc.erp_account_code)
        if row is None:
            row = ErpAccount(erp_integration_id=integration_id,
                             erp_account_code=acc.erp_account_code,
                             with_vat=acc.with_vat)
            session.add(row)
            existing[acc.erp_account_code] = row
        row.erp_account_name = acc.erp_account_name
        row.erp_account_type = acc.erp_account_type
        row.parent_code = acc.parent_code
        row.is_active = acc.is_active
        row.raw_json = acc.raw
        mapping[acc.erp_account_code] = row.id
    session.commit()
    return mapping


def _enabled_account_codes(session: Session, integration_id: str) -> set[str]:
    """Return the native codes of accounts selected for sync (``sync_enabled``)."""
    rows = session.exec(
        select(ErpAccount).where(
            ErpAccount.erp_integration_id == integration_id,
            ErpAccount.sync_enabled == True,  # noqa: E712
        )
    ).all()
    return {r.erp_account_code for r in rows}


def _vendor_key(v: ErpVendorData) -> str:
    """Global supplier identity: VAT number as the ERP states it when present, else the normalized name.

    The key keeps the ERP's own spelling so that suppliers already stored keep their ids.
    """
    vat = (v.vat_number or "").strip().lower()
    if vat:
        return f"vat:{vat}"
    return "name:" + " ".join((v.name or "").split()).lower()


def _persist_vendors(
    session: Session, vendors: list[ErpVendorData]
) -> dict[str, str]:
    """Upsert vendors into the global supplier catalog."""
    mapping: dict[str, str] = {}
    for v in vendors:
        vendor_id = _det_id("vendor", _vendor_key(v))
        row = session.get(Vendor, vendor_id)
        if row is None:
            row = Vendor(id=vendor_id, name=v.name)
            session.add(row)
        row.name = v.name
        row.country_code = v.country_code
        row.vat_number = international_vat(v.vat_number, v.country_code)
        if v.description and row.description_source != _HUMAN_DESCRIPTION:
            row.description = v.description
            row.description_source = _ERP_DESCRIPTION
        mapping[v.erp_id] = vendor_id
    session.commit()
    return mapping


def _persist_file(
    session: Session, company_id: str, invoice_id: str, inv: ErpInvoiceData
) -> Optional[str]:
    """Upsert the scanned-document File for an invoice."""
    if not inv.file_name and not inv.file_ref:
        return None
    file_id = _det_id("file", invoice_id, inv.file_ref or inv.file_name or "")
    row = session.get(File, file_id)
    if row is None:
        row = File(id=file_id, company_id=company_id, filename=inv.file_name or "scan.pdf",
                   file_type="invoice_pdf", storage_path=inv.file_ref or "")
        session.add(row)
    row.filename = inv.file_name or "scan.pdf"
    row.storage_path = inv.file_ref or ""
    row.status = "processed"
    return file_id


def _has_human_lines(session: Session, invoice_id: str) -> bool:
    """Has anyone verified or hand-written a line on this invoice?"""
    return session.exec(
        select(InvoiceLine.id)
        .where(
            InvoiceLine.invoice_id == invoice_id,
            or_(
                InvoiceLine.status == LineStatus.VERIFIED,
                InvoiceLine.origin == LineOrigin.HUMAN,
            ),
        )
        .limit(1)
    ).first() is not None


def _queue_document(
    session: Session, row: Invoice, previous_file_id: Optional[str]
) -> bool:
    """Set ``doc_status`` for an invoice the sync is writing."""
    if row.file_id is None:
        row.doc_status = DocStatus.NOT_APPLICABLE
        return False
    if row.doc_status == DocStatus.PROCESSING:
        return False
    if row.doc_status == DocStatus.PROCESSED and row.file_id == previous_file_id:
        return False
    if row.doc_status == DocStatus.FAILED:
        return False
    if _has_human_lines(session, row.id):
        return False
    row.doc_status = DocStatus.PENDING
    return True


def _assigner(session: Session, row, hard_reset: bool):
    """A setter for one row that respects what a human has settled."""
    entity_type = "invoice" if isinstance(row, Invoice) else "invoice_line"

    def assign(field: str, value) -> None:
        if not is_verified(row, field):
            setattr(row, field, value)
            return
        if not hard_reset:
            return
        previous = getattr(row, field)
        setattr(row, field, value)
        clear_verified(row, [field])
        changes = diff_changes({field: previous}, {field: value}, (field,))
        if changes:
            record_audit(
                session, entity_type=entity_type, entity_id=row.id,
                action="hard_reset", changes=changes,
            )

    return assign


def _persist_invoices(
    session: Session,
    company_id: str,
    invoices: list[ErpInvoiceData],
    vendor_map: dict[str, str],
    fx: FxService,
    base_currency: str,
    fx_counts: dict[str, int],
    hard_reset: bool = False,
) -> tuple[dict[str, str], int, int, int, int]:
    """Upsert Invoice + InvoiceLine (+ scan File) as pending."""
    voucher_invoice_map: dict[str, str] = {}
    n_lines = 0
    n_queued = 0
    n_withdrawn = 0
    for inv in invoices:
        invoice_id = _det_id("invoice", company_id, inv.erp_id)
        vendor_id = vendor_map.get(inv.vendor_erp_id)
        file_id = _persist_file(session, company_id, invoice_id, inv)
        row = session.get(Invoice, invoice_id)
        if row is None:
            row = Invoice(id=invoice_id, company_id=company_id, status=InvoiceStatus.UNCATEGORIZED)
            session.add(row)
        previous_file_id = row.file_id
        assign = _assigner(session, row, hard_reset)
        assign("vendor_id", vendor_id)
        row.file_id = file_id
        if _queue_document(session, row, previous_file_id):
            n_queued += 1
        assign("invoice_number", inv.invoice_number)
        assign("invoice_date", inv.invoice_date)
        assign("currency", inv.currency)
        assign("total", _dec(inv.total))
        assign("tax", _dec(inv.tax))
        row.raw_json = inv.raw
        _safe_convert(fx_counts, lambda: fx.convert_invoice(row, base_currency))

        if inv.voucher_id is not None:
            voucher_invoice_map[inv.voucher_id] = invoice_id

        superseded = _superseding_origins(session, invoice_id)
        if superseded:
            n_withdrawn += _withdraw_superseded_erp_lines(session, invoice_id)
            continue

        stated_line_ids: set[str] = set()
        for idx, line in enumerate(inv.lines):
            line_key = line.line_erp_id or str(idx)
            line_id = _det_id("line", invoice_id, line_key)
            stated_line_ids.add(line_id)
            lrow = session.get(InvoiceLine, line_id)
            if lrow is None:
                lrow = InvoiceLine(id=line_id, company_id=company_id,
                                   invoice_id=invoice_id, status=LineStatus.UNCATEGORIZED,
                                   origin=LineOrigin.ERP)
                session.add(lrow)
            lrow.origin = LineOrigin.ERP
            lrow.sequence = idx
            assign_line = _assigner(session, lrow, hard_reset)
            assign_line("item_name", line.item_name or line.description)
            assign_line("description", line.description if line.item_name else None)
            assign_line("quantity", _dec(line.quantity))
            assign_line("unit", line.unit)
            assign_line("unit_price", _dec(line.unit_price))
            assign_line("amount", _dec(line.amount))
            lrow.native_account_code = line.native_account_code
            lrow.raw_json = line.raw
            _safe_convert(
                fx_counts,
                lambda lrow=lrow: fx.convert_line(
                    lrow, base_currency,
                    currency=inv.currency, invoice_date=inv.invoice_date,
                ),
            )
            n_lines += 1

        if stated_line_ids:
            n_withdrawn += _withdraw_unstated_lines(session, invoice_id, stated_line_ids)
    session.commit()
    return voucher_invoice_map, len(invoices), n_lines, n_queued, n_withdrawn


def _superseding_origins(session: Session, invoice_id: str) -> bool:
    """Whether a document has been read for this invoice."""
    return session.exec(
        select(InvoiceLine.id).where(
            InvoiceLine.invoice_id == invoice_id,
            InvoiceLine.origin == LineOrigin.DOCUMENT_AI,
        ).limit(1)
    ).first() is not None


def _withdraw_superseded_erp_lines(session: Session, invoice_id: str) -> int:
    """Remove ERP-derived lines left beside a better source's."""
    doomed = session.exec(
        select(InvoiceLine).where(
            InvoiceLine.invoice_id == invoice_id,
            InvoiceLine.origin.in_(  # type: ignore[union-attr]
                (LineOrigin.ERP, LineOrigin.ENTRY_FALLBACK)
            ),
        )
    ).all()
    if not doomed:
        return 0

    return _withdraw_lines(session, invoice_id, doomed)


def _withdraw_unstated_lines(
    session: Session, invoice_id: str, stated_ids: set[str]
) -> int:
    """Remove the invoice's ERP lines that this fetch did not restate."""
    doomed = [
        line for line in session.exec(
            select(InvoiceLine).where(
                InvoiceLine.invoice_id == invoice_id,
                InvoiceLine.origin == LineOrigin.ERP,
            )
        ).all()
        if line.id not in stated_ids
    ]
    if not doomed:
        return 0

    return _withdraw_lines(session, invoice_id, doomed)


def _withdraw_lines(session: Session, invoice_id: str, doomed: list[InvoiceLine]) -> int:
    """Unlink, audit and delete ``doomed`` lines, then refresh the invoice status."""
    doomed_ids = [line.id for line in doomed]
    for entry in session.exec(
        select(ErpEntry).where(ErpEntry.source_invoice_line_id.in_(doomed_ids))  # type: ignore[union-attr]
    ).all():
        entry.source_invoice_line_id = None
        session.add(entry)

    for line in doomed:
        record_audit(
            session,
            entity_type="invoice_line",
            entity_id=line.id,
            action=WITHDRAWN_ACTION,
            actor=SYSTEM_ACTOR,
            changes=[
                {"field": field, "old": _audit_value(line, field), "new": None}
                for field in _WITHDRAWN_FIELDS
            ],
        )
        session.delete(line)

    session.flush()
    recompute_invoice_status(session, invoice_id)
    return len(doomed)


def _audit_value(row, field: str):
    """A row's value for the audit trail, JSON-safe."""
    value = getattr(row, field, None)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _source_line_id(
    session: Session, source_invoice_id: Optional[str], entry: ErpEntryData
) -> Optional[str]:
    """The `InvoiceLine` a posting came from, or None when it came from no line."""
    if source_invoice_id is None or entry.source_line_erp_id is None:
        return None
    line_id = _det_id("line", source_invoice_id, entry.source_line_erp_id)
    if session.get(InvoiceLine, line_id) is None:
        logger.warning("  entry %s references unknown invoice line %s",
                       entry.erp_entry_id, entry.source_line_erp_id)
        return None
    return line_id


def _persist_entries(
    session: Session,
    company_id: str,
    integration_id: str,
    entries: list[ErpEntryData],
    voucher_invoice_map: dict[str, str],
    account_map: dict[str, str],
    fx: FxService,
    base_currency: str,
    fx_counts: dict[str, int],
) -> tuple[int, int]:
    """Upsert raw ErpEntry rows, linking each to its invoice via the voucher."""
    n_entries = 0
    n_linked = 0
    for e in entries:
        erp_account_id = account_map.get(e.erp_account_code)
        if erp_account_id is None:
            logger.warning("  skipping entry %s: unknown account %s",
                           e.erp_entry_id, e.erp_account_code)
            continue
        entry_id = _det_id("entry", integration_id, e.erp_entry_id)
        source_invoice_id = voucher_invoice_map.get(e.voucher_id)
        source_invoice_line_id = _source_line_id(session, source_invoice_id, e)
        row = session.get(ErpEntry, entry_id)
        if row is None:
            row = ErpEntry(id=entry_id, company_id=company_id,
                           erp_account_id=erp_account_id,
                           entry_type=e.entry_type)
            session.add(row)
        row.erp_account_id = erp_account_id
        row.entry_type = e.entry_type
        row.voucher_id = e.voucher_id
        row.voucher_number = e.voucher_number
        row.source_invoice_id = source_invoice_id
        row.source_invoice_line_id = source_invoice_line_id
        row.accounting_date = e.accounting_date
        row.description = e.description
        row.debit_amount = _dec(e.debit_amount)
        row.credit_amount = _dec(e.credit_amount)
        row.currency = e.currency
        row.erp_entry_id = e.erp_entry_id
        row.raw_json = e.raw
        _safe_convert(fx_counts, lambda row=row: fx.convert_entry(row, base_currency))
        n_entries += 1
        if source_invoice_id is not None:
            n_linked += 1
    session.commit()
    return n_entries, n_linked


def _persist_standin_lines(
    session: Session,
    company_id: str,
    invoice_ids: set[str],
    fx: FxService,
    base_currency: str,
    fx_counts: dict[str, int],
    hard_reset: bool = False,
) -> int:
    """Stand a line in for every expense posting on an invoice that has none."""
    if not invoice_ids:
        return 0

    rows = session.exec(
        select(ErpEntry, ErpAccount.erp_account_type, ErpAccount.erp_account_code)
        .join(ErpAccount, ErpAccount.id == ErpEntry.erp_account_id)
        .where(ErpEntry.source_invoice_id.in_(invoice_ids))  # type: ignore[union-attr]
    ).all()

    postings: dict[str, list[tuple[ErpEntry, str]]] = {}
    for entry, account_type, account_code in rows:
        if account_type != EXPENSE_ACCOUNT_TYPE:
            continue
        postings.setdefault(entry.source_invoice_id, []).append((entry, account_code))

    n_written = 0
    for invoice_id in sorted(invoice_ids):
        existing = session.exec(
            select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id)
        ).all()
        if any(line.origin != LineOrigin.ENTRY_FALLBACK for line in existing):
            continue

        invoice = session.get(Invoice, invoice_id)
        if invoice is None:  # pragma: no cover
            continue

        for seq, (entry, account_code) in enumerate(
            sorted(postings.get(invoice_id, []), key=lambda pair: pair[0].id)
        ):
            line_id = _det_id("standin", entry.id)
            lrow = session.get(InvoiceLine, line_id)
            if lrow is None:
                lrow = InvoiceLine(id=line_id, company_id=company_id,
                                   invoice_id=invoice_id, status=LineStatus.UNCATEGORIZED,
                                   origin=LineOrigin.ENTRY_FALLBACK)
                session.add(lrow)
            lrow.origin = LineOrigin.ENTRY_FALLBACK
            lrow.sequence = seq
            assign_line = _assigner(session, lrow, hard_reset)
            assign_line(
                "amount",
                (entry.debit_amount or _ZERO) - (entry.credit_amount or _ZERO),
            )
            assign_line("item_name", entry.description)
            assign_line("description", None)
            lrow.native_account_code = account_code
            _safe_convert(
                fx_counts,
                lambda lrow=lrow, entry=entry, invoice=invoice: fx.convert_line(
                    lrow, base_currency,
                    currency=entry.currency or invoice.currency,
                    invoice_date=invoice.invoice_date,
                ),
            )
            entry.source_invoice_line_id = line_id
            n_written += 1

    session.commit()
    return n_written


def _withdraw_voided_vouchers(
    session: Session, integration_id: str, voucher_ids: set[str]
) -> int:
    """Delete this integration's postings for vouchers the ERP has voided."""
    if not voucher_ids:
        return 0
    entries = session.exec(
        select(ErpEntry)
        .join(ErpAccount, ErpEntry.erp_account_id == ErpAccount.id)
        .where(
            ErpAccount.erp_integration_id == integration_id,
            ErpEntry.voucher_id.in_(voucher_ids),  # type: ignore[union-attr]
        )
    ).all()
    for entry in entries:
        record_audit(
            session,
            entity_type="erp_entry",
            entity_id=entry.id,
            action=VOIDED_ACTION,
            actor=SYSTEM_ACTOR,
            changes=[
                {"field": field, "old": _audit_value(entry, field), "new": None}
                for field in _VOIDED_ENTRY_FIELDS
            ],
        )
        session.delete(entry)
    if entries:
        logger.info("    withdrew %d posting(s) from %d voided voucher(s)",
                    len(entries), len(voucher_ids))
    return len(entries)


def _call_stub(label: str, fn, *args) -> object:
    """Call a downstream stub, tolerating not-yet-implemented bodies."""
    try:
        result = fn(*args)
    except NotImplementedError:
        logger.info("  %s: not implemented yet (stub)", label)
        return "stub"
    if result is Ellipsis or result is None:
        logger.info("  %s: stub (no output yet)", label)
        return "stub"
    logger.info("  %s: %s rows", label, len(result) if hasattr(result, "__len__") else "ok")
    return result


def _build_summary(session: Session, company_id: str) -> dict:
    invoices = session.exec(select(Invoice).where(Invoice.company_id == company_id)).all()
    lines = session.exec(select(InvoiceLine).where(InvoiceLine.company_id == company_id)).all()
    entries = session.exec(select(ErpEntry).where(ErpEntry.company_id == company_id)).all()
    vendor_ids = {inv.vendor_id for inv in invoices if inv.vendor_id is not None}

    def _counts(rows, attr="status"):
        out: dict[str, int] = {}
        for r in rows:
            out[getattr(r, attr)] = out.get(getattr(r, attr), 0) + 1
        return out

    categorized = [ln for ln in lines if ln.status in (LineStatus.AI_CATEGORIZED, LineStatus.VERIFIED)]
    total_spend = sum((ln.amount or Decimal(0)) for ln in categorized)
    spend_by_l2: dict[str, Decimal] = {}
    for ln in categorized:
        key = ln.level_2 or "Uncategorized"
        spend_by_l2[key] = spend_by_l2.get(key, Decimal(0)) + (ln.amount or Decimal(0))

    return {
        "vendors": len(vendor_ids),
        "invoices": len(invoices),
        "invoice_status": _counts(invoices),
        "lines": len(lines),
        "line_status": _counts(lines),
        "entries": len(entries),
        "entries_linked": sum(1 for e in entries if e.source_invoice_id is not None),
        "categorized_spend": float(total_spend),
        "spend_by_level_2": {k: float(v) for k, v in sorted(spend_by_l2.items())},
    }


def _sync_one(
    session: Session,
    integration: ErpIntegration,
    connector: ErpConnector,
    since_override: date | None,
    fx: FxService,
    base_currency: str,
    hard_reset: bool = False,
) -> dict:
    """Run the full pipeline for one integration."""
    company_id = integration.company_id
    integration_id = integration.id
    fx_counts = _fx_counts()

    sync_state = _begin_sync_state(session, integration_id)
    since = _resolve_since(sync_state, since_override)

    try:
        connector.authorize()
        if not connector.test_connection():
            raise RuntimeError(
                f"Could not reach the {integration.erp_type} ERP — is it running?"
            )

        logger.info("  [1/6] Fetching accounts & vendors…")
        accounts = connector.fetch_accounts()
        vendors = connector.fetch_vendors(since=since)
        account_map = _persist_accounts(session, integration_id, accounts)
        enabled_codes = _enabled_account_codes(session, integration_id)
        logger.info("    fetched %d accounts (%d enabled for sync), %d vendors",
                    len(accounts), len(enabled_codes), len(vendors))

        entries = connector.fetch_entries(since=since, account_codes=enabled_codes)
        vouchers: dict[str, list[ErpEntryData]] = {}
        for e in entries:
            vouchers.setdefault(e.voucher_id, []).append(e)
        invoice_vouchers = [
            v for v, es in vouchers.items()
            if any(e.entry_type == "purchase_invoice" for e in es)
        ]
        invoices: list[ErpInvoiceData] = []
        for v in invoice_vouchers:
            scan = connector.fetch_invoice_scan(v)
            if scan is not None:
                invoices.append(scan)
        logger.info("    fetched %d entries (%d vouchers, %d invoice scans)",
                    len(entries), len(vouchers), len(invoices))

        logger.info("  [2/6] Persisting to PostgreSQL…")
        vendor_map = _persist_vendors(session, vendors)
        voucher_invoice_map, n_inv, n_lines, n_queued, n_withdrawn = _persist_invoices(
            session, company_id, invoices, vendor_map, fx, base_currency, fx_counts,
            hard_reset=hard_reset,
        )
        n_entries, n_linked = _persist_entries(
            session, company_id, integration_id, entries,
            voucher_invoice_map, account_map, fx, base_currency, fx_counts
        )
        n_entries_withdrawn = _withdraw_voided_vouchers(
            session, integration_id, connector.voided_voucher_ids()
        )
        session.commit()
        n_standin = _persist_standin_lines(
            session, company_id, set(voucher_invoice_map.values()),
            fx, base_currency, fx_counts, hard_reset,
        )
        n_lines += n_standin
        logger.info("    persisted %d invoices, %d lines (%d standing in for a posting), "
                    "%d entries (%d linked to an invoice)",
                    n_inv, n_lines, n_standin, n_entries, n_linked)
        logger.info("    queued %d invoices for document processing", n_queued)
        logger.info("    converted to %s: %d rows (%d unconverted, %d already current)",
                    base_currency, fx_counts[CONVERTED],
                    fx_counts[UNCONVERTED], fx_counts[UNCHANGED])

        logger.info("  [3/6] Categorizing pending invoice lines…")
        cat_stats = categorize_integration(session, integration_id, company_id)
        categorization_skipped = cat_stats.get("skipped")

        logger.info("  [4/6] Aggregating spend…")
        _call_stub("spend_by_category", aggregation.spend_by_category, company_id)
        _call_stub("spend_by_vendor", aggregation.spend_by_vendor, company_id)
        logger.info("  [5/6] Detecting redundant vendors…")
        _call_stub("same_category_overlaps", redundancy.find_same_category_overlaps, company_id)
        logger.info("  [6/6] Generating savings recommendations…")
        _call_stub("recommendations", recommender.all_recommendations, company_id)

        summary = _build_summary(session, company_id)
        _finish_sync_state(
            session, sync_state, invoices, status="idle", error=categorization_skipped
        )
        summary["status"] = "ok"
        summary["company_id"] = company_id
        summary["erp_type"] = integration.erp_type
        summary["categorization"] = cat_stats
        summary["accounts"] = len(accounts)
        summary["accounts_enabled"] = len(enabled_codes)
        summary["documents_queued"] = n_queued
        summary["standin_lines"] = n_standin
        summary["lines_withdrawn"] = n_withdrawn
        summary["entries_withdrawn"] = n_entries_withdrawn
        summary["base_currency"] = base_currency
        summary["fx"] = fx_counts
        return summary
    except Exception as exc:
        _finish_sync_state(session, sync_state, [], status="error", error=str(exc))
        raise


def run_sync(
    *,
    since: date | None = None,
    integration_id: str | None = None,
    hard_reset: bool = False,
) -> dict[str, dict]:
    """Sync every connected ERP integration."""
    SQLModel.metadata.create_all(engine)
    results: dict[str, dict] = {}

    with Session(engine) as session:
        work = connected_integrations(session, integration_id)
        if not work:
            logger.info(
                "No connected ERP integrations — create a company with an ERP "
                "connection in Settings first."
            )
            return results

        logger.info("Syncing %d connected integration(s)…", len(work))
        fx = FxService(session)
        for integration in work:
            company = session.get(Company, integration.company_id)
            label = company.name if company is not None else integration.company_id
            base_currency = company.base_currency if company is not None else "EUR"
            logger.info("[%s] %s via %s", label, integration.id, integration.erp_type)
            try:
                connector_settings = _connector_config(session, integration)
                connector: ErpConnector = get_connector(integration.erp_type, connector_settings)
                results[integration.id] = _sync_one(
                    session, integration, connector, since, fx, base_currency,
                    hard_reset=hard_reset,
                )
                logger.info("  done: %s", results[integration.id])
            except Exception as exc:
                logger.error("  FAILED: %s", exc)
                results[integration.id] = {
                    "status": "error",
                    "error": str(exc),
                    "company_id": integration.company_id,
                    "erp_type": integration.erp_type,
                }
    return results


def _begin_sync_state(session: Session, integration_id: str) -> SyncState:
    """Mark this integration as syncing, preserving what it already knows."""
    state_id = _det_id("sync_state", integration_id)
    state = session.get(SyncState, state_id)
    if state is None:
        state = SyncState(id=state_id, erp_integration_id=integration_id)
        session.add(state)
    state.status = "syncing"
    state.error_message = None
    session.commit()
    return state


def _finish_sync_state(
    session: Session,
    state: SyncState,
    invoices: list[ErpInvoiceData],
    *,
    status: str,
    error: str | None = None,
) -> None:
    watermark = max((inv.invoice_date for inv in invoices), default=None)
    state.last_sync_at = _now()
    if watermark is not None and (
        state.last_invoice_date is None or watermark > state.last_invoice_date
    ):
        state.last_invoice_date = watermark
    state.status = status
    state.error_message = error
    session.add(state)
    session.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync every connected ERP integration. Companies and their "
                    "ERP connections are created in the app, never here.",
    )
    parser.add_argument(
        "--integration-id", default=None,
        help="Sync only this integration (must already exist and be connected)",
    )
    parser.add_argument(
        "--since", default=None,
        help="Backfill from this ISO date, overriding each integration's own watermark",
    )
    parser.add_argument(
        "--hard-reset", action="store_true",
        help="Overwrite fields a human verified with the ERP's values. Opt-in, "
             "audited as 'system', and never implied by any other flag. Human-added "
             "lines are not deleted.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    since = date.fromisoformat(args.since) if args.since else None
    if args.hard_reset:
        logger.warning(
            "--hard-reset: human-verified values will be overwritten by the ERP's "
            "(each one audited, so the overwritten value stays recoverable)"
        )

    try:
        results = run_sync(
            since=since, integration_id=args.integration_id, hard_reset=args.hard_reset
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    if not results:
        print("\nNothing to sync — no connected ERP integrations.")
        return 0

    failed = 0
    for integration_id, summary in results.items():
        print(f"\n=== {integration_id} ({summary.get('erp_type')}) ===")
        if summary.get("status") == "error":
            failed += 1
            print(f"status: error\nerror: {summary['error']}")
            continue
        for key, value in summary.items():
            print(f"{key}: {value}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
