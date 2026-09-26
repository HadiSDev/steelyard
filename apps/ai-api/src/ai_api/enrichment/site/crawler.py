"""A supplier's site as one capped text: its home page and the pages about what it sells, cached by host.

Each page gets an equal share of the cap, so one long page cannot crowd out the others.
"""
from __future__ import annotations

from typing import Callable
from urllib.parse import urlsplit

from ... import config
from ...web_context import read_cache, write_cache
from .discovery import pages_to_crawl

PagePicker = Callable[[list[str]], list[str]]
SiteFetcher = Callable[[str, PagePicker], list[str]]


def crawl_site(
    root: str,
    *,
    fetch_site: SiteFetcher,
    max_pages: int | None = None,
    max_chars: int | None = None,
    cache_dir: str | None = None,
) -> str:
    """The site's text, fetched once and read from the cache afterwards; empty when nothing could be read."""
    max_pages = config.SUPPLIER_CRAWL_MAX_PAGES if max_pages is None else max_pages
    max_chars = config.SUPPLIER_CRAWL_MAX_CHARS if max_chars is None else max_chars
    cache_dir = config.WEB_CONTEXT_CACHE_DIR if cache_dir is None else cache_dir

    key = f"site-{urlsplit(root).hostname or root}"
    cached = read_cache(cache_dir, key)
    if cached is not None:
        return cached

    def pick(links: list[str]) -> list[str]:
        return pages_to_crawl(root, links, max_pages)

    pages = [page.strip() for page in fetch_site(root, pick) if page.strip()]
    share = max_chars // max(len(pages), 1)
    text = "\n\n".join(page[:share] for page in pages)
    if text:
        write_cache(cache_dir, key, text)
    return text
