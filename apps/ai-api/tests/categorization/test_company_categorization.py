"""Categorizing one company's lines without contacting the ERP."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from ai_api.categorization import company as company_categorization
from ai_api.categorization import categorize_company, categorize_integration
from ai_api.sync import runner
from web_api.db.models import Company, ErpIntegration, Invoice, InvoiceLine, LineStatus
from web_api.spend_trees import service


def _synced_without_a_tree(engine, make_tenant, name: str = "Acme") -> dict:
    """A tenant whose sync landed its lines but left them uncategorized."""
    tenant = make_tenant(name)
    runner.run_sync(integration_id=tenant["integration_id"])
    return tenant


def _assign_default_tree(engine, company_id: str) -> None:
    with Session(engine) as s:
        company = s.get(Company, company_id)
        tree = service.ensure_default_tree(s, company.organization_id)
        company.spend_tree_id = tree.id
        s.add(company)
        s.commit()


def _statuses(engine, company_id: str) -> list[str]:
    with Session(engine) as s:
        return [
            line.status
            for line in s.exec(
                select(InvoiceLine).where(InvoiceLine.company_id == company_id)
            ).all()
        ]


def test_a_company_with_a_tree_has_its_lines_categorized(engine, make_tenant):
    tenant = _synced_without_a_tree(engine, make_tenant)
    assert _statuses(engine, tenant["company_id"]) == [LineStatus.UNCATEGORIZED]
    _assign_default_tree(engine, tenant["company_id"])

    with Session(engine) as s:
        stats = categorize_company(s, tenant["company_id"])

    assert stats["categorized"] == 1
    assert stats["invoices_completed"] == 1
    assert "skipped" not in stats
    assert _statuses(engine, tenant["company_id"]) == [LineStatus.AI_CATEGORIZED]


def test_the_invoice_selector_leaves_other_invoices_alone(engine, make_tenant):
    tenant = _synced_without_a_tree(engine, make_tenant)
    _assign_default_tree(engine, tenant["company_id"])

    with Session(engine) as s:
        stats = categorize_company(s, tenant["company_id"], invoice_ids=["someone-else"])

    assert stats["categorized"] == 0
    assert _statuses(engine, tenant["company_id"]) == [LineStatus.UNCATEGORIZED]


def test_the_invoice_selector_categorizes_the_named_invoice(engine, make_tenant):
    tenant = _synced_without_a_tree(engine, make_tenant)
    _assign_default_tree(engine, tenant["company_id"])
    with Session(engine) as s:
        invoice_id = s.exec(select(Invoice.id)).one()

    with Session(engine) as s:
        stats = categorize_company(s, tenant["company_id"], invoice_ids=[invoice_id])

    assert stats["categorized"] == 1


def test_another_companys_lines_are_never_touched(engine, make_tenant):
    acme = _synced_without_a_tree(engine, make_tenant, "Acme")
    globex = _synced_without_a_tree(engine, make_tenant, "Globex")
    _assign_default_tree(engine, acme["company_id"])
    _assign_default_tree(engine, globex["company_id"])

    with Session(engine) as s:
        categorize_company(s, acme["company_id"])

    assert _statuses(engine, acme["company_id"]) == [LineStatus.AI_CATEGORIZED]
    assert _statuses(engine, globex["company_id"]) == [LineStatus.UNCATEGORIZED]


def test_no_tree_is_reported_as_skipped(engine, make_tenant):
    tenant = _synced_without_a_tree(engine, make_tenant)

    with Session(engine) as s:
        stats = categorize_company(s, tenant["company_id"])

    assert "no spend tree" in stats["skipped"]
    assert stats["categorized"] == 0
    assert _statuses(engine, tenant["company_id"]) == [LineStatus.UNCATEGORIZED]


def test_no_connected_integration_is_reported_as_skipped(engine, make_tenant):
    tenant = _synced_without_a_tree(engine, make_tenant)
    _assign_default_tree(engine, tenant["company_id"])
    with Session(engine) as s:
        integration = s.get(ErpIntegration, tenant["integration_id"])
        integration.disconnected_at = datetime.now(timezone.utc)
        s.add(integration)
        s.commit()

    with Session(engine) as s:
        stats = categorize_company(s, tenant["company_id"])

    assert "no connected ERP integration" in stats["skipped"]
    assert _statuses(engine, tenant["company_id"]) == [LineStatus.UNCATEGORIZED]


def test_the_integration_level_call_reports_the_same_stats(engine, make_tenant):
    tenant = _synced_without_a_tree(engine, make_tenant)
    _assign_default_tree(engine, tenant["company_id"])

    with Session(engine) as s:
        stats = categorize_integration(s, tenant["integration_id"], tenant["company_id"])

    assert stats["categorized"] == 1
    assert stats["failed"] == 0


def test_each_connected_integration_is_categorized_and_the_counts_summed(
    engine, make_tenant, monkeypatch
):
    tenant = make_tenant("Acme")
    with Session(engine) as s:
        second = ErpIntegration(
            company_id=tenant["company_id"], erp_type="fake", label="second",
            connected_at=datetime.now(timezone.utc),
        )
        s.add(second)
        s.commit()
        second_id = second.id

    seen: list[str] = []

    def fake_integration(session, integration_id, company_id, invoice_ids=None):
        seen.append(integration_id)
        return {"categorized": 2, "failed": 1, "invoices_completed": 1,
                "invoices_failed": 1, "cache_hits": 2}

    monkeypatch.setattr(company_categorization, "categorize_integration", fake_integration)

    with Session(engine) as s:
        stats = categorize_company(s, tenant["company_id"])

    assert sorted(seen) == sorted([tenant["integration_id"], second_id])
    assert stats == {"categorized": 4, "failed": 2, "invoices_completed": 2,
                     "invoices_failed": 2, "cache_hits": 4}
