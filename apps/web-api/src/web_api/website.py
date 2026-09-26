"""Websites in one form, the root of the site (`scheme://host/`), and whether one is a supplier's."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

MIN_KEY_LENGTH = 3
MIN_WORD_LENGTH = 2

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


def name_words(name: str) -> list[str]:
    """The supplier's name split into words, legal forms dropped: "CS-Online A/S" gives cs, online."""
    words = re.split(r"[^a-z0-9]+", name.lower().translate(_DANISH_LETTERS))
    return [word for word in words if len(word) >= MIN_WORD_LENGTH and word not in LEGAL_FORMS]


def printed_website_names_supplier(website: str, name: str) -> bool:
    """Whether a website printed on the supplier's own invoice names it.

    Looser than for a search result, since the supplier printed it: a label may also be any word
    of the name, or begin with the name's first word.
    """
    if website_names_supplier(website, name):
        return True
    words = name_words(name)
    if not words:
        return False
    host = (urlsplit(website).hostname or "").lower()
    for label in host.split(".")[:-1]:
        joined = label.replace("-", "")
        if joined in words or joined.startswith(words[0]):
            return True
    return False
