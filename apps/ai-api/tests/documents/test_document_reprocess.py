"""Reading documents again in bulk: which invoices are put back in the queue, and that they are read."""
from __future__ import annotations

import pytest
from sqlmodel import Session, select

from ai_api.documents import runner as docs
from ai_api.documents.content import ExtractedLines
from ai_api.documents.requeue import requeue_documents
from ai_api.models import LineItem
from ai_api.sync import runner as sync_runner
from ai_api_testkit import BALANCED_VOUCHER, SCAN_WITHOUT_LINES, TYPED_ACCOUNTS
from web_api.connectors.base import DocumentPayload
from web_api.db.models import AuditLog, DocStatus, Invoice


@pytest.fixture(autouse=True)
def _stage_engine(engine, monkeypatch):
    monkeypatch.setattr(docs, "engine", engine)
    return engine


@pytest.fixture(autouse=True)
def _serves_a_document(fake_connector, monkeypatch):
    monkeypatch.setattr(
        fake_connector, "fetch_invoice_document",
        lambda self, voucher_id: DocumentPayload(content=b"%PDF", media_type="application/pdf",
                                                 filename="invoice.pdf"),
        raising=False,
    )


@pytest.fixture
def synced(engine, fake_connector, make_tenant):
    fake_connector.accounts = TYPED_ACCOUNTS
    fake_connector.entries = BALANCED_VOUCHER
    fake_connector.scan = SCAN_WITHOUT_LINES
    tenant = make_tenant("Acme")
    sync_runner.run_sync()
    return tenant


def _extract_with_website(payload: DocumentPayload) -> ExtractedLines:
    return ExtractedLines(lines=[LineItem(description="Beans", amount=1000.0)],
                          supplier_website="https://danskkaffe.dk/")


def _set_status(engine, status: DocStatus, *, attempts: int = 1) -> str:
    with Session(engine) as s:
        invoice = s.exec(select(Invoice)).one()
        invoice.doc_status = status
        invoice.doc_attempts = attempts
        invoice.doc_error = "boom" if status == DocStatus.FAILED else None
        s.add(invoice)
        s.commit()
        return invoice.id


def _invoice(engine) -> Invoice:
    with Session(engine) as s:
        return s.exec(select(Invoice)).one()


@pytest.mark.parametrize("status", [DocStatus.PROCESSED, DocStatus.FAILED])
def test_a_read_or_failed_document_is_put_back_in_the_queue(engine, synced, status):
    invoice_id = _set_status(engine, status, attempts=3)

    with Session(engine) as s:
        requeued = requeue_documents(s)

    invoice = _invoice(engine)
    assert requeued == 1
    assert invoice.doc_status == DocStatus.PENDING
    assert invoice.doc_attempts == 0
    assert invoice.doc_error is None
    with Session(engine) as s:
        audit = s.exec(select(AuditLog).where(AuditLog.entity_id == invoice_id,
                                              AuditLog.action == "reprocess_document")).all()
    assert len(audit) == 1


@pytest.mark.parametrize("status", [DocStatus.PROCESSING, DocStatus.NOT_APPLICABLE, DocStatus.PENDING])
def test_a_document_being_read_or_absent_or_waiting_is_left_alone(engine, synced, status):
    _set_status(engine, status)

    with Session(engine) as s:
        requeued = requeue_documents(s)

    assert requeued == 0
    assert _invoice(engine).doc_status == status


def test_the_selectors_narrow_what_is_put_back(engine, synced):
    _set_status(engine, DocStatus.PROCESSED)

    with Session(engine) as s:
        assert requeue_documents(s, company_id="another-company") == 0
        assert requeue_documents(s, invoice_id="another-invoice") == 0
        assert requeue_documents(s, limit=0) == 0

    assert _invoice(engine).doc_status == DocStatus.PROCESSED


def test_reprocessing_reads_the_documents_again(engine, synced):
    _set_status(engine, DocStatus.PROCESSED)

    counts = docs.run_documents(reprocess=True, extract=_extract_with_website)

    invoice = _invoice(engine)
    assert counts["processed"] == 1
    assert invoice.doc_status == DocStatus.PROCESSED
    assert invoice.document_supplier_website == "https://danskkaffe.dk/"


def test_without_reprocessing_a_read_document_is_not_read_again(engine, synced):
    _set_status(engine, DocStatus.PROCESSED)

    counts = docs.run_documents(extract=_extract_with_website)

    assert counts["processed"] == 0
