"""VAT numbers in their international form: the country's prefix, then the number."""
from __future__ import annotations

import re

_VAT_PREFIXES = {"GR": "EL"}
_SEPARATORS = re.compile(r"[\s.\-]")


def international_vat(vat_number: str | None, country_code: str | None) -> str | None:
    """The VAT number with its country prefix; one that already starts with letters is kept as stated."""
    compact = _SEPARATORS.sub("", vat_number or "").upper()
    if not compact:
        return None
    if compact[:2].isalpha() or not country_code:
        return compact
    country = country_code.strip().upper()
    return f"{_VAT_PREFIXES.get(country, country)}{compact}"
