## MODIFIED Requirements

### Requirement: Persistent application shell across authenticated routes

The themed application shell SHALL be owned by the authenticated layout rather
than by any single page — sidebar, navigation, topbar, theme toggle, and user
menu — so every authenticated route renders inside it and the shell is not
remounted when navigating between routes. Sidebar navigation entries SHALL be
router links that navigate on activation, and the entry matching the current
route SHALL be rendered as active. Entries for pages that do not exist yet SHALL
remain visibly disabled.

The navigation SHALL offer a **Spend Lines** entry linking to the
`/invoice-lines` route. It replaces the previous disabled **Invoices**
placeholder: the page lists invoice lines grouped by voucher, so its URL names
the lines rather than the ERP entries behind them. No Invoices entry SHALL be
shown until an invoice review page exists.

The navigation SHALL offer a **Suppliers** entry linking to the `/suppliers`
route. It replaces the previous disabled **Vendors** placeholder; the product
calls the businesses a company buys from suppliers throughout, so the entry
does too. No Vendors entry SHALL be shown.

#### Scenario: Shell is shared by every authenticated page

- **WHEN** a signed-in user navigates from the dashboard to another
  authenticated route
- **THEN** the same shell persists, with the page content swapping inside it

#### Scenario: Active route is highlighted

- **WHEN** an authenticated route is open
- **THEN** the sidebar entry corresponding to it is marked active and the others
  are not

#### Scenario: Navigation happens through the router

- **WHEN** the user activates an enabled sidebar entry
- **THEN** the router navigates to that route and the URL updates, without a full
  page load

#### Scenario: Spend Lines is a working navigation entry

- **WHEN** a signed-in user activates the Spend Lines entry
- **THEN** the router navigates to `/invoice-lines`, the entry is marked active,
  and no disabled Invoices entry is present

#### Scenario: Suppliers is a working navigation entry

- **WHEN** a signed-in user activates the Suppliers entry
- **THEN** the router navigates to `/suppliers`, the entry is marked active,
  and no Vendors entry is present
