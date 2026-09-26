## Context

`Vendor` is a global catalog row (name, country, VAT number, description), and a tenant reaches a vendor only through `Invoice.vendor_id`. Two read paths exist today:

- `GET /api/v1/vendors` lists the suppliers referenced by the caller's invoices, by name, for the Spend Lines supplier filter. It carries no figures.
- `GET /api/v1/reports/spend-by-vendor` sums `Invoice.base_total` per vendor and currency, unpaged and unsorted beyond amount.

Neither answers the page's question in one request: a searchable, sortable, paged list with each supplier's figures. The Spend Lines page already sets the patterns this page should follow: URL-held filters validated in a route `validateSearch`, TanStack Query options in `lib/api/`, a `table-fixed` table with a `<colgroup>`, `keepPreviousData` while filters change, and page-sized skeletons.

## Goals / Non-Goals

**Goals:**
- One request per table view, returning the page of rows and their figures.
- Figures that agree with the rest of the product's rules: tenant-scoped, base currency, never summed across currencies.
- A page consistent with Spend Lines in layout, filters and states, and a one-step hand-off to a supplier's lines.

**Non-Goals:**
- Editing a supplier, including its description (the catalog is shared; editing needs its own audit and ownership rules).
- A supplier detail page, charts, or procurement signals such as redundancy or concentration.
- Merging duplicate suppliers.
- Renaming `vendor` in code, tables or API paths.

## Decisions

### A new `GET /api/v1/vendors/overview` rather than extending `GET /vendors`

`GET /vendors` serves the supplier filter's type-ahead, which needs names only and is called on every keystroke. Adding aggregates to it would slow that path and couple two consumers with different needs. A sibling endpoint keeps the filter cheap. *Alternative:* compose the page client-side from `/vendors` plus `spend-by-vendor` — rejected, because the report is unpaged and the two lists cannot be sorted or paged together.

### One aggregate query, grouped by vendor, then a second for spend per currency

The page of vendors is selected by one grouped query over `invoices ⨝ vendors` filtered to the caller's companies: `count(*)`, `max(invoice_date)`, and — for the spend sort — `sum(base_total − coalesce(base_tax, 0))`, ordered and limited in SQL. The spend-per-currency entries for just that page's vendor ids come from a second grouped query. This keeps both queries bounded by the page size and avoids loading invoices into Python.

### Spend is net of VAT

The Spend Lines summary reports net spend, and VAT is not a cost to a VAT-registered buyer. Using `base_total − base_tax` keeps the supplier figures comparable with it. *Alternative:* the gross `base_total` that `spend-by-vendor` sums — rejected for the page, and left unchanged in the report.

### Sorting by spend only within one base currency

Ordering amounts in DKK against amounts in EUR would be meaningless. Before sorting by spend, the endpoint reads the distinct base currencies of the listed companies; with more than one it answers 422. The frontend reads the companies it already loads to know whether spend sorting is available, and defaults to name when it is not. *Alternative:* sort by a converted amount — rejected; the platform does not convert between base currencies.

### Frontend layout

- `routes/_authed/suppliers.tsx` holds the queries and URL state; `components/suppliers/` holds the presentational pieces (`suppliers-panel.tsx`, `supplier-table.tsx`, `supplier-spend.tsx`, `suppliers-toolbar.tsx`), each with one component per concern.
- Search params: `q`, `company_id`, `sort`, `order`, `page`, validated in a `lib/supplier-search.ts` like `lib/entry-search.ts`. The search box updates the URL on a short debounce.
- Row activation opens `/suppliers/$vendorId`; its "View spend lines" button navigates to `/invoice-lines` with `vendor_id`, the filter Spend Lines already accepts. The route folder holds the list (`index.tsx`) and the detail (`$vendorId.tsx`) as siblings, not a layout.
- The nav entry becomes `{ label: 'Suppliers', icon: Building2, to: '/suppliers' }`.

## Risks / Trade-offs

- [An invoice with no base amount distorts the spend order] → it is counted and reported as unconverted, and contributes nothing to the sort key, matching how the rest of the product treats it.
- [A vendor named only by postings, not invoices, is missing] → accepted; every connector records a supplier on the invoice, and postings carry no vendor of their own.
- [Two grouped queries per request on large tenants] → both are bounded by `page_size`; `invoices.company_id` and `invoices.vendor_id` are the join and filter keys. If profiling shows a need, an index on `(company_id, vendor_id)` is a later migration.
- [The global description may be written by enrichment and be wrong] → the page labels it as the stored description and does not let anyone edit it here; correcting it is a separate change.

## Migration Plan

No schema change. Deploy the web API before the web app; the new route calls only the new endpoint, and removing the page rolls back cleanly.

## Open Questions

- None blocking. A supplier detail view and description editing are natural follow-ups once the list is in use.
