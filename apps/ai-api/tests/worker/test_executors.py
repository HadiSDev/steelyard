"""Each run kind executes its stage for one company and summarizes it."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select

from ai_api.worker import executors
from ai_api.worker.executors import RunFailed, execute
from web_api.db.models import DocStatus, ErpIntegration, Invoice, InvoiceLine, LineStatus
from worker_testkit import assign_default_tree


def _line_statuses(engine) -> list[str]:
    with Session(engine) as s:
        return [line.status for line in s.exec(select(InvoiceLine)).all()]


def test_sync_syncs_the_companys_integration(worker_engine, make_tenant, fake_connector):
    tenant = make_tenant("Acme")

    with Session(worker_engine) as s:
        summary = execute(s, "sync", tenant["company_id"])

    assert summary["integrations"] == 1
    assert summary["invoices"] == 1
    assert summary["lines"] == 1
    assert "no spend tree" in summary["categorization_skipped"]
    assert fake_connector.seen_configs, "the ERP was contacted"


def test_sync_categorizes_when_the_company_has_a_tree(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    assign_default_tree(worker_engine, tenant["company_id"])

    with Session(worker_engine) as s:
        summary = execute(s, "sync", tenant["company_id"])

    assert summary["categorized"] == 1
    assert "categorization_skipped" not in summary


def test_sync_leaves_other_companies_alone(worker_engine, make_tenant, fake_connector):
    acme = make_tenant("Acme")
    make_tenant("Globex")

    with Session(worker_engine) as s:
        execute(s, "sync", acme["company_id"])

    with Session(worker_engine) as s:
        companies = {invoice.company_id for invoice in s.exec(select(Invoice)).all()}
    assert companies == {acme["company_id"]}


def test_sync_without_a_connected_integration_fails(worker_engine, make_tenant):
    tenant = make_tenant("Acme", connected=False)

    with Session(worker_engine) as s:
        with pytest.raises(RunFailed, match="no connected ERP integration"):
            execute(s, "sync", tenant["company_id"])


def test_an_unreachable_erp_fails_the_sync(worker_engine, make_tenant, fake_connector):
    tenant = make_tenant("Acme")
    fake_connector.reachable = False

    with Session(worker_engine) as s:
        with pytest.raises(RunFailed, match="Could not reach"):
            execute(s, "sync", tenant["company_id"])


def test_read_documents_reads_the_companys_pending_documents(
    worker_engine, documented_tenant, offline_reads
):
    tenant = documented_tenant("Acme")

    with Session(worker_engine) as s:
        summary = execute(s, "read_documents", tenant["company_id"])

    assert summary["processed"] == 1
    assert summary["categorization_skipped"] == 1
    with Session(worker_engine) as s:
        assert s.exec(select(Invoice)).one().doc_status == DocStatus.PROCESSED


def test_read_documents_with_nothing_pending_reports_zero(worker_engine, make_tenant):
    tenant = make_tenant("Acme")

    with Session(worker_engine) as s:
        summary = execute(s, "read_documents", tenant["company_id"])

    assert summary["processed"] == 0


def test_categorize_categorizes_without_contacting_the_erp(
    worker_engine, make_tenant, fake_connector
):
    tenant = make_tenant("Acme")
    with Session(worker_engine) as s:
        execute(s, "sync", tenant["company_id"])
    assign_default_tree(worker_engine, tenant["company_id"])
    fake_connector.reachable = False

    with Session(worker_engine) as s:
        summary = execute(s, "categorize", tenant["company_id"])

    assert summary["categorized"] == 1
    assert _line_statuses(worker_engine) == [LineStatus.AI_CATEGORIZED]


def test_categorize_works_for_a_disconnected_company_by_skipping(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    with Session(worker_engine) as s:
        integration = s.get(ErpIntegration, tenant["integration_id"])
        integration.disconnected_at = datetime.now(timezone.utc)
        s.add(integration)
        s.commit()

    with Session(worker_engine) as s:
        summary = execute(s, "categorize", tenant["company_id"])

    assert "no connected ERP integration" in summary["skipped"]


def test_an_unavailable_categorizer_fails_the_run(worker_engine, make_tenant, monkeypatch):
    tenant = make_tenant("Acme")
    monkeypatch.setattr(
        executors, "categorize_company",
        lambda session, company_id: {"categorized": 0, "unavailable": "model down"},
    )

    with Session(worker_engine) as s:
        with pytest.raises(RunFailed, match="model down"):
            execute(s, "categorize", tenant["company_id"])


def test_an_unknown_kind_fails(worker_engine, make_tenant):
    tenant = make_tenant("Acme")

    with Session(worker_engine) as s:
        with pytest.raises(RunFailed, match="unknown run kind"):
            execute(s, "reindex", tenant["company_id"])
