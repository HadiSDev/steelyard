"""Describing a supplier: from its own site when it can be found and read, from search snippets otherwise."""
from __future__ import annotations

import json

import pytest

from ai_api import config
from ai_api.enrichment.supplier_profile import (
    SupplierProfile,
    describe_supplier,
    search_supplier,
    site_description,
    summarize_site,
)
from ai_api.web_context import summarize_supplier

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


def _describe_stated(calls: _Calls, tmp_path, *, site_answer: str, crawl=None, crawling: bool = True):
    return describe_supplier(
        "Dansk Kaffe ApS", "DK", "https://www.danskkaffe.dk/",
        search_fn=calls.search,
        crawl_fn=(crawl or calls.crawl) if crawling else None,
        summarize_site_fn=lambda name, country, text: site_description(site_answer),
        summarize_snippets_fn=calls.snippet_summary,
        cache_dir=str(tmp_path),
    )


def test_a_stated_website_is_crawled_without_searching(tmp_path):
    calls = _Calls()

    profile = _describe_stated(calls, tmp_path, site_answer=_answer(True, "Roasts coffee."))

    assert profile == SupplierProfile("Roasts coffee.", "https://www.danskkaffe.dk/")
    assert calls.crawled == ["https://www.danskkaffe.dk/"]
    assert calls.searched == []


def test_a_stated_website_is_kept_when_its_site_cannot_describe_the_supplier(tmp_path):
    calls = _Calls()

    profile = _describe_stated(calls, tmp_path, site_answer=_answer(True, "unused"), crawl=lambda root: "")

    assert profile == SupplierProfile(
        "A Danish coffee supplier (from snippets).", "https://www.danskkaffe.dk/",
    )
    assert len(calls.searched) == 1


def test_a_stated_website_is_kept_when_crawling_is_off(tmp_path):
    calls = _Calls()

    profile = _describe_stated(calls, tmp_path, site_answer=_answer(True, "unused"), crawling=False)

    assert calls.crawled == []
    assert profile.website == "https://www.danskkaffe.dk/"


def test_without_a_stated_website_the_name_is_searched_for_one(tmp_path):
    calls = _Calls()

    profile = _describe(calls, tmp_path, site_answer=_answer(True, "Roasts coffee."))

    assert len(calls.searched) == 1
    assert calls.crawled == ["https://danskkaffe.dk/"]
    assert profile.website == "https://danskkaffe.dk/"


class _RecordingLlm:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def call(self, messages: list[dict]) -> str:
        self.prompts.append(messages[0]["content"])
        return self.reply


def test_the_site_is_described_in_english_and_a_product_site_does_not_count(monkeypatch):
    llm = _RecordingLlm(_answer(True, "Runs trains."))
    monkeypatch.setattr(config, "get_llm", lambda: llm)

    assert summarize_site("DSB", "DK", "DSB kører tog i Danmark.") == "Runs trains."
    assert "in English" in llm.prompts[0]
    assert "one of its products or services" in llm.prompts[0]


def test_the_snippets_are_described_in_english(monkeypatch):
    llm = _RecordingLlm("Runs trains in Denmark.")
    monkeypatch.setattr(config, "get_llm", lambda: llm)

    assert summarize_supplier("DSB", "DSB er et jernbaneselskab.") == "Runs trains in Denmark."
    assert "in English" in llm.prompts[0]
