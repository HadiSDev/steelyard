"""The Suppliers page's overview: the org's suppliers, their figures, search, sort, paging."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session

from web_api.db.models import Company, Invoice, Vendor

from web_api_testkit import auth

_URL = "/api/v1/vendors/overview"


def _invoice(s: Session, company_id: str, vendor_id: str, *, total: str | None,
             tax: str | None = None, on: date | None = None, base: str = "DKK") -> None:
    s.add(Invoice(
        company_id=company_id, vendor_id=vendor_id, invoice_date=on,
        currency=base, total=None if total is None else Decimal(total),
        base_currency=None if total is None else base,
        base_total=None if total is None else Decimal(total),
        base_tax=None if tax is None else Decimal(tax),
    ))


@pytest.fixture
def suppliers(engine, seed):
    """Org A buys from Acme (two companies), Beta (shared with Org B) and Cloud (unconverted)."""
    with Session(engine) as s:
        acme = Vendor(name="Acme Supplies", country_code="DK", vat_number="DK111",
                      description="Office furniture", website="https://acmesupplies.dk/")
        beta = Vendor(name="Beta Legal", country_code="DK", vat_number="DK222")
        cloud = Vendor(name="Cloud Co", country_code="DE", vat_number="DE333")
        unused = Vendor(name="Zeta Unused", vat_number="DK999")
        for vendor in (acme, beta, cloud, unused):
            s.add(vendor)
        second = Company(organization_id=seed["org_a"], name="Acme A2", base_currency="DKK")
        s.add(second)
        s.commit()

        s.get(Invoice, seed["inv_a"]).vendor_id = acme.id
        s.get(Invoice, seed["inv_b"]).vendor_id = beta.id
        _invoice(s, seed["comp_a"], acme.id, total="1250.00", tax="250.00", on=date(2025, 9, 10))
        _invoice(s, second.id, acme.id, total="300.00", on=date(2025, 10, 1))
        _invoice(s, seed["comp_a"], beta.id, total="500.00", on=date(2025, 8, 1))
        _invoice(s, seed["comp_a"], cloud.id, total=None, on=date(2025, 6, 1))
        s.commit()
        return {
            **seed, "second": second.id,
            "acme": acme.id, "beta": beta.id, "cloud": cloud.id, "unused": unused.id,
        }


def _get(client, token: str = "tokA", **params):
    return client.get(_URL, params=params, headers=auth(token))


def _rows(client, token: str = "tokA", **params) -> list[dict]:
    res = _get(client, token, **params)
    assert res.status_code == 200, res.text
    return res.json()["items"]


def _by_id(rows: list[dict]) -> dict[str, dict]:
    return {row["id"]: row for row in rows}


def _spend(row: dict) -> dict[str | None, Decimal]:
    return {entry["currency"]: Decimal(entry["amount"]) for entry in row["spend"]}


def test_only_the_organizations_suppliers_are_listed(client, suppliers):
    ids = {row["id"] for row in _rows(client)}

    assert ids == {suppliers["acme"], suppliers["beta"], suppliers["cloud"]}


def test_each_supplier_carries_its_website(client, suppliers):
    rows = _by_id(_rows(client))

    assert rows[suppliers["acme"]]["website"] == "https://acmesupplies.dk/"
    assert rows[suppliers["beta"]]["website"] is None


def test_a_shared_supplier_carries_only_the_callers_figures(client, suppliers):
    beta_for_a = _by_id(_rows(client))[suppliers["beta"]]
    beta_for_b = _by_id(_rows(client, "tokB"))[suppliers["beta"]]

    assert beta_for_a["invoice_count"] == 1
    assert _spend(beta_for_a) == {"DKK": Decimal("500.00")}
    assert beta_for_b["invoice_count"] == 1
    assert _spend(beta_for_b) == {"DKK": Decimal("50.00")}


def test_the_company_filter_narrows_list_and_figures(client, suppliers):
    rows = _rows(client, company_id=suppliers["second"])

    assert [row["id"] for row in rows] == [suppliers["acme"]]
    assert rows[0]["invoice_count"] == 1
    assert _spend(rows[0]) == {"DKK": Decimal("300.00")}


def test_a_foreign_company_is_404(client, suppliers):
    assert _get(client, company_id=suppliers["comp_b"]).status_code == 404


def test_a_row_carries_the_suppliers_identity(client, suppliers):
    acme = _by_id(_rows(client))[suppliers["acme"]]

    assert acme["name"] == "Acme Supplies"
    assert acme["country_code"] == "DK"
    assert acme["vat_number"] == "DK111"
    assert acme["description"] == "Office furniture"


def test_spend_is_net_of_vat_in_base_currency(client, suppliers):
    acme = _by_id(_rows(client))[suppliers["acme"]]

    assert acme["invoice_count"] == 3
    assert _spend(acme) == {"DKK": Decimal("1400.00")}


def test_the_last_invoice_date_is_the_latest(client, suppliers):
    acme = _by_id(_rows(client))[suppliers["acme"]]

    assert acme["last_invoice_date"] == "2025-10-01"


def test_an_unconverted_invoice_is_counted_not_summed(client, suppliers):
    cloud = _by_id(_rows(client))[suppliers["cloud"]]

    assert cloud["invoice_count"] == 1
    assert _spend(cloud) == {"DKK": Decimal("0")}
    assert cloud["spend"][0]["unconverted_count"] == 1


def test_two_base_currencies_stay_apart(client, suppliers, engine):
    with Session(engine) as s:
        euro = Company(organization_id=suppliers["org_a"], name="Acme EU", base_currency="EUR")
        s.add(euro)
        s.commit()
        _invoice(s, euro.id, suppliers["acme"], total="200.00", base="EUR", on=date(2025, 5, 1))
        s.commit()

    acme = _by_id(_rows(client, sort="name"))[suppliers["acme"]]

    assert _spend(acme) == {"DKK": Decimal("1400.00"), "EUR": Decimal("200.00")}


def test_search_matches_the_name_case_insensitively(client, suppliers):
    assert [row["id"] for row in _rows(client, q="ACME")] == [suppliers["acme"]]


def test_search_matches_part_of_a_vat_number(client, suppliers):
    assert [row["id"] for row in _rows(client, q="E33")] == [suppliers["cloud"]]


def test_the_default_order_is_largest_spend_first(client, suppliers):
    names = [row["name"] for row in _rows(client)]

    assert names == ["Acme Supplies", "Beta Legal", "Cloud Co"]


@pytest.mark.parametrize(("sort", "order", "expected"), [
    ("name", "asc", ["Acme Supplies", "Beta Legal", "Cloud Co"]),
    ("name", "desc", ["Cloud Co", "Beta Legal", "Acme Supplies"]),
    ("spend", "asc", ["Cloud Co", "Beta Legal", "Acme Supplies"]),
    ("invoice_count", "desc", ["Acme Supplies", "Beta Legal", "Cloud Co"]),
    ("last_invoice_date", "desc", ["Acme Supplies", "Beta Legal", "Cloud Co"]),
    ("last_invoice_date", "asc", ["Cloud Co", "Beta Legal", "Acme Supplies"]),
])
def test_each_sort_orders_the_rows(client, suppliers, sort, order, expected):
    assert [row["name"] for row in _rows(client, sort=sort, order=order)] == expected


def test_ties_are_broken_by_name_and_each_row_is_on_one_page(client, suppliers):
    pages = [
        _rows(client, sort="invoice_count", order="asc", page=page, page_size=1)
        for page in (1, 2, 3)
    ]

    assert [page[0]["name"] for page in pages] == ["Beta Legal", "Cloud Co", "Acme Supplies"]


def test_the_page_envelope_counts_every_match(client, suppliers):
    body = _get(client, page_size=2).json()

    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_the_page_size_is_capped_at_one_hundred(client, suppliers):
    assert _get(client, page_size=101).status_code == 422


def test_an_unknown_sort_is_422(client, suppliers):
    assert _get(client, sort="vat_number").status_code == 422


def test_a_spend_sort_across_base_currencies_is_refused(client, suppliers, engine):
    with Session(engine) as s:
        s.add(Company(organization_id=suppliers["org_a"], name="Acme EU", base_currency="EUR"))
        s.commit()

    res = _get(client, sort="spend")

    assert res.status_code == 422
    assert "currenc" in res.json()["detail"]


def test_without_a_shared_currency_the_default_order_is_by_name(client, suppliers, engine):
    with Session(engine) as s:
        s.add(Company(organization_id=suppliers["org_a"], name="Acme EU", base_currency="EUR"))
        s.commit()

    names = [row["name"] for row in _rows(client)]

    assert names == ["Acme Supplies", "Beta Legal", "Cloud Co"]


def test_a_named_sort_defaults_to_ascending_and_a_figure_to_descending(client, suppliers):
    assert [row["name"] for row in _rows(client, sort="name")][0] == "Acme Supplies"
    assert [row["name"] for row in _rows(client, sort="invoice_count")][0] == "Acme Supplies"


def test_an_organization_without_suppliers_gets_an_empty_page(client, suppliers):
    body = _get(client, "tok_empty").json()

    assert body == {"items": [], "page": 1, "page_size": 25, "total": 0}
