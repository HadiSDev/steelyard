"""A voucher group says whether its document's total matches what the ERP posted."""
from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session

from web_api.db.models import Invoice

from web_api_testkit import auth


def _set_document_totals(engine, invoice_id: str, **figures) -> None:
    with Session(engine) as s:
        invoice = s.get(Invoice, invoice_id)
        for field, value in figures.items():
            setattr(invoice, field, value)
        s.add(invoice)
        s.commit()


def _group(client, voucher_id: str) -> dict:
    body = client.get("/api/v1/erp-entries/vouchers", headers=auth("tokA")).json()
    return next(g for g in body["items"] if g["voucher_id"] == voucher_id)


def test_an_unread_document_has_nothing_to_compare(client, voucher_seed):
    group = _group(client, voucher_seed["voucher"])

    assert group["totals_agree"] is None
    assert group["document_total"] is None


def test_a_matching_document_total_agrees(client, voucher_seed, engine):
    _set_document_totals(engine, voucher_seed["inv_a"], document_total=Decimal("100.00"))

    group = _group(client, voucher_seed["voucher"])

    assert group["totals_agree"] is True


def test_a_different_document_total_is_flagged_with_both_figures(client, voucher_seed, engine):
    _set_document_totals(engine, voucher_seed["inv_a"], document_total=Decimal("130.00"))

    group = _group(client, voucher_seed["voucher"])

    assert group["totals_agree"] is False
    assert Decimal(group["document_total"]) == Decimal("130.00")
    assert Decimal(group["invoice_total"]) == Decimal("100.00")
    assert group["invoice_currency"] == "DKK"


def test_a_document_stating_the_net_of_the_posted_gross_agrees(client, voucher_seed, engine):
    _set_document_totals(engine, voucher_seed["inv_a"], document_total=Decimal("125.00"),
                         document_subtotal=Decimal("100.00"))

    assert _group(client, voucher_seed["voucher"])["totals_agree"] is True


def test_a_voucher_without_an_invoice_has_nothing_to_compare(client, voucher_seed):
    body = client.get("/api/v1/erp-entries/vouchers", headers=auth("tokA")).json()
    unvouchered = next(g for g in body["items"] if g["voucher_id"] is None)

    assert unvouchered["totals_agree"] is None
    assert unvouchered["invoice_total"] is None


def test_the_group_and_the_invoice_panel_give_the_same_verdict(client, voucher_seed, engine):
    _set_document_totals(engine, voucher_seed["inv_a"], document_total=Decimal("130.00"))

    group = _group(client, voucher_seed["voucher"])
    invoice = client.get(f"/api/v1/invoices/{voucher_seed['inv_a']}", headers=auth("tokA")).json()

    assert group["totals_agree"] == invoice["totals_agree"]
