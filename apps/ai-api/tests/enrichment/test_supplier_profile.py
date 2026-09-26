"""Describing a supplier: from its own site when it can be found and read, from search snippets otherwise."""
from __future__ import annotations

import json

import pytest

from ai_api.enrichment.supplier_profile import (
    SupplierProfile,
    describe_supplier,
    search_supplier,
    site_description,
)

RESULTS = [
    {"title": "Dansk Kaffe ApS - Proff", "body": "Dansk Kaffe ApS, CVR 123.", "href": "https://www.proff.dk/firma/123"},
    {"title": "Om os", "body": "Kaffe til kontoret.", "href": "https://danskkaffe.dk/om-os"},
]


class _Calls:
    def __init__(self) -> None:
        self.crawled: list[str] = []
        self.snippets: list[str] = []
        self.searched: list[str] = []

    def search(self, query: str) -> list[dict]:
        self.searched.append(query)
        return RESULTS

    def crawl(self, root: str) -> str:
        self.crawled.append(root)
        return "Dansk Kaffe roasts coffee for offices."

    def snippet_summary(self, name: str, snippets: str) -> str:
        self.snippets.append(snippets)
        return "A Danish coffee supplier (from snippets)."


def _describe(calls: _Calls, tmp_path, *, site_answer: str, crawl=None, crawling: bool = True):
    crawl_fn = (crawl or calls.crawl) if crawling else None
    return describe_supplier(
        "Dansk Kaffe ApS", "DK",
        search_fn=calls.search,
        crawl_fn=crawl_fn,
        summarize_site_fn=lambda name, country, text: site_description(site_answer),
        summarize_snippets_fn=calls.snippet_summary,
        cache_dir=str(tmp_path),
    )


def _answer(is_site: bool, description: str) -> str:
    return json.dumps({"is_supplier_site": is_site, "description": description})


def test_the_own_site_describes_the_supplier_and_is_kept(tmp_path):
    calls = _Calls()

    profile = _describe(calls, tmp_path, site_answer=_answer(True, "Roasts coffee for offices."))

    assert profile == SupplierProfile("Roasts coffee for offices.", "https://danskkaffe.dk/")
    assert calls.crawled == ["https://danskkaffe.dk/"]
    assert calls.snippets == []


def test_someone_elses_site_falls_back_to_the_snippets(tmp_path):
    calls = _Calls()

    profile = _describe(calls, tmp_path, site_answer=_answer(False, ""))

    assert profile == SupplierProfile("A Danish coffee supplier (from snippets).", None)


def test_an_unreadable_answer_falls_back_to_the_snippets(tmp_path):
    calls = _Calls()

    profile = _describe(calls, tmp_path, site_answer="I think it is a coffee company")

    assert profile.website is None
    assert profile.description == "A Danish coffee supplier (from snippets)."


def test_a_failed_crawl_falls_back_to_the_snippets(tmp_path):
    calls = _Calls()

    def timeout(root: str) -> str:
        raise TimeoutError(root)

    profile = _describe(calls, tmp_path, site_answer=_answer(True, "unused"), crawl=timeout)

    assert profile == SupplierProfile("A Danish coffee supplier (from snippets).", None)


def test_an_empty_crawl_falls_back_to_the_snippets(tmp_path):
    calls = _Calls()

    profile = _describe(calls, tmp_path, site_answer=_answer(True, "unused"), crawl=lambda root: "")

    assert profile.website is None


def test_crawling_off_never_crawls(tmp_path):
    calls = _Calls()

    profile = _describe(calls, tmp_path, site_answer=_answer(True, "unused"), crawling=False)

    assert calls.crawled == []
    assert profile == SupplierProfile("A Danish coffee supplier (from snippets).", None)


def test_the_snippets_summarized_are_the_search_results(tmp_path):
    calls = _Calls()

    _describe(calls, tmp_path, site_answer=_answer(False, ""))

    assert calls.snippets == ["Dansk Kaffe ApS, CVR 123. | Kaffe til kontoret."]


def test_the_search_is_cached_with_its_links(tmp_path):
    calls = _Calls()

    first = search_supplier("Dansk Kaffe ApS", "DK", search_fn=calls.search, cache_dir=str(tmp_path))
    second = search_supplier("Dansk Kaffe ApS", "DK", search_fn=calls.search, cache_dir=str(tmp_path))

    assert first == second == RESULTS
    assert calls.searched == ["Dansk Kaffe ApS DK company what they sell"]


@pytest.mark.parametrize("reply, expected", [
    ('{"is_supplier_site": true, "description": " Roasts coffee. "}', "Roasts coffee."),
    ('```json\n{"is_supplier_site": true, "description": "Roasts coffee."}\n```', "Roasts coffee."),
    ('{"is_supplier_site": false, "description": "Roasts coffee."}', ""),
    ('{"is_supplier_site": "yes", "description": "Roasts coffee."}', ""),
    ('{"is_supplier_site": true, "description": 7}', ""),
    ("not json at all", ""),
    ('["a list"]', ""),
])
def test_the_site_answer_is_read_strictly(reply, expected):
    assert site_description(reply) == expected
