## ADDED Requirements

### Requirement: The supplier's own website SHALL be found from search results by its domain

Enrichment SHALL choose the supplier's website from the web search results for its name, taking the first result whose host names the supplier. The name is lowercased, Danish letters are spelled as domains spell them (æ→ae, ø→oe, å→aa), punctuation and legal-form words (such as "A/S", "ApS", "GmbH", "Ltd", "Limited", "Inc", "AB", "BV") are dropped, and its words are joined cumulatively ("Dansk Kaffe ApS" gives `dansk` and `danskkaffe`), keeping keys of at least three characters. A host names the supplier when one of its labels other than the top-level domain, with hyphens removed, equals one of those keys or contains the full joined name.

Results on directories, company registries, social networks, marketplaces and encyclopedias SHALL never be chosen, whatever their domain says. The website stored SHALL be the site's root (`https://<host>/`), not the page the search returned.

#### Scenario: The supplier's own domain is chosen over a directory

- **WHEN** the results for "Dansk Kaffe ApS" are a `proff.dk` listing, then `danskkaffe.dk/om-os`
- **THEN** the website found is `https://danskkaffe.dk/`

#### Scenario: A namesake's domain is not taken for the supplier

- **WHEN** no result's domain contains the supplier's distinctive name
- **THEN** no website is found and the site is not crawled

#### Scenario: A social profile is never the website

- **WHEN** the only matching result is `linkedin.com/company/dansk-kaffe`
- **THEN** no website is found

### Requirement: A supplier's site SHALL be crawled within fixed limits

The crawl SHALL fetch the site's home page and at most a configured number of further pages on the same host (default 3), preferring links whose path names the company, its products or its services, in English or Danish (such as `about`, `om-os`, `products`, `produkter`, `services`, `ydelser`). Each page SHALL have a timeout, the crawl SHALL honour `robots.txt`, and it SHALL never follow a link to another host.

Each page's text SHALL be taken as Markdown with navigation, footers and other boilerplate removed, and the text passed on SHALL be capped in length.

#### Scenario: The crawl stays small

- **WHEN** a home page links to forty same-site pages, two of them `/om-os` and `/produkter`
- **THEN** the crawl fetches the home page, `/om-os` and `/produkter`, and at most the configured number of further pages in total

#### Scenario: A site that forbids crawling is not crawled

- **WHEN** the site's `robots.txt` disallows the pages
- **THEN** no page text is returned and enrichment falls back as it would for an unreachable site

#### Scenario: A link off the site is not followed

- **WHEN** the home page links to `facebook.com/danskkaffe`
- **THEN** that page is not fetched

### Requirement: A crawled site SHALL be cached by its host

The crawled text of a site SHALL be cached under the web-context cache directory, keyed by its host, so enriching again or enriching another supplier on the same site makes no request to it.

#### Scenario: A cached site is not fetched again

- **WHEN** a site's text is already cached and it is looked up again
- **THEN** the cached text is used and no request is made to the site

### Requirement: The description SHALL be written from the site only when the site is the supplier's

The LLM SHALL be given the supplier's name and country and the crawled text, and SHALL answer with a JSON object stating whether the site belongs to that supplier and, if it does, one or two sentences on what the supplier sells: its industry and its main products or services. The answer SHALL be requested in the prompt and parsed, not enforced through guided decoding.

A site the LLM says is not the supplier's, or an answer that cannot be parsed, SHALL yield neither a description nor a website.

#### Scenario: The supplier's own site describes it

- **WHEN** the crawled text is the supplier's site and states it roasts and sells coffee to offices
- **THEN** the description says it is a coffee roaster supplying offices, and the website is kept

#### Scenario: Someone else's site is discarded

- **WHEN** the LLM answers that the site belongs to another company
- **THEN** neither the description nor the website from it is used

#### Scenario: An unreadable answer is not a description

- **WHEN** the LLM's answer is not valid JSON
- **THEN** the site yields no description and enrichment falls back to the search snippets

### Requirement: A description SHALL be written in English, and a product's site SHALL NOT count as the supplier's

A supplier's description SHALL be written in English whatever the language of the site or snippets it is written from. When deciding whether a crawled site is the supplier's own, a site for one of the supplier's products or services rather than for the company itself SHALL NOT count.

#### Scenario: A Danish site

- **WHEN** the supplier's site is in Danish
- **THEN** its description is written in English

#### Scenario: A product's site

- **WHEN** the crawled site is `ai.studio`, a product of Google Cloud EMEA Limited
- **THEN** it is not taken as the supplier's website
