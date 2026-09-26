"""What a supplier sells, from its own website when that can be found and read, from search snippets otherwise."""
from __future__ import annotations

import json
import logging
from typing import Callable, NamedTuple

import json_repair

from .. import config
from ..web_context import ddg_search, read_cache, summarize_supplier, write_cache
from .site.discovery import find_website

logger = logging.getLogger("ai_api.enrichment")


class SupplierProfile(NamedTuple):
    description: str
    website: str | None


def describe_supplier(
    name: str,
    country_code: str | None = None,
    *,
    search_fn: Callable[[str], list[dict]] = ddg_search,
    crawl_fn: Callable[[str], str] | None = None,
    summarize_site_fn: Callable[[str, str | None, str], str] | None = None,
    summarize_snippets_fn: Callable[[str, str], str] = summarize_supplier,
    cache_dir: str | None = None,
) -> SupplierProfile:
    """The supplier's description, and its website when the description came from it."""
    if not (name or "").strip():
        return SupplierProfile("", None)
    if summarize_site_fn is None:
        summarize_site_fn = summarize_site

    results = search_supplier(name, country_code, search_fn=search_fn, cache_dir=cache_dir)

    if crawl_fn is not None:
        website = find_website(name, results)
        if website is not None:
            description = _describe_from_site(name, country_code, website, crawl_fn, summarize_site_fn)
            if description:
                return SupplierProfile(description, website)

    snippets = " | ".join(result.get("body", "") for result in results if result.get("body"))
    return SupplierProfile(summarize_snippets_fn(name, snippets), None)


def search_supplier(
    name: str,
    country_code: str | None,
    *,
    search_fn: Callable[[str], list[dict]],
    cache_dir: str | None = None,
) -> list[dict]:
    """The web search results for the supplier, with their links, cached by query."""
    cache_dir = config.WEB_CONTEXT_CACHE_DIR if cache_dir is None else cache_dir
    query = " ".join(part for part in (name, country_code, "company what they sell") if part)
    key = f"supplier-results-{query}"
    cached = read_cache(cache_dir, key)
    if cached is not None:
        return json.loads(cached)
    results = search_fn(query)
    write_cache(cache_dir, key, json.dumps(results))
    return results


def summarize_site(name: str, country_code: str | None, text: str) -> str:
    """Ask the LLM whether the text is the supplier's own site and, if so, what the supplier sells."""
    where = f" (based in {country_code})" if country_code else ""
    prompt = (
        f"Below is text from a website. Decide whether it is the own website of the "
        f"company '{name}'{where}. If it is, state in one or two sentences what the "
        "company sells or does: its industry and its main products or services. "
        "Write nothing about any customer of theirs.\n\n"
        "Reply with only a JSON object and nothing else:\n"
        '{"is_supplier_site": true or false, "description": "..."}\n'
        'When it is not the company\'s own website, use an empty description.\n\n'
        f"{text[:config.SUPPLIER_CRAWL_MAX_CHARS]}"
    )
    try:
        reply = config.get_llm().call(messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not summarize the site of %s: %s", name, exc)
        return ""
    return site_description(reply or "")


def site_description(reply: str) -> str:
    """The description in the LLM's answer, or empty when the site is not the supplier's or the answer is unreadable."""
    answer = json_repair.loads(reply)
    if not isinstance(answer, dict):
        return ""
    if answer.get("is_supplier_site") is not True:
        return ""
    description = answer.get("description")
    if not isinstance(description, str):
        return ""
    return description.strip()


def _describe_from_site(
    name: str,
    country_code: str | None,
    website: str,
    crawl_fn: Callable[[str], str],
    summarize_site_fn: Callable[[str, str | None, str], str],
) -> str:
    try:
        text = crawl_fn(website)
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not crawl %s for %s: %s", website, name, exc)
        return ""
    if not text.strip():
        return ""
    return summarize_site_fn(name, country_code, text)
