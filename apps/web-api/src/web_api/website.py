"""Websites in one form, the root of the site (`scheme://host/`), and whether one is a supplier's."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

MIN_KEY_LENGTH = 3

LEGAL_FORMS = frozenset({
    "ab", "ag", "amba", "aps", "as", "bv", "co", "corp", "gmbh", "inc", "is",
    "ivs", "ks", "limited", "llc", "ltd", "nv", "oy", "plc", "ps", "sa",
    "sarl", "sas", "smba", "spa", "srl", "uab",
})

_DANISH_LETTERS = str.maketrans({"æ": "ae", "ø": "oe", "å": "aa", "ä": "ae", "ö": "oe", "ü": "ue"})
_SCHEMES = ("http", "https")
_HOST = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def site_root(website: str | None) -> str | None:
    """The root of the site a printed web address names, or None when it names none."""
    text = (website or "").strip().rstrip(".")
    if not text or "@" in text:
        return None
    if "://" not in text:
        text = f"https://{text}"
    parts = urlsplit(text)
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in _SCHEMES or not _HOST.match(host):
        return None
    return f"{parts.scheme}://{host}/"


def name_keys(name: str) -> list[str]:
    """The supplier's name words joined cumulatively: "Dansk Kaffe ApS" gives dansk, danskkaffe."""
    words = []
    for token in name.lower().translate(_DANISH_LETTERS).split():
        word = re.sub(r"[^a-z0-9]", "", token)
        if word and word not in LEGAL_FORMS:
            words.append(word)
    keys = ["".join(words[:count]) for count in range(1, len(words) + 1)]
    return [key for key in keys if len(key) >= MIN_KEY_LENGTH]


def host_names_supplier(host: str, name: str) -> bool:
    """Whether a label of the host, before its top-level domain, is the supplier's name or contains it whole."""
    keys = name_keys(name)
    if not keys:
        return False
    full = keys[-1]
    for label in host.lower().split(".")[:-1]:
        joined = label.replace("-", "")
        if joined in keys or full in joined:
            return True
    return False


def website_names_supplier(website: str, name: str) -> bool:
    """Whether the website's host names the supplier."""
    return host_names_supplier(urlsplit(website).hostname or "", name)
