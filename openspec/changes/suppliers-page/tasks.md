## 1. Supplier overview API (web-api)

- [x] 1.1 Add `VendorSpendRead` (currency, amount, unconverted_count) and `VendorOverviewRead` (id, name, country_code, vat_number, description, invoice_count, last_invoice_date, spend) schemas and export them
- [x] 1.2 Write failing tests for `GET /api/v1/vendors/overview`: only the caller's suppliers are listed; a shared supplier carries only the caller's figures; `company_id` narrows list and figures and a foreign company is 404
- [x] 1.3 Write failing tests for the figures: spend is net of VAT in base currency; an unconverted invoice is counted but not summed; two base currencies give two spend entries; `last_invoice_date` is the latest date
- [x] 1.4 Write failing tests for search (name and VAT number), each `sort`/`order`, name-then-id tie-breaking across pages, `page_size` capped at 100, and 422 for a spend sort across base currencies
- [x] 1.5 Implement the endpoint: one grouped query selecting the page of vendors with count, last date and the spend sort key; a second grouped query for spend per currency over that page's vendor ids

## 2. Data layer (web)

- [x] 2.1 Add `VendorOverviewRead`, `VendorSpendRead` and `SupplierFilters` types
- [x] 2.2 Add `lib/supplier-search.ts` validating `q`, `company_id`, `sort`, `order` and `page`, dropping unknown values, with tests
- [x] 2.3 Add `supplierOverviewQueryOptions` in `lib/api/` keyed by the filters, keeping previous data while they change, with a test of its key and request

## 3. Suppliers page (web)

- [x] 3.1 Build `components/suppliers/supplier-spend.tsx`: amounts per currency and the unconverted note
- [x] 3.2 Build `components/suppliers/supplier-table.tsx`: fixed columns (Supplier, VAT number, What they sell, Invoices, Spend, Last invoice), sortable headers with `aria-sort`, explicit marks for missing values, keyboard-activatable rows
- [x] 3.3 Build `components/suppliers/suppliers-toolbar.tsx`: debounced search and company filter
- [x] 3.4 Build `components/suppliers/suppliers-panel.tsx`: toolbar, table, pagination, and the loading, empty ("appear once invoices are synced"), no-match (with clear) and error states
- [x] 3.5 Add `routes/_authed/suppliers.tsx`: URL state, default sort by spend when the listed companies share a base currency and by name otherwise, and row activation navigating to `/invoice-lines?vendor_id=`
- [x] 3.6 Component tests covering each scenario in `frontend-suppliers`

## 4. Navigation (web)

- [x] 4.1 Rename the sidebar entry to **Suppliers** with a link to `/suppliers`; update the shell tests so the entry navigates, is active on the route, and no Vendors entry exists
- [x] 4.2 Regenerate the route tree

## 5. Verify

- [x] 5.1 Run web-api pytest, and vitest, tsc, eslint and prettier on the web app, with no regressions
- [ ] 5.2 Check the page in the browser at desktop and phone widths: no horizontal scroll, and no layout shift when sorting, paging or searching
