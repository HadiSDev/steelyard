"""Websites in one form: the root of the site, `scheme://host/`."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

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
