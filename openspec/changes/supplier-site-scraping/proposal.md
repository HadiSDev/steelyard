## Why

A supplier's description is written today from DuckDuckGo result snippets: a few lines of text about whatever the search returned, which is often a directory listing, a namesake, or a news item rather than the supplier itself. The description is what the categorizer reads to decide what a line bought, so a vague or wrong one costs accuracy on every line from that supplier. The supplier's own website says what it sells far more reliably, and we never read it.

## What Changes

- Enrichment finds the supplier's **own website** from the search results, choosing a result whose domain matches the supplier's name and skipping directories, registries and social networks.
- It crawls that site with **Crawl4AI**: the home page plus up to a few same-site pages about the company, its products or its services, as clean Markdown, respecting `robots.txt`.
- The LLM writes the description from the site's text, and confirms the site belongs to the supplier; a site that does not is discarded.
- When no site is found, the crawl fails or the site is not the supplier's, enrichment falls back to today's snippet summary, so no supplier ends up worse described than it is now.
- The website found is stored on the supplier as `Vendor.website` (new nullable column) and returned by the vendor APIs. A website someone has already set is never overwritten.
- Crawling is governed by its own flag, off by default, on top of the existing enrichment flag, so the stage still runs without a browser installed.
- New dependency: `crawl4ai` in ai-api, which needs a Chromium download on the machine that runs enrichment.

## Capabilities

### New Capabilities
- `supplier-site-crawl`: finding a supplier's own website, crawling it within fixed limits, and turning its pages into text for the description.

### Modified Capabilities
- `supplier-enrichment`: the description is written from the supplier's own website when one is found, falling back to search snippets; the website is stored on the vendor and never overwrites one already set; crawling has its own opt-in flag.

## Impact

- **ai-api**: a new `enrichment/site/` package (discovery, crawl, fetch) and `enrichment/supplier_profile.py`, which replaces `web_context.get_supplier_context` and reuses its snippet summary as the fallback; `describe_vendors` stores a website as well as a description; new config values; tests.
- **web-api**: `Vendor.website` column with migration `0013`; `website` added to `VendorRead` and `VendorOverviewRead`.
- **Dependencies**: `crawl4ai` added to `apps/ai-api/pyproject.toml`. Installing it and its browser (`uv sync`, then `crawl4ai-setup`) is left to whoever runs enrichment.
- **Not in scope**: showing the website on the Suppliers page. That page's spec is still in the unarchived `suppliers-page` change; the link can follow once it is archived.
