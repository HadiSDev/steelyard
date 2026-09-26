## ADDED Requirements

### Requirement: The Suppliers page SHALL show one table of the organization's suppliers

The `/suppliers` route SHALL render, inside the application shell, a table of the suppliers from `GET /api/v1/vendors/overview`, one row per supplier, with the columns **Supplier** (name, and the country code where known), **VAT number**, **What they sell** (the stored description, truncated to one line and shown in full on hover or focus), **Invoices**, **Spend**, and **Last invoice**. Spend SHALL be shown per base currency, never summed across currencies; a supplier with invoices left unconverted SHALL say so beside its amount. Absent values SHALL be shown as an explicit mark rather than an empty cell. The table SHALL keep fixed column widths, so loading, paging or sorting does not reflow it.

#### Scenario: A supplier's figures are shown

- **WHEN** the page loads for an organization with suppliers
- **THEN** each supplier appears once with its country, VAT number, description, invoice count, spend and last invoice date

#### Scenario: A supplier with no description

- **WHEN** a supplier has no stored description
- **THEN** its description cell shows an explicit "not described" mark

#### Scenario: Several currencies

- **WHEN** a supplier's spend has a DKK and a EUR entry
- **THEN** both amounts are shown, each in its own currency

### Requirement: The table SHALL be searchable, filterable, sortable and paged through the URL

The page SHALL offer a search box (name or VAT number), a company filter, sortable column headers for Supplier, Invoices, Spend and Last invoice, and pagination. Every one of these SHALL be held in the URL's search parameters, so a reload, a shared link or the back button restores the same view. The default view SHALL be sorted by spend, largest first, when the listed companies share one base currency, and by name otherwise; sorting by spend SHALL not be offered when it would compare currencies.

#### Scenario: A search survives a reload

- **WHEN** the user searches for "google", sorts by invoices, then reloads
- **THEN** the same search, sort and page are shown

#### Scenario: Default order

- **WHEN** the user opens the page without parameters and all companies share a base currency
- **THEN** suppliers are listed by spend, largest first

#### Scenario: Mixed base currencies

- **WHEN** the organization's companies have different base currencies and no company is selected
- **THEN** the table is sorted by name and the Spend header offers no sorting

### Requirement: Selecting a supplier SHALL open its spend lines

Activating a supplier row, by pointer or keyboard, SHALL navigate to Spend Lines (`/invoice-lines`) filtered to that supplier.

#### Scenario: From supplier to lines

- **WHEN** the user activates the row for a supplier
- **THEN** the router navigates to `/invoice-lines` with that supplier's id as the supplier filter

### Requirement: The page SHALL have loading, empty and error states

While the first page loads the table SHALL show placeholder rows of the final layout's size. When the organization has no suppliers the page SHALL say so and explain that suppliers appear once invoices are synced; when a search or filter matches nothing it SHALL say that instead and offer to clear it. A failed request SHALL show an error state rather than an empty table. While a new search, sort or page loads, the previous rows SHALL remain in place.

#### Scenario: Nothing synced yet

- **WHEN** the organization has no invoices naming a supplier
- **THEN** the page states that suppliers appear once invoices are synced

#### Scenario: Nothing matches

- **WHEN** a search matches no supplier
- **THEN** the page states that nothing matches and offers to clear the search

#### Scenario: The request fails

- **WHEN** the overview request fails
- **THEN** an error state is shown instead of the table
