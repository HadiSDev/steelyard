"""How much of the spend the ERP posted has been categorized, over the listed vouchers."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlmodel import Session, select

from web_api.db.models import ErpEntry, InvoiceLine

from web_api_testkit import auth

_URL = "/api/v1/erp-entries/vouchers/summary"


@pytest.fixture
def converted(engine, voucher_seed):
    """The seeded postings converted into the company's DKK at par."""
    with Session(engine) as s:
        for entry in s.exec(select(ErpEntry)).all():
            entry.base_currency = "DKK"
            entry.fx_rate = Decimal("1")
            entry.base_debit_amount = entry.debit_amount
            entry.base_credit_amount = entry.credit_amount
            s.add(entry)
        s.commit()
    return voucher_seed


def _summary(client, token: str = "tokA", **params) -> dict:
    res = client.get(_URL, params=params, headers=auth(token))
    assert res.status_code == 200
    rows = res.json()["rows"]
    assert len(rows) == 1
    return rows[0]


def _set_line(engine, line_id: str, **fields) -> None:
    with Session(engine) as s:
        line = s.get(InvoiceLine, line_id)
        for name, value in fields.items():
            setattr(line, name, value)
        s.add(line)
        s.commit()


def test_posted_spend_is_the_net_spend_of_every_listed_voucher(client, converted):
    row = _summary(client)

    assert row["currency"] == "DKK"
    assert row["voucher_count"] == 2
    assert Decimal(row["posted_spend"]) == Decimal("110.00")


def test_categorized_spend_counts_only_categorized_lines(client, converted):
    row = _summary(client)

    assert Decimal(row["categorized_spend"]) == Decimal("20.00")
    assert row["line_count"] == 2
    assert row["categorized_lines"] == 1
    assert row["uncategorized_lines"] == 1


def test_a_verified_line_counts_as_categorized_and_as_verified(client, converted, engine):
    _set_line(engine, converted["line_a1"], status="verified")

    row = _summary(client)

    assert Decimal(row["categorized_spend"]) == Decimal("100.00")
    assert row["categorized_lines"] == 2
    assert row["verified_lines"] == 1


def test_a_doubtful_categorization_needs_review(client, converted, engine):
    _set_line(engine, converted["line_a2"], confidence=Decimal("0.2"))

    row = _summary(client)

    assert row["needs_review_lines"] == 1
    assert row["categorized_lines"] == 1


def test_a_failed_line_is_counted_apart(client, converted, engine):
    _set_line(engine, converted["line_a1"], status="ai_failed")

    row = _summary(client)

    assert row["failed_lines"] == 1
    assert row["uncategorized_lines"] == 0


def test_the_summary_follows_the_table_filters(client, converted):
    row = _summary(client, entry_type="purchase_invoice")

    assert row["voucher_count"] == 1
    assert Decimal(row["posted_spend"]) == Decimal("100.00")


def test_an_unconverted_posting_is_counted_not_summed(client, voucher_seed):
    row = _summary(client)

    assert row["unconverted_vouchers"] == 2
    assert Decimal(row["posted_spend"]) == Decimal("0")


def test_another_tenant_sees_none_of_it(client, converted):
    res = client.get(_URL, headers=auth("tokB"))

    assert res.status_code == 200
    assert all(row["voucher_count"] == 0 for row in res.json()["rows"])
