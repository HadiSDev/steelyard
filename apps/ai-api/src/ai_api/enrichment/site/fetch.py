"""Fetching a site's pages as pruned Markdown with Crawl4AI, one browser per site."""
from __future__ import annotations

import asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from ... import config
from .crawler import PagePicker


def fetch_site(root: str, pick: PagePicker) -> list[str]:
    """The home page's text, then the text of each page `pick` chooses from its links."""
    return asyncio.run(_fetch_site(root, pick))


async def _fetch_site(root: str, pick: PagePicker) -> list[str]:
    run = _run_config()
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        home = await crawler.arun(url=root, config=run)
        if not home.success:
            return []
        texts = [_text(home)]
        links = [link.get("href", "") for link in (home.links or {}).get("internal", [])]
        for url in pick([link for link in links if link]):
            page = await crawler.arun(url=url, config=run)
            if page.success:
                texts.append(_text(page))
    return [text for text in texts if text]


def _run_config() -> CrawlerRunConfig:
    return CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.45, threshold_type="dynamic"),
        ),
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        page_timeout=config.SUPPLIER_CRAWL_TIMEOUT_S * 1000,
        excluded_tags=["nav", "footer", "header", "form"],
        verbose=False,
    )


def _text(result) -> str:
    markdown = result.markdown
    if markdown is None:
        return ""
    return (markdown.fit_markdown or markdown.raw_markdown or "").strip()
