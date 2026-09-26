## ADDED Requirements

### Requirement: Extraction SHALL read the supplier's website the document prints

Both extraction paths, from a document's text and from its page images, SHALL read the supplier's own website when the document prints one, such as in its header, footer or beside the supplier's address. The buyer's website, a payment portal, an email address, and an address printed in a legal or regulatory note (a deposit guarantee scheme, a financial regulator, a complaints body, a parent group) SHALL NOT be read as the supplier's website. On a document of several pages, the first page that prints a website states it.

The website read SHALL be reduced to the root of its site (`scheme://host/`, `https` when the document prints no scheme) and stored on the invoice as `document_supplier_website`, beside the invoice's other document readings. A value that names no site, such as an email address or a bare name, SHALL be stored as none.

#### Scenario: A website printed in the footer

- **WHEN** a document's footer prints `DanskKaffe.dk/kontakt`
- **THEN** the invoice's `document_supplier_website` is `https://danskkaffe.dk/`

#### Scenario: Only an email address

- **WHEN** the document prints `info@danskkaffe.dk` and no website
- **THEN** the invoice's `document_supplier_website` is none

### Requirement: Documents SHALL be readable again in bulk from the command line

The document-processing CLI SHALL accept `--reprocess`, which first puts the selected invoices whose documents were already read or failed back in the queue, exactly as the API's reprocess does (pending, error cleared, attempts reset, audited as `reprocess_document`), and then reads them in the same run. It SHALL honour `--company-id`, `--invoice-id` and `--limit`, and SHALL leave alone documents being read, absent, or already waiting. Without `--reprocess`, a document already read SHALL NOT be read again.

#### Scenario: Reading a company's documents again

- **WHEN** the CLI runs with `--reprocess --company-id <id>`
- **THEN** that company's read and failed documents are read again, and other companies' are untouched

#### Scenario: A document being read is left alone

- **WHEN** an invoice's document is being read and the CLI runs with `--reprocess`
- **THEN** that invoice is not put back in the queue

### Requirement: Extraction SHALL keep the supplier country and VAT number the document prints

Extraction SHALL store the supplier's country and VAT number as the document prints them on the invoice, as `document_supplier_country_code` (a two-letter code, upper case, or none when what was read is not one) and `document_supplier_vat_number` (in its international form, with the country prefix), beside the ERP's facts about the supplier, which they never overwrite.

#### Scenario: A Lithuanian bank's statement

- **WHEN** a document prints the supplier's country as `lt` and its VAT number as `100 011 747 16`
- **THEN** the invoice's `document_supplier_country_code` is `LT` and its `document_supplier_vat_number` is `LT10001174716`
