## ADDED Requirements

### Requirement: Extraction SHALL read the supplier's website the document prints

Both extraction paths, from a document's text and from its page images, SHALL read the supplier's own website when the document prints one, such as in its header, footer or beside the supplier's address. The buyer's website, a payment portal and an email address SHALL NOT be read as the supplier's website. On a document of several pages, the first page that prints a website states it.

The website read SHALL be reduced to the root of its site (`scheme://host/`, `https` when the document prints no scheme) and stored on the invoice as `document_supplier_website`, beside the invoice's other document readings. A value that names no site, such as an email address or a bare name, SHALL be stored as none.

#### Scenario: A website printed in the footer

- **WHEN** a document's footer prints `DanskKaffe.dk/kontakt`
- **THEN** the invoice's `document_supplier_website` is `https://danskkaffe.dk/`

#### Scenario: Only an email address

- **WHEN** the document prints `info@danskkaffe.dk` and no website
- **THEN** the invoice's `document_supplier_website` is none
