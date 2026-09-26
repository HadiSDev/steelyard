"""Which search result is the supplier's own website, and which of its pages say what it sells."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from web_api.website import host_names_supplier

BLOCKED_HOSTS = frozenset({
    "amazon.com", "bing.com", "bloomberg.com", "cvr.dk", "cvrapi.dk",
    "crunchbase.com", "dnb.com", "duckduckgo.com", "ebay.com", "facebook.com",
    "instagram.com", "krak.dk", "linkedin.com",
    "northdata.com", "opencorporates.com", "proff.dk", "proff.no", "proff.se",
    "trustpilot.com", "twitter.com", "virk.dk", "wikipedia.org", "x.com",
    "youtube.com", "yelp.com",
})

PAGE_KEYWORDS: tuple[tuple[str, ...], ...] = (
    ("about", "/om-", "omos", "om_os", "company", "virksomhed", "who-we-are"),
    ("product", "produkt", "sortiment", "catalog", "katalog"),
    ("service", "ydelse", "solution", "loesning", "losning", "løsning"),
)

SKIPPED_PAGE_WORDS = (
    "privacy", "privat", "persondata", "cookie", "gdpr", "terms", "betingelser",
    "vilkaar", "vilkår", "legal", "career", "karriere", "job", "news", "nyhed",
    "presse", "press", "blog",
)

def find_website(name: str, results: list[dict]) -> str | None:
    """The root of the first result whose domain names the supplier, skipping directories and social networks."""
    for result in results:
        parts = urlsplit(result.get("href") or "")
        host = (parts.hostname or "").lower()
        if not host or _is_blocked(host):
            continue
        if host_names_supplier(host, name):
            return f"{parts.scheme or 'https'}://{host}/"
    return None


def pages_to_crawl(root: str, links: list[str], limit: int) -> list[str]:
    """Up to `limit` same-site pages about the company, its products or its services, in that order, shallowest first."""
    root_host = _bare_host(urlsplit(root).hostname or "")
    ranked: list[tuple[int, int, int, str]] = []
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
            ranked.append((rank, path.count("/"), position, url))
    ranked.sort()
    return [url for _, _, _, url in ranked[:limit]]


def _is_blocked(host: str) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in BLOCKED_HOSTS)


def _bare_host(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        return host[len("www."):]
    return host


def _page_rank(path: str) -> int | None:
    if _is_skipped(path):
        return None
    for rank, keywords in enumerate(PAGE_KEYWORDS):
        if any(keyword in path for keyword in keywords):
            return rank
    return None


def _is_skipped(path: str) -> bool:
    words = [word for word in re.split(r"[/\-_.]", path) if word]
    return any(
        word.startswith(skipped) or word.endswith(skipped)
        for word in words
        for skipped in SKIPPED_PAGE_WORDS
    )
