## Why

The sidebar has carried a disabled **Vendors** entry since the shell was built, and there is still no page behind it. Suppliers are the second question a buyer asks after "what did we spend on" — "who did we spend it with" — and today the only way to see a supplier's figures is to filter Spend Lines by them one at a time. The rest of the product says "supplier" (the Spend Lines column, the filter, the invoice header), so the entry's name is also out of step.

## What Changes

- Rename the sidebar entry **Vendors** to **Suppliers** and make it a working link to a new `/suppliers` route.
- Add a **Suppliers** page: one table of every supplier the organization's invoices name, with each supplier's country (flag and name), VAT number, what they sell (the stored description), how many invoices they sent, the spend on them in base currency, and the date of the last invoice.
- The table can be searched by name or VAT number, filtered by company, sorted by name, spend, invoice count or last invoice, and paged. Its state lives in the URL, as Spend Lines' does.
- Selecting a supplier opens Spend Lines filtered to that supplier.
- Add a read-only web API endpoint, `GET /api/v1/vendors/overview`, returning the paged, sorted supplier rows with their figures. The existing `GET /api/v1/vendors` (used by the supplier filter) is unchanged.

## Capabilities

### New Capabilities
- `supplier-directory`: the tenant-scoped supplier overview endpoint — which suppliers are listed, the figures each carries, search, company filter, sorting and paging.
- `frontend-suppliers`: the Suppliers page — its table, search, filter, sort, paging, loading/empty/error states, and the hand-off to Spend Lines.

### Modified Capabilities
- `frontend-auth-dashboard`: the shell's navigation offers a working **Suppliers** entry linking to `/suppliers` in place of the disabled **Vendors** placeholder.

## Impact

- **web-api**: new route in `routers/vendors.py` (or a sibling module if that file grows), a new response schema, tests. No migration: every figure is derived from `invoices` and `vendors`.
- **web**: new route `routes/_authed/suppliers.tsx`, a `components/suppliers/` folder, a query in `lib/api/`, types, the nav entry in `app-shell.tsx`, and a search-param validator.
- The name in code stays `vendor` (model, table, API path); "Supplier" is the user-facing word.
