"""Which search result is the supplier's own website, and which of its pages say what it sells."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

MIN_KEY_LENGTH = 3

LEGAL_FORMS = frozenset({
    "ab", "ag", "amba", "aps", "as", "bv", "co", "corp", "gmbh", "inc", "is",
    "ivs", "ks", "limited", "llc", "ltd", "nv", "oy", "plc", "ps", "sa",
    "sarl", "sas", "smba", "spa", "srl",
})

BLOCKED_HOSTS = frozenset({
    "amazon.com", "bing.com", "bloomberg.com", "cvr.dk", "cvrapi.dk",
    "crunchbase.com", "dnb.com", "duckduckgo.com", "ebay.com", "facebook.com",
    "instagram.com", "krak.dk", "linkedin.com",
    "northdata.com", "opencorporates.com", "proff.dk", "proff.no", "proff.se",
    "trustpilot.com", "twitter.com", "virk.dk", "wikipedia.org", "x.com",
    "youtube.com", "yelp.com",
})

PAGE_KEYWORDS: tuple[tuple[str, ...], ...] = (
    ("about", "om-os", "omos", "om_os", "company", "virksomhed", "who-we-are"),
    ("product", "produkt", "sortiment", "catalog", "katalog"),
    ("service", "ydelse", "solution", "loesning", "losning", "løsning"),
)

_DANISH_LETTERS = str.maketrans({"æ": "ae", "ø": "oe", "å": "aa", "ä": "ae", "ö": "oe", "ü": "ue"})


def name_keys(name: str) -> list[str]:
    """The supplier's name words joined cumulatively: "Dansk Kaffe ApS" gives dansk, danskkaffe."""
    words = []
    for token in name.lower().translate(_DANISH_LETTERS).split():
        word = re.sub(r"[^a-z0-9]", "", token)
        if word and word not in LEGAL_FORMS:
            words.append(word)
    keys = ["".join(words[:count]) for count in range(1, len(words) + 1)]
    return [key for key in keys if len(key) >= MIN_KEY_LENGTH]


def find_website(name: str, results: list[dict]) -> str | None:
    """The root of the first result whose domain names the supplier, skipping directories and social networks."""
    keys = name_keys(name)
    if not keys:
        return None
    for result in results:
        parts = urlsplit(result.get("href") or "")
        host = (parts.hostname or "").lower()
        if not host or _is_blocked(host):
            continue
        if _host_names(host, keys):
            return f"{parts.scheme or 'https'}://{host}/"
    return None


def pages_to_crawl(root: str, links: list[str], limit: int) -> list[str]:
    """Up to `limit` same-site pages about the company, its products or its services, in that order."""
    root_host = _bare_host(urlsplit(root).hostname or "")
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for position, link in enumerate(links):
        parts = urlsplit(link)
        if _bare_host(parts.hostname or "") != root_host:
            continue
        path = parts.path.rstrip("/")
        if not path:
            continue
        url = f"{parts.scheme}://{parts.hostname}{path}"
        if url in seen:
            continue
        seen.add(url)
        rank = _page_rank(path.lower())
        if rank is not None:
            ranked.append((rank, position, url))
    ranked.sort()
    return [url for _, _, url in ranked[:limit]]


def _is_blocked(host: str) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in BLOCKED_HOSTS)


def _host_names(host: str, keys: list[str]) -> bool:
    full = keys[-1]
    for label in host.split(".")[:-1]:
        joined = label.replace("-", "")
        if joined in keys or full in joined:
            return True
    return False


def _bare_host(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        return host[len("www."):]
    return host


def _page_rank(path: str) -> int | None:
    for rank, keywords in enumerate(PAGE_KEYWORDS):
        if any(keyword in path for keyword in keywords):
            return rank
    return None
