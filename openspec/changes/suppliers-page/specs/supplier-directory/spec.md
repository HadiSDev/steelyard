## ADDED Requirements

### Requirement: The supplier overview SHALL list only the organization's own suppliers

`GET /api/v1/vendors/overview` SHALL return the suppliers named by at least one invoice of the caller's companies, and no other. The `vendors` table is a global catalog shared by every tenant, so a supplier SHALL appear only through the caller's own invoices, and its figures SHALL be computed from those invoices alone. A `company_id` parameter SHALL narrow the list and the figures to one of the caller's companies; a company outside the caller's organization SHALL be refused as the existing tenant-scoped endpoints refuse it.

#### Scenario: A supplier only another tenant buys from is not listed

- **WHEN** a supplier appears only on invoices of another organization
- **THEN** it is absent from the caller's overview

#### Scenario: A shared supplier carries only the caller's figures

- **WHEN** two organizations both buy from the same supplier
- **THEN** each sees that supplier once, with the invoice count and spend of its own invoices only

#### Scenario: The company filter narrows list and figures

- **WHEN** the caller passes the id of one of their companies
- **THEN** only suppliers on that company's invoices are listed, and their figures count only that company's invoices

### Requirement: Each supplier row SHALL carry its identity and its figures

Each row SHALL carry the supplier's id, name, country code, VAT number and stored description, together with:

- `invoice_count`: the number of the caller's invoices naming the supplier;
- `last_invoice_date`: the latest invoice date among them, or null when none is dated;
- `spend`: one entry per base currency, each with the net-of-VAT amount (`base_total − base_tax`) of those invoices in that currency and the number of invoices left out for lacking a base amount.

Amounts in different currencies SHALL never be summed together.

#### Scenario: Spend is net of VAT in the base currency

- **WHEN** a supplier sent two DKK-based invoices of 1,250.00 with 250.00 VAT and 500.00 with no VAT
- **THEN** its row states spend of 1,500.00 in DKK and an invoice count of 2

#### Scenario: An unconverted invoice is counted, not summed

- **WHEN** one of a supplier's invoices has no base amount
- **THEN** the invoice is included in `invoice_count` and reported as left out of spend, and adds nothing to the amount

#### Scenario: Two base currencies stay apart

- **WHEN** a supplier sold to a DKK-based company and a EUR-based company of the same organization
- **THEN** the row's spend has one DKK entry and one EUR entry

### Requirement: The overview SHALL be searchable, sortable and paged

The endpoint SHALL accept `q` (a case-insensitive substring of the name or the VAT number), `sort` (one of `name`, `spend`, `invoice_count`, `last_invoice_date`), `order` (`asc` or `desc`), `page` and `page_size` (at most 100), and SHALL return the standard `Page` envelope with the total number of matching suppliers. Ties SHALL be broken by name and then id, so paging is stable. Sorting by `spend` SHALL be accepted only when every listed company shares one base currency; otherwise the endpoint SHALL answer 422 naming the reason, rather than order amounts across currencies.

#### Scenario: Search matches a VAT number

- **WHEN** the caller searches for part of a supplier's VAT number
- **THEN** that supplier is listed and suppliers matching neither name nor VAT number are not

#### Scenario: Largest suppliers first

- **WHEN** the caller sorts by spend descending
- **THEN** rows arrive in descending order of their base-currency spend

#### Scenario: Spend order is refused across currencies

- **WHEN** the listed companies have different base currencies and the caller sorts by spend
- **THEN** the response is 422 and no rows are returned

#### Scenario: Paging is stable

- **WHEN** several suppliers have equal spend
- **THEN** they are ordered by name, and each appears on exactly one page
