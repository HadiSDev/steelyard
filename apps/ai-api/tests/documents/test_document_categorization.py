"""A document read categorizes the lines it created."""
from __future__ import annotations

import pytest
from sqlmodel import Session, select

from ai_api.documents import runner as docs
from ai_api.documents.content import ExtractedLines
from ai_api.models import LineItem
from ai_api.sync import runner as sync_runner
from ai_api_testkit import BALANCED_VOUCHER, SCAN_WITHOUT_LINES, TYPED_ACCOUNTS
from web_api.connectors.base import DocumentPayload
from web_api.db.models import Company, DocStatus, Invoice, InvoiceLine, LineOrigin, LineStatus
from web_api.spend_trees import service


@pytest.fixture(autouse=True)
def _stage_engine(engine, monkeypatch):
    monkeypatch.setattr(docs, "engine", engine)
    return engine


@pytest.fixture(autouse=True)
def _serves_a_document(fake_connector, monkeypatch):
    monkeypatch.setattr(
        fake_connector, "fetch_invoice_document",
        lambda self, voucher_id: DocumentPayload(
            content=b"%PDF-1.4 fake", media_type="application/pdf", filename="inv-1.pdf"
        ),
        raising=False,
    )


def _sync(engine, fake_connector, make_tenant, *, with_tree: bool) -> dict:
    fake_connector.accounts = TYPED_ACCOUNTS
    fake_connector.entries = BALANCED_VOUCHER
    fake_connector.scan = SCAN_WITHOUT_LINES
    tenant = make_tenant("Acme")
    if with_tree:
        with Session(engine) as s:
            company = s.get(Company, tenant["company_id"])
            tree = service.ensure_default_tree(s, company.organization_id)
            company.spend_tree_id = tree.id
            s.add(company)
            s.commit()
    sync_runner.run_sync()
    return tenant


def _extractor(*amounts: str):
    def _extract(payload: DocumentPayload) -> ExtractedLines:
        return ExtractedLines(
            lines=[
                LineItem(description=f"Cloud hosting part {i + 1}", amount=float(a))
                for i, a in enumerate(amounts)
            ]
        )

    return _extract


def _extracted_lines(engine) -> list[InvoiceLine]:
    with Session(engine) as s:
        return list(
            s.exec(
                select(InvoiceLine).where(InvoiceLine.origin == LineOrigin.DOCUMENT_AI)
            ).all()
        )


def _invoice(engine) -> Invoice:
    with Session(engine) as s:
        return s.exec(select(Invoice)).one()


def test_a_processed_read_leaves_no_line_uncategorized(engine, fake_connector, make_tenant):
    _sync(engine, fake_connector, make_tenant, with_tree=True)

    counts = docs.run_documents(extract=_extractor("600.00", "400.00"))

    lines = _extracted_lines(engine)
    assert counts["processed"] == 1
    assert len(lines) == 2
    assert all(
        line.status in (LineStatus.AI_CATEGORIZED, LineStatus.AI_FAILED) for line in lines
    )
    assert counts["categorized"] + counts["categorization_failed"] == 2
    assert counts["categorization_skipped"] == 0


def test_a_rejected_read_categorizes_nothing(engine, fake_connector, make_tenant, monkeypatch):
    _sync(engine, fake_connector, make_tenant, with_tree=True)
    calls: list[str] = []
    monkeypatch.setattr(
        docs, "categorize_company",
        lambda session, company_id, invoice_ids=None: calls.append(company_id),
    )

    counts = docs.run_documents(extract=_extractor("300.00"))

    assert counts["rejected"] == 1
    assert calls == []
    assert counts["categorized"] == 0


def test_a_failed_read_categorizes_nothing(engine, fake_connector, make_tenant, monkeypatch):
    _sync(engine, fake_connector, make_tenant, with_tree=True)
    calls: list[str] = []
    monkeypatch.setattr(
        docs, "categorize_company",
        lambda session, company_id, invoice_ids=None: calls.append(company_id),
    )

    counts = docs.run_documents(extract=lambda payload: ExtractedLines(lines=[]))

    assert counts["failed"] == 1
    assert calls == []


def test_only_the_read_invoice_is_categorized(engine, fake_connector, make_tenant, monkeypatch):
    tenant = _sync(engine, fake_connector, make_tenant, with_tree=True)
    seen: list[tuple[str, list[str]]] = []

    def record(session, company_id, invoice_ids=None):
        seen.append((company_id, list(invoice_ids)))
        return {"categorized": 0, "failed": 0, "invoices_completed": 0, "invoices_failed": 0}

    monkeypatch.setattr(docs, "categorize_company", record)

    docs.run_documents(extract=_extractor("1000.00"))

    assert seen == [(tenant["company_id"], [_invoice(engine).id])]


def test_no_tree_leaves_the_lines_uncategorized_and_says_so(engine, fake_connector, make_tenant):
    _sync(engine, fake_connector, make_tenant, with_tree=False)

    counts = docs.run_documents(extract=_extractor("1000.00"))

    assert counts["processed"] == 1
    assert counts["categorization_skipped"] == 1
    assert counts["categorized"] == 0
    assert [line.status for line in _extracted_lines(engine)] == [LineStatus.UNCATEGORIZED]


def test_a_categorization_crash_keeps_the_extraction(
    engine, fake_connector, make_tenant, monkeypatch
):
    _sync(engine, fake_connector, make_tenant, with_tree=True)

    def crash(session, company_id, invoice_ids=None):
        raise RuntimeError("categorizer fell over")

    monkeypatch.setattr(docs, "categorize_company", crash)

    counts = docs.run_documents(extract=_extractor("1000.00"))

    assert counts["processed"] == 1
    assert counts["categorization_errors"] == 1
    assert _invoice(engine).doc_status == DocStatus.PROCESSED
    assert [line.status for line in _extracted_lines(engine)] == [LineStatus.UNCATEGORIZED]
