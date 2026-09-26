"""Fixtures for the worker: every stage pointed at the test engine."""
from __future__ import annotations

import pytest

from ai_api.documents import runner as documents_runner
from ai_api.documents.content import ExtractedLines
from ai_api.models import LineItem
from ai_api.sync import runner as sync_runner
from ai_api.worker import loop
from ai_api_testkit import BALANCED_VOUCHER, SCAN_WITHOUT_LINES, TYPED_ACCOUNTS
from web_api.connectors.base import DocumentPayload


def _balanced_extract(payload: DocumentPayload) -> ExtractedLines:
    return ExtractedLines(lines=[LineItem(description="Cloud hosting", amount=1000.0)])


@pytest.fixture
def worker_engine(engine, monkeypatch):
    """The worker, the sync and the document stage all on the test engine."""
    monkeypatch.setattr(loop, "engine", engine)
    monkeypatch.setattr(documents_runner, "engine", engine)
    return engine


@pytest.fixture
def offline_reads(fake_connector, monkeypatch):
    """Documents are served by the fake ERP and read by a stub extractor."""
    monkeypatch.setattr(
        fake_connector, "fetch_invoice_document",
        lambda self, voucher_id: DocumentPayload(
            content=b"%PDF-1.4 fake", media_type="application/pdf", filename="inv-1.pdf"
        ),
        raising=False,
    )
    original = documents_runner.run_documents

    def run_documents(**kwargs):
        return original(extract=_balanced_extract, **kwargs)

    monkeypatch.setattr(documents_runner, "run_documents", run_documents)


@pytest.fixture
def documented_tenant(worker_engine, fake_connector, make_tenant):
    """Sync a tenant whose invoice has a document waiting to be read."""
    fake_connector.accounts = TYPED_ACCOUNTS
    fake_connector.entries = BALANCED_VOUCHER
    fake_connector.scan = SCAN_WITHOUT_LINES

    def _make(name: str = "Acme") -> dict:
        tenant = make_tenant(name)
        sync_runner.run_sync(integration_id=tenant["integration_id"])
        return tenant

    return _make
