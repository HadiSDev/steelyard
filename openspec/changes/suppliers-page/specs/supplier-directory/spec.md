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

### Requirement: A supplier's detail SHALL be readable by the organizations that bought from it

`GET /api/v1/vendors/{vendor_id}/detail`, optionally narrowed by `company_id`, SHALL return the supplier's name, country, VAT number, description with its source, and website, together with figures over the caller's invoices only: invoice count, first and last invoice date, spend net of VAT per base currency with unconverted invoices counted, line spend grouped by category and base currency largest first, and the ten latest invoices, newest first with undated ones last. A supplier the caller has no invoice from, an unknown supplier, or a foreign `company_id` SHALL be 404.

#### Scenario: Only the caller's figures

- **WHEN** a supplier has invoices to two organizations and one of them reads its detail
- **THEN** the counts, spend, categories and invoices cover only that organization's invoices

#### Scenario: A supplier the caller never bought from

- **WHEN** the caller reads a supplier that none of its companies has an invoice from
- **THEN** the response is 404

### Requirement: A supplier's VAT number SHALL be stated internationally

A supplier's VAT number SHALL be stored and returned in its international form: spaces, dots and hyphens removed, upper case, and prefixed with the supplier's country code (`EL` for Greece) unless it already starts with letters. This SHALL hold for numbers synced from an ERP, for a person's correction of an invoice's supplier VAT number (using the country stated in the correction, else the invoice's, else the supplier's), and, through a migration, for numbers already stored. An empty VAT number SHALL be stored as none. A supplier's identity in the catalog SHALL remain keyed on the VAT number as its ERP states it, so that suppliers already stored keep their ids.

#### Scenario: A Danish CVR number from the ERP

- **WHEN** the ERP states a Danish supplier's VAT number as `12 64 44 26`
- **THEN** it is stored and returned as `DK12644426`

#### Scenario: A number already international

- **WHEN** the ERP states `IE6388047V` for an Irish supplier
- **THEN** it is stored as `IE6388047V`

