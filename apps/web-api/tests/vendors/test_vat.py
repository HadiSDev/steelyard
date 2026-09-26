"""A VAT number is always stated internationally: the country's prefix, then the number."""
from __future__ import annotations

import pytest

from web_api.vat import international_vat


@pytest.mark.parametrize("vat, country, expected", [
    ("12644426", "DK", "DK12644426"),
    ("DK12644426", "DK", "DK12644426"),
    ("dk 12 64 44 26", "DK", "DK12644426"),
    ("123 456-789", "se", "SE123456789"),
    ("094014298", "GR", "EL094014298"),
    ("EL094014298", "GR", "EL094014298"),
    ("IE6388047V", "IE", "IE6388047V"),
    ("HRB38891", "DE", "HRB38891"),
    ("12644426", None, "12644426"),
    ("", "DK", None),
    ("   ", "DK", None),
    (None, "DK", None),
])
def test_a_vat_number_is_stated_internationally(vat, country, expected):
    assert international_vat(vat, country) == expected
