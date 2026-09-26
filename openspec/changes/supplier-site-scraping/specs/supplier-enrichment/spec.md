## ADDED Requirements

### Requirement: A supplier's description SHALL come from its own website first, and from search snippets otherwise

When site crawling is enabled, enrichment SHALL first try to describe a supplier from its own website (see `supplier-site-crawl`). When no website is found, the site cannot be crawled, or the site yields no description, enrichment SHALL describe the supplier from the web search snippets as it did before this change. A supplier SHALL never be left undescribed by the crawl when the snippets alone would have described it.

#### Scenario: The site is used when there is one

- **WHEN** the supplier's own site is found and yields a description
- **THEN** that description is stored and the snippets are not summarized

#### Scenario: The snippets are used when the site fails

- **WHEN** the supplier's site times out
- **THEN** the description is written from the search snippets, and no website is stored

#### Scenario: Crawling off leaves today's behaviour

- **WHEN** enrichment is enabled and site crawling is not
- **THEN** no site is crawled and the description is written from the search snippets

### Requirement: The supplier's website SHALL be stored on the vendor and SHALL NOT overwrite one already set

`Vendor` SHALL carry a nullable `website`. When a supplier is described from its own site, that site's root SHALL be stored as its website, unless the vendor already has a website, which SHALL be left as it is. The website SHALL be returned wherever a vendor is read through the web API (`VendorRead` and `VendorOverviewRead`).

#### Scenario: The website found is stored

- **WHEN** a supplier with no website is described from `https://danskkaffe.dk/`
- **THEN** its website is `https://danskkaffe.dk/`

#### Scenario: A website already set stands

- **WHEN** a supplier's website is already set and enrichment finds a different one
- **THEN** the stored website is unchanged

#### Scenario: The website is readable through the API

- **WHEN** a client lists suppliers
- **THEN** each supplier carries its `website`, null when none is known

### Requirement: A website the supplier's invoices state SHALL be crawled before any is searched for

A supplier's known website is the one set on it, else the one its invoices' documents print most often among those whose domain names the supplier: by the same name match that picks a site from search results, or, since the supplier printed it, by a domain label that is any word of the name (of at least two letters, legal forms dropped) or begins with the name's first word. A printed website whose domain does not name the supplier, such as a deposit guarantee scheme in a bank's footer, SHALL NOT be a known website. When a supplier has a known website, enrichment SHALL crawl that site directly, without looking for one among the search results, and SHALL keep it as the supplier's website whether or not the site yields the description. Only when no website is known SHALL enrichment search for the supplier's name to find one.

#### Scenario: The invoices print the website

- **WHEN** a supplier's invoices print `https://danskkaffe.dk/` and crawling is enabled
- **THEN** that site is crawled, no search is made to find a site, and the supplier's website is `https://danskkaffe.dk/`

#### Scenario: The printed site does not describe the supplier

- **WHEN** the known website cannot be read
- **THEN** the description is written from the search snippets and the known website is still stored

#### Scenario: A printed address that is not the supplier's

- **WHEN** a bank's invoices print only `https://www.iidraudimas.lt/`, its deposit guarantee scheme
- **THEN** the bank has no known website, and its name is searched for one

#### Scenario: No website known

- **WHEN** neither the supplier nor its invoices state a website
- **THEN** the supplier's name is searched and its site looked for among the results

## MODIFIED Requirements

### Requirement: Enrichment SHALL be opt-in, and its absence SHALL degrade nothing

Supplier enrichment makes outbound requests to the public web and SHALL therefore be governed by an environment flag, defaulting to **off**, so tests and offline runs make no outbound request. This follows the rule `FX_ENABLED` already sets.

Crawling a supplier's website additionally needs a headless browser, and SHALL be governed by a second environment flag, also defaulting to **off**, that has effect only when enrichment is enabled. With crawling off, enrichment SHALL behave exactly as it does from search snippets alone, and SHALL NOT require the browser or the crawling library to be installed.

With enrichment off, or with a lookup that fails or returns nothing, the supplier's description SHALL remain null and categorization SHALL proceed on the facts that exist. A failure to describe a supplier, including a failure to start the browser, SHALL never fail a line, an invoice, or a sync.

#### Scenario: Off by default

- **WHEN** the enrichment flag is unset
- **THEN** no outbound request is made and every vendor description stays as stored

#### Scenario: Crawling off by default

- **WHEN** the enrichment flag is set and the crawling flag is unset
- **THEN** no browser is started and no supplier website is fetched

#### Scenario: A failed lookup is not a failed line

- **WHEN** a supplier lookup times out
- **THEN** the vendor's description stays null, the line is still categorized, and the sync still completes

#### Scenario: A browser that will not start is not a failed run

- **WHEN** crawling is enabled but the browser cannot be launched
- **THEN** each supplier is described from its search snippets and the enrichment run completes

### Requirement: A described supplier SHALL be able to get a website without being described again

The enrichment CLI SHALL accept `--websites`, which, instead of describing suppliers, stores a website for each described supplier that has none, leaving its description untouched. The website SHALL be its known website when it has one; otherwise one found for its name among the search results, kept only when crawling it confirms it is the supplier's own site. With crawling off, only a known website SHALL be stored.

#### Scenario: A described supplier gets its website

- **WHEN** `--websites` runs with crawling on for a described supplier with no website whose site is found and confirmed
- **THEN** its website is stored and its description is unchanged

#### Scenario: Nothing confirmed

- **WHEN** no site is found for the supplier, or its site says it belongs to someone else
- **THEN** no website is stored
