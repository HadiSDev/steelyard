"""Crawling a supplier's site: the pages chosen, the cap, and the cache by host."""
from __future__ import annotations

from ai_api.enrichment.site.crawler import PagePicker, crawl_site


class _Site:
    """A stub site: a home page with links, and the text of each page."""

    def __init__(self, home: str, links: list[str], pages: dict[str, str]) -> None:
        self.home = home
        self.links = links
        self.pages = pages
        self.fetched: list[str] = []

    def fetch(self, root: str, pick: PagePicker) -> list[str]:
        self.fetched.append(root)
        return [self.home, *(self.pages[url] for url in pick(self.links))]


def _coffee() -> _Site:
    return _Site(
        "Dansk Kaffe roasts coffee.",
        ["https://danskkaffe.dk/om-os", "https://danskkaffe.dk/kontakt", "https://danskkaffe.dk/produkter"],
        {
            "https://danskkaffe.dk/om-os": "We supply offices.",
            "https://danskkaffe.dk/produkter": "Beans and machines.",
        },
    )


def test_the_home_page_and_pages_about_the_company_are_read(tmp_path):
    site = _coffee()

    text = crawl_site("https://danskkaffe.dk/", fetch_site=site.fetch,
                      max_pages=3, max_chars=1000, cache_dir=str(tmp_path))

    assert text == "Dansk Kaffe roasts coffee.\n\nWe supply offices.\n\nBeans and machines."


def test_the_page_count_is_capped(tmp_path):
    site = _coffee()

    text = crawl_site("https://danskkaffe.dk/", fetch_site=site.fetch,
                      max_pages=1, max_chars=1000, cache_dir=str(tmp_path))

    assert "Beans" not in text


def test_the_text_is_capped(tmp_path):
    site = _coffee()

    text = crawl_site("https://danskkaffe.dk/", fetch_site=site.fetch,
                      max_pages=3, max_chars=11, cache_dir=str(tmp_path))

    assert text == "Dansk Kaffe"


def test_a_cached_site_is_not_fetched_again(tmp_path):
    site = _coffee()
    crawl_site("https://danskkaffe.dk/", fetch_site=site.fetch, cache_dir=str(tmp_path))

    again = crawl_site("https://danskkaffe.dk/", fetch_site=site.fetch, cache_dir=str(tmp_path))

    assert site.fetched == ["https://danskkaffe.dk/"]
    assert again.startswith("Dansk Kaffe roasts coffee.")


def test_a_site_that_yields_nothing_is_empty_and_tried_again(tmp_path):
    fetched: list[str] = []

    def disallowed(root: str, pick: PagePicker) -> list[str]:
        fetched.append(root)
        return []

    first = crawl_site("https://danskkaffe.dk/", fetch_site=disallowed, cache_dir=str(tmp_path))
    crawl_site("https://danskkaffe.dk/", fetch_site=disallowed, cache_dir=str(tmp_path))

    assert first == ""
    assert len(fetched) == 2
