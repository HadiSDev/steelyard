"""A website as an invoice prints it, reduced to the site's root."""
from __future__ import annotations

import pytest

from web_api.website import name_keys, site_root, website_names_supplier


@pytest.mark.parametrize("printed, expected", [
    ("https://www.danskkaffe.dk/", "https://www.danskkaffe.dk/"),
    ("www.danskkaffe.dk", "https://www.danskkaffe.dk/"),
    ("DanskKaffe.dk/kontakt", "https://danskkaffe.dk/"),
    ("http://shop.danskkaffe.dk/om-os?ref=1", "http://shop.danskkaffe.dk/"),
    (" www.danskkaffe.dk. ", "https://www.danskkaffe.dk/"),
    ("info@danskkaffe.dk", None),
    ("mailto:info@danskkaffe.dk", None),
    ("Dansk Kaffe", None),
    ("localhost", None),
    ("ftp://files.danskkaffe.dk", None),
    ("", None),
    (None, None),
])
def test_a_printed_website_is_reduced_to_its_root(printed, expected):
    assert site_root(printed) == expected


@pytest.mark.parametrize("website, name, expected", [
    ("https://danskkaffe.dk/", "Dansk Kaffe ApS", True),
    ("https://www.dansk-kaffe.dk/", "Dansk Kaffe ApS", True),
    ("https://www.revolut.com/", "Revolut Bank UAB", True),
    ("https://www.iidraudimas.lt/", "Revolut Bank UAB", False),
    ("https://danskebank.dk/", "Dansk Kaffe ApS", False),
    ("https://www.hetzner.com/", "Hetzner Online GmbH", True),
    ("https://as.dk/", "A/S", False),
])
def test_a_website_names_the_supplier_only_when_its_domain_carries_the_name(website, name, expected):
    assert website_names_supplier(website, name) is expected


def test_legal_forms_are_not_part_of_the_name():
    assert name_keys("Revolut Bank UAB") == ["revolut", "revolutbank"]
