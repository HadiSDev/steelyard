"""Putting documents already read, or failed, back in the queue to be read again."""
from __future__ import annotations

from sqlmodel import Session, select

from web_api.audit import diff_changes, record_audit
from web_api.db.models import DocStatus, Invoice

REQUEUEABLE = (DocStatus.PROCESSED, DocStatus.FAILED)
_AUDITED = ("doc_status", "doc_error")


def requeue_documents(
    session: Session,
    *,
    company_id: str | None = None,
    invoice_id: str | None = None,
    limit: int | None = None,
) -> int:
    """Mark the selected invoices' read or failed documents as pending, as the API's reprocess does."""
    statement = select(Invoice).where(
        Invoice.doc_status.in_(REQUEUEABLE),  # type: ignore[attr-defined]
        Invoice.file_id.is_not(None),  # type: ignore[union-attr]
    )
    if company_id is not None:
        statement = statement.where(Invoice.company_id == company_id)
    if invoice_id is not None:
        statement = statement.where(Invoice.id == invoice_id)
    statement = statement.order_by(Invoice.invoice_date, Invoice.id)
    if limit is not None:
        statement = statement.limit(limit)

    invoices = list(session.exec(statement).all())
    for invoice in invoices:
        before = {"doc_status": invoice.doc_status, "doc_error": invoice.doc_error}
        invoice.doc_status = DocStatus.PENDING
        invoice.doc_error = None
        invoice.doc_attempts = 0
        session.add(invoice)
        record_audit(
            session, entity_type="invoice", entity_id=invoice.id, action="reprocess_document",
            changes=diff_changes(
                before, {"doc_status": invoice.doc_status, "doc_error": invoice.doc_error}, _AUDITED,
            ),
        )
    session.commit()
    return len(invoices)
