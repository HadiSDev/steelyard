## ADDED Requirements

### Requirement: A system admin can run a company's pipeline from Settings

The Companies section SHALL offer, on each company row and to system admins
only, a **Run** menu with **Sync from ERP**, **Read documents** and
**Categorize lines**, and SHALL show the company's latest run.

- A reader without the platform flag SHALL NOT see the menu or the run status at
  all, rather than see them disabled.
- **Sync from ERP** SHALL NOT be offered for a company with no connected ERP
  integration.
- Choosing an action SHALL request the run and confirm it was queued. A refusal
  from the server SHALL be shown as an error, not swallowed.
- The latest run SHALL be shown with its kind, status and when it was requested;
  a finished run SHALL show its counts, a failed run its error, and a run started
  by the worker on its own SHALL be marked as automatic.
- While the latest run is `queued` or `running`, its status SHALL refresh on its
  own until it finishes, and the action it represents SHALL be shown as in
  progress rather than offered again.

#### Scenario: A system admin sees the run menu

- **WHEN** a system admin views the companies list
- **THEN** each company row offers a Run menu with the three actions and shows
  the company's latest run

#### Scenario: Everyone else sees neither

- **WHEN** an org admin, moderator, member or viewer views the companies list
- **THEN** no Run menu and no run status are rendered

#### Scenario: A queued run updates until it finishes

- **WHEN** a system admin requests Categorize lines and the run is `queued`
- **THEN** the row shows the run as queued, then running, then its result,
  without the page being reloaded

#### Scenario: A failure is shown where it happened

- **WHEN** the latest run of a company has `failed`
- **THEN** the row shows it failed and states its error

#### Scenario: No sync without an ERP

- **WHEN** a system admin opens the Run menu for a company with no connected ERP
  integration
- **THEN** Sync from ERP is not offered
