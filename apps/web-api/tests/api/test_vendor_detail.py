"""A supplier's detail: tenant scoping, its figures, its categories and its latest invoices."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session

from web_api.db.models import (
    Company, ErpAccount, ErpEntry, ErpIntegration, Invoice, InvoiceLine, SpendCategory, SpendTree,
    Vendor,
)

from web_api_testkit import auth


def _url(vendor_id: str) -> str:
    return f"/api/v1/vendors/{vendor_id}/detail"


@pytest.fixture
def supplier(engine, seed):
    """Acme sells to Org A (three invoices, one of them undated) and to Org B (one invoice)."""
    with Session(engine) as s:
        acme = Vendor(name="Acme Supplies", country_code="DK", vat_number="DK111",
                      description="Office furniture", description_source="web",
                      website="https://acmesupplies.dk/")
        stranger = Vendor(name="Stranger ApS")
        tree = SpendTree(organization_id=seed["org_a"], name="Default")
        s.add(acme)
        s.add(stranger)
        s.add(tree)
        s.commit()
        cloud = SpendCategory(spend_tree_id=tree.id, name="Cloud hosting")
        s.add(cloud)
        s.commit()

        s.get(Invoice, seed["inv_a"]).vendor_id = acme.id
        s.get(Invoice, seed["inv_b"]).vendor_id = acme.id
        s.get(InvoiceLine, seed["line_a2"]).spend_category_id = cloud.id
        later = Invoice(company_id=seed["comp_a"], vendor_id=acme.id, invoice_number="A2",
                        invoice_date=date(2025, 9, 1), currency="EUR", total=Decimal("40.00"),
                        base_currency="DKK", base_total=Decimal("300.00"), base_tax=Decimal("60.00"),
                        status="categorized")
        undated = Invoice(company_id=seed["comp_a"], vendor_id=acme.id, invoice_number="A0",
                          currency="DKK", total=Decimal("5.00"), status="uncategorized")
        s.add(later)
        s.add(undated)
        s.commit()
        s.add(InvoiceLine(company_id=seed["comp_a"], invoice_id=later.id, description="Servers",
                          amount=Decimal("32.00"), base_currency="DKK", base_amount=Decimal("240.00"),
                          status="verified", sequence=0, spend_category_id=cloud.id))
        s.commit()
        return {**seed, "acme": acme.id, "stranger": stranger.id, "cloud": cloud.id}


def _detail(client, vendor_id: str, token: str = "tokA", **params) -> dict:
    res = client.get(_url(vendor_id), params=params, headers=auth(token))
    assert res.status_code == 200, res.text
    return res.json()


def test_the_supplier_is_described(client, supplier):
    body = _detail(client, supplier["acme"])

    assert body["name"] == "Acme Supplies"
    assert body["country_code"] == "DK"
    assert body["vat_number"] == "DK111"
    assert body["description"] == "Office furniture"
    assert body["description_source"] == "web"
    assert body["website"] == "https://acmesupplies.dk/"


def test_its_figures_cover_only_the_callers_invoices(client, supplier):
    body = _detail(client, supplier["acme"])

    assert body["invoice_count"] == 3
    assert body["first_invoice_date"] == "2025-07-01"
    assert body["last_invoice_date"] == "2025-09-01"
    assert [(s["currency"], Decimal(s["amount"]), s["unconverted_count"]) for s in body["spend"]] == [
        ("DKK", Decimal("340.00"), 1),
    ]


def test_another_tenant_sees_its_own_figures(client, supplier):
    body = _detail(client, supplier["acme"], token="tokB")

    assert body["invoice_count"] == 1
    assert [i["invoice_number"] for i in body["recent_invoices"]] == ["B1"]


def test_its_lines_are_grouped_by_category_largest_first(client, supplier):
    body = _detail(client, supplier["acme"])

    assert [
        (c["category_name"], c["currency"], Decimal(c["amount"]), c["line_count"])
        for c in body["categories"]
    ] == [
        ("Cloud hosting", "DKK", Decimal("260.00"), 2),
        (None, "DKK", Decimal("80.00"), 1),
    ]
    assert body["categories"][0]["category_id"] == supplier["cloud"]


def test_its_latest_invoices_come_newest_first_with_undated_last(client, supplier):
    body = _detail(client, supplier["acme"])

    invoices = body["recent_invoices"]
    assert [i["invoice_number"] for i in invoices] == ["A2", "A1", "A0"]
    assert invoices[0]["company_name"] == "Acme A"
    assert invoices[0]["currency"] == "EUR"
    assert Decimal(invoices[0]["total"]) == Decimal("40.00")
    assert invoices[0]["status"] == "categorized"


def test_a_company_filter_narrows_the_figures(client, engine, supplier):
    with Session(engine) as s:
        second = Company(organization_id=supplier["org_a"], name="Acme A2", base_currency="DKK")
        s.add(second)
        s.commit()
        s.add(Invoice(company_id=second.id, vendor_id=supplier["acme"], invoice_number="C1",
                      invoice_date=date(2025, 10, 1), status="uncategorized"))
        s.commit()
        second_id = second.id

    body = _detail(client, supplier["acme"], company_id=second_id)

    assert body["invoice_count"] == 1
    assert [i["invoice_number"] for i in body["recent_invoices"]] == ["C1"]


def test_a_supplier_the_caller_never_bought_from_is_not_found(client, supplier):
    res = client.get(_url(supplier["stranger"]), headers=auth("tokA"))

    assert res.status_code == 404


def test_an_unknown_supplier_is_not_found(client, supplier):
    res = client.get(_url("no-such-vendor"), headers=auth("tokA"))

    assert res.status_code == 404


def test_a_foreign_company_is_not_found(client, supplier):
    res = client.get(_url(supplier["acme"]), params={"company_id": supplier["comp_b"]},
                     headers=auth("tokA"))

    assert res.status_code == 404


def test_a_caller_without_companies_sees_nothing(client, supplier):
    res = client.get(_url(supplier["acme"]), headers=auth("tok_empty"))

    assert res.status_code == 404


def test_an_invoice_is_numbered_by_its_document_when_the_erp_has_no_number(client, engine, supplier):
    with Session(engine) as s:
        invoice = s.get(Invoice, supplier["inv_a"])
        invoice.invoice_number = None
        invoice.document_invoice_number = "2026-0412"
        s.add(invoice)
        s.commit()

    invoices = {i["id"]: i for i in _detail(client, supplier["acme"])["recent_invoices"]}

    assert invoices[supplier["inv_a"]]["invoice_number"] == "2026-0412"


def test_an_invoice_carries_the_voucher_it_was_posted_on(client, engine, supplier):
    with Session(engine) as s:
        integration = ErpIntegration(company_id=supplier["comp_a"], erp_type="mock", label="ERP")
        s.add(integration)
        s.commit()
        account = ErpAccount(erp_integration_id=integration.id, erp_account_code="6200",
                             erp_account_name="Software", erp_account_type="expense")
        s.add(account)
        s.commit()
        s.add(ErpEntry(company_id=supplier["comp_a"], erp_account_id=account.id,
                       source_invoice_id=supplier["inv_a"], voucher_id="v-4821",
                       voucher_number="4821", entry_type="purchase_invoice",
                       debit_amount=Decimal("100.00"), currency="DKK"))
        s.commit()

    invoices = {i["id"]: i for i in _detail(client, supplier["acme"])["recent_invoices"]}

    assert invoices[supplier["inv_a"]]["voucher_number"] == "4821"
    assert invoices[supplier["inv_a"]]["invoice_number"] == "A1"
    unposted = [i for i in invoices.values() if i["id"] != supplier["inv_a"]]
    assert all(i["voucher_number"] is None for i in unposted)
