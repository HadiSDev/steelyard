## Context

Enrichment is a CLI stage (`python -m ai_api.enrichment.runner`) behind `VENDOR_ENRICHMENT_ENABLED`. `describe_vendors` walks the vendors with no description and calls a `describe(name, country_code) -> str` callable, by default `web_context.get_supplier_context`: a DuckDuckGo text search for the name, whose result snippets are cached on disk and summarized by the LLM into one or two sentences. The search results also carry each hit's URL (`href`), which is thrown away today.

`Vendor` is a global catalog shared by every tenant; `description_source` records whether a description came from the web or a human. The run is synchronous, over at most a few hundred suppliers, each described once.

## Goals / Non-Goals

**Goals:**
- Describe a supplier from its own website when one can be found, with today's snippet summary as the fallback.
- Store the website found on the vendor and expose it through the vendor APIs.
- Keep the stage runnable with no browser installed, and keep tests offline.

**Non-Goals:**
- Showing the website on the Suppliers page (follows once `suppliers-page` is archived).
- Any other scraped fields (industry, logo, contact details, address).
- Re-describing suppliers that already have a description, or refreshing stale ones.
- Running enrichment from the worker or on a schedule.

## Decisions

### Crawl4AI over Lightpanda
Crawl4AI is a Python library that returns boilerplate-free Markdown and in-page links, which is what the LLM step needs, and it drives real Chromium, so JavaScript-built small-business sites render. Lightpanda would be a separate service driven through CDP, with its own extraction left to us, and it trades compatibility for a speed that a once-per-supplier run of a few hundred does not need. Its AGPL licence is a further cost.

### Three small modules under `enrichment/`, one job each
- `site_discovery.py`: picks the website from search results (pure functions: name normalization, domain matching, the blocked-host list). No I/O, so it is tested exhaustively.
- `site_crawler.py`: the only module importing `crawl4ai`. Given a root URL, returns the page texts, cached by host. `crawl4ai` is a declared dependency, so importing it is always safe; what may be missing is the Chromium binary, which is only touched when a crawl starts.
- `supplier_profile.py`: composes search → discovery → crawl → LLM → fallback into a `SupplierProfile(description, website)` NamedTuple. It takes the crawl function as a parameter; with crawling off it is given none and goes straight to the snippets.

`describe_vendors`' callable changes from returning `str` to returning `SupplierProfile`. Its existing tests adapt; the stubs stay injectable, so no test starts a browser or reaches the network.

### Search once, reuse its results for both paths
The site path and the snippet fallback read the same search results, so a supplier costs one search. The search cache changes from storing joined snippet text to storing the result list as JSON, so the URLs survive; old `supplier-*` cache files are ignored by using a new key prefix (`supplier-results-`).

### Domain matching, not LLM site picking
The website is picked by comparing the supplier's normalized name with each result's registrable domain label, after a blocked-host list (registries such as `proff.dk`, `cvrapi.dk`, `virk.dk`; `linkedin.com`, `facebook.com`, `instagram.com`; `wikipedia.org`; marketplaces). This is deterministic and testable, and the LLM then confirms ownership from the page text. The alternative, asking the LLM to choose among results, costs a call per supplier and is harder to test.

### Which pages to crawl
The home page first, then up to `SUPPLIER_CRAWL_MAX_PAGES` (default 3) same-host links scored by path keywords (about/om-os/company/virksomhed, products/produkter, services/ydelser, solutions/løsninger). Each page uses Crawl4AI's pruning content filter for "fit" Markdown, `check_robots_txt=True`, and a page timeout (`SUPPLIER_CRAWL_TIMEOUT_S`, default 20). The joined text is capped at about 8,000 characters before it reaches the LLM. The crawl runs in `asyncio.run` from the synchronous stage, one supplier at a time.

### JSON from the prompt, not guided decoding
The LLM is asked for `{"is_supplier_site": bool, "description": str}` and the reply is parsed with `json_repair` (already a dependency). Guided decoding is avoided because it has caused runaway timeouts with the local vLLM.

### A separate crawl flag
`SUPPLIER_CRAWL_ENABLED` (default off) sits under `VENDOR_ENRICHMENT_ENABLED`, because crawling adds a browser dependency the snippet path does not have. A crawler that fails to start is logged once and the run continues on snippets alone.

### Website column
`Vendor.website: str | None`, migration `0013_vendor_website`. It is written only when the vendor has none, in the same guarded write as the description.

## Risks / Trade-offs

- [A supplier's name does not appear in its domain (e.g. an acronym domain)] → No website is found and the snippet fallback describes it; nothing is worse than today.
- [The domain match picks a namesake's site] → The LLM's ownership check rejects it; the website is stored only when the site produced the description.
- [Chromium is heavy and may be missing where enrichment runs] → Crawling is opt-in and a launch failure degrades to snippets.
- [Sites behind cookie walls or bot protection yield little text] → An empty or thin crawl counts as no site and falls back.
- [Scraping etiquette] → `robots.txt` is honoured, pages per site are capped, each site is fetched once and cached, and requests are sequential.

## Migration Plan

1. Merge; run migration `0013` (adds a nullable column, no backfill).
2. Whoever runs enrichment installs dependencies (`uv sync`) and the browser (`crawl4ai-setup`), then sets `SUPPLIER_CRAWL_ENABLED`.
3. Suppliers described before this change keep their descriptions. To re-describe one, clear its description.

Rollback: unset `SUPPLIER_CRAWL_ENABLED`; the migration's downgrade drops the column.

## Open Questions

- Whether suppliers already described from snippets should be re-described once from their sites. This change leaves them alone.
