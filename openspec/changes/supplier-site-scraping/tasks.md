## 1. Vendor website (web-api)

- [x] 1.1 Add `Vendor.website: str | None` and migration `0013_vendor_website` (upgrade adds the nullable column, downgrade drops it)
- [x] 1.2 Add `website` to `VendorRead` and `VendorOverviewRead`; extend the vendor and vendor-overview API tests to assert it is returned, null when unset
- [x] 1.3 Add `website` to the web app's `VendorRead` type

## 2. Configuration and dependency (ai-api)

- [x] 2.1 Add `crawl4ai` to `apps/ai-api/pyproject.toml` (the install is left to the user)
- [x] 2.2 Add `SUPPLIER_CRAWL_ENABLED` (default off), `SUPPLIER_CRAWL_MAX_PAGES` (default 3), `SUPPLIER_CRAWL_TIMEOUT_S` (default 20) and a text cap to `config.py`, with config tests for the defaults

## 3. Site discovery

- [x] 3.1 Write failing tests for `enrichment/site_discovery.py`: legal-form words dropped, own domain chosen over a directory, blocked hosts never chosen, namesake rejected, root URL returned
- [x] 3.2 Implement name normalization, registrable-domain matching, the blocked-host list and `find_website(name, results) -> str | None`
- [x] 3.3 Write failing tests for page selection: same-host only, keyword-scored links in English and Danish, capped at the configured count
- [x] 3.4 Implement `pages_to_crawl(root, links, limit) -> list[str]`

## 4. Site crawl

- [x] 4.1 Implement `enrichment/site_crawler.py`: crawl the home page, pick further pages with `pages_to_crawl`, fetch them with Crawl4AI (pruned Markdown, `check_robots_txt`, page timeout), join and cap the text, cache it by host
- [x] 4.2 Test the cache and the cap with the Crawl4AI fetch stubbed: a cached host makes no fetch; an empty or disallowed crawl returns no text

## 5. Supplier profile

- [x] 5.1 Store supplier search results as JSON under the `supplier-results-` cache key, keeping each hit's URL; the snippet summary reads the same results
- [x] 5.2 Write failing tests for `enrichment/supplier_profile.py`: site description used with its website; site rejected by the LLM falls back to snippets with no website; unparsable JSON falls back; crawl failure falls back; crawling off never calls the crawler
- [x] 5.3 Implement `SupplierProfile(description, website)` and `describe_supplier(name, country_code, *, search_fn, crawl_fn, summarize_site_fn, summarize_snippets_fn)`, parsing the LLM's JSON with `json_repair`

## 6. Enrichment stage

- [x] 6.1 Change `describe_vendors` to take a callable returning `SupplierProfile`, storing the website only when the vendor has none, under the same re-check as the description; update its tests and add ones for the website written and the website kept
- [x] 6.2 In the runner, pass the real crawler when `SUPPLIER_CRAWL_ENABLED` is set and none otherwise; a crawl that fails, including a browser that will not launch, is logged for that supplier and the run continues on snippets
- [x] 6.3 Document the new flags and the `crawl4ai-setup` step in `.env.example`, beside `VENDOR_ENRICHMENT_ENABLED`, and in the enrichment runner's message

## 7. Verify

- [x] 7.1 Run the ai-api and web-api test suites and tsc on the web app, with no regressions
- [ ] 7.2 With the user's go-ahead, run enrichment with crawling on for a handful of real suppliers and compare the descriptions with the snippet ones
