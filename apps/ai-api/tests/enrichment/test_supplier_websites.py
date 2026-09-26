"""Finding the website of a supplier already described, without touching its description."""
from __future__ import annotations

import json

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from ai_api.enrichment.supplier_profile import locate_website, site_description
from ai_api.enrichment.websites import find_vendor_websites, vendors_needing_website
from web_api.db.models import Company, Invoice, Organization, Vendor

RESULTS = [
    {"title": "EKWB - Wikipedia", "body": "EKWB is a Slovenian company.", "href": "https://en.wikipedia.org/wiki/EKWB"},
    {"title": "EK Water Blocks", "body": "Liquid cooling.", "href": "https://www.ekwb.com/shop/"},
]


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _vendor(s: Session, name: str, **kwargs) -> Vendor:
    vendor = Vendor(name=name, **kwargs)
    s.add(vendor)
    s.commit()
    return vendor


def _locating(website: str | None):
    asked: list[tuple[str, str | None]] = []

    def locate(name: str, country_code: str | None, known: str | None) -> str | None:
        asked.append((name, known))
        return website

    locate.asked = asked  # type: ignore[attr-defined]
    return locate


def test_only_described_suppliers_without_a_website_are_considered(session):
    _vendor(session, "EKWB", description="Cooling parts.")
    _vendor(session, "Hetzner", description="Hosting.", website="https://www.hetzner.com/")
    _vendor(session, "Undescribed ApS")

    assert [v.name for v in vendors_needing_website(session)] == ["EKWB"]


def test_a_found_website_is_stored_and_the_description_kept(session):
    _vendor(session, "EKWB", description="Cooling parts.", description_source="web")

    result = find_vendor_websites(session, enabled=True, locate=_locating("https://www.ekwb.com/"))

    vendor = session.exec(select(Vendor)).one()
    assert vendor.website == "https://www.ekwb.com/"
    assert vendor.description == "Cooling parts."
    assert result.found == 1


def test_nothing_found_stores_nothing(session):
    _vendor(session, "EKWB", description="Cooling parts.")

    result = find_vendor_websites(session, enabled=True, locate=_locating(None))

    assert session.exec(select(Vendor)).one().website is None
    assert result.not_found == 1


def test_a_printed_website_that_names_the_supplier_is_handed_on(session):
    vendor = _vendor(session, "CS-Online A/S", description="Electronics retailer.")
    org = Organization(name="Org")
    session.add(org)
    session.commit()
    company = Company(organization_id=org.id, name="Acme", base_currency="DKK")
    session.add(company)
    session.commit()
    session.add(Invoice(company_id=company.id, vendor_id=vendor.id, status="uncategorized",
                        document_supplier_website="https://www.csmegastore.dk/"))
    session.commit()
    locate = _locating("https://www.csmegastore.dk/")

    find_vendor_websites(session, enabled=True, locate=locate)

    assert locate.asked == [("CS-Online A/S", "https://www.csmegastore.dk/")]


def test_disabled_does_nothing(session):
    _vendor(session, "EKWB", description="Cooling parts.")
    locate = _locating("https://www.ekwb.com/")

    result = find_vendor_websites(session, enabled=False, locate=locate)

    assert locate.asked == []
    assert result.considered == 0


def _answer(is_site: bool) -> str:
    return json.dumps({"is_supplier_site": is_site, "description": "Liquid cooling parts." if is_site else ""})


def test_a_known_website_is_returned_as_it_is(tmp_path):
    searched: list[str] = []

    site = locate_website("EKWB", "SI", "https://www.ekwb.com/",
                          search_fn=lambda q: searched.append(q) or RESULTS, cache_dir=str(tmp_path))

    assert site == "https://www.ekwb.com/"
    assert searched == []


def test_a_searched_website_is_kept_only_when_its_site_confirms_it(tmp_path):
    confirmed = locate_website(
        "EKWB", "SI", search_fn=lambda q: RESULTS, crawl_fn=lambda root: "EK makes water blocks.",
        summarize_site_fn=lambda name, country, text: site_description(_answer(True)),
        cache_dir=str(tmp_path / "a"),
    )
    rejected = locate_website(
        "EKWB", "SI", search_fn=lambda q: RESULTS, crawl_fn=lambda root: "Someone else.",
        summarize_site_fn=lambda name, country, text: site_description(_answer(False)),
        cache_dir=str(tmp_path / "b"),
    )

    assert confirmed == "https://www.ekwb.com/"
    assert rejected is None


def test_without_a_crawler_a_search_finds_nothing(tmp_path):
    assert locate_website("EKWB", "SI", search_fn=lambda q: RESULTS, cache_dir=str(tmp_path)) is None
