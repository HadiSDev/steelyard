"""A website as an invoice prints it, reduced to the site's root."""
from __future__ import annotations

import pytest

from web_api.website import site_root


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
