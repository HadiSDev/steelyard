## ADDED Requirements

### Requirement: A pipeline run is a stored record

The system SHALL store every requested or automatic pipeline run as a
`PipelineRun` row carrying: the company it runs for, its `kind`, its `status`,
who requested it, when it was requested, started and finished, a `summary` of
counts, and an `error` when it failed.

- `kind` SHALL be one of `sync` (sync from ERP), `read_documents` (read the
  company's pending documents) or `categorize` (categorize the company's
  uncategorized lines).
- `status` SHALL move only `queued → running → succeeded | failed`. A run SHALL
  never move backwards, and a finished run SHALL never change again.
- `requested_by` SHALL be the requesting user's id, or `system` for a run the
  worker started on its own.
- Deleting a company SHALL delete its runs.

#### Scenario: A requested run starts queued

- **WHEN** a run is requested for a company
- **THEN** a `PipelineRun` exists for that company with status `queued`, the
  requesting user as `requested_by`, and no start or finish time

#### Scenario: A finished run is final

- **WHEN** a run has reached `succeeded` or `failed`
- **THEN** no later operation changes its status, times, summary or error

### Requirement: A system admin can request a run for a company

The API SHALL provide `POST /api/v1/companies/{company_id}/runs` with a body
`{"kind": <kind>}`, restricted to system admins, which records a `queued` run
and responds `201 Created` with it.

- It SHALL respond `403 Forbidden` to any caller who is not a system admin,
  whatever their organization role, and record nothing.
- It SHALL respond `404 Not Found` for an unknown company.
- It SHALL respond `422 Unprocessable Entity` for an unknown `kind`.
- It SHALL respond `409 Conflict` for a `sync` when the company has no connected
  ERP integration, since the run could never succeed.
- When a run of the same kind is already `queued` or `running` for the company,
  it SHALL respond `200 OK` with that existing run instead of recording a
  second one. Clicking twice SHALL NOT queue the work twice.
- It SHALL NOT import or call `ai_api`. Recording the request is the whole of
  its work.

#### Scenario: A system admin queues a sync

- **WHEN** a system admin posts `{"kind": "sync"}` for a company with a connected
  integration
- **THEN** the API responds `201 Created` with a `queued` sync run

#### Scenario: An org admin cannot request a run

- **WHEN** an organization admin who is not a system admin posts a run request
- **THEN** the API responds `403 Forbidden` and no run is recorded

#### Scenario: A second click returns the run already waiting

- **WHEN** a `read_documents` run is `queued` for a company and a system admin
  requests another `read_documents` run for it
- **THEN** the API responds `200 OK` with the existing run and no new run is
  recorded

#### Scenario: A sync needs an ERP connection

- **WHEN** a system admin requests a `sync` for a company with no connected
  integration
- **THEN** the API responds `409 Conflict` and no run is recorded

### Requirement: A company's recent runs can be listed

The API SHALL provide `GET /api/v1/companies/{company_id}/runs`, restricted to
system admins, returning the company's runs newest first, limited to the most
recent 20 by default and to at most 100 with `?limit=`.

#### Scenario: Runs are listed newest first

- **WHEN** a system admin lists a company's runs after requesting a sync and then
  a categorize
- **THEN** the categorize run is listed before the sync run

#### Scenario: Only system admins may list runs

- **WHEN** a caller who is not a system admin lists a company's runs
- **THEN** the API responds `403 Forbidden`

### Requirement: The worker executes requested runs

`python -m ai_api.worker` SHALL be a long-running process that repeatedly
claims the oldest `queued` run, executes it, and records the outcome.

- Claiming SHALL be atomic: a run SHALL be moved from `queued` to `running` in a
  single conditional update, so two workers never execute the same run.
- A `sync` run SHALL sync every connected integration of the company exactly as
  `python -m ai_api.sync.runner --integration-id <id>` does.
- A `read_documents` run SHALL read the company's `pending` documents exactly as
  `python -m ai_api.documents.runner --company-id <id>` does, including the
  categorization of the lines each read creates.
- A `categorize` run SHALL categorize the company's `uncategorized` lines the
  way the sync's categorization step does, without contacting the ERP.
- On success the run SHALL be `succeeded` with a `summary` of the counts the
  stage reports (for example lines categorized, documents read, failures).
- An exception SHALL mark the run `failed` with the error message, and the worker
  SHALL continue with the next run.
- When the worker starts, any run left `running` by a previous worker SHALL be
  marked `failed` with an error saying the worker stopped, so no run stays
  `running` forever.

#### Scenario: A queued run is executed

- **WHEN** a `categorize` run is `queued` and the worker polls
- **THEN** the run becomes `running`, the company's uncategorized lines are
  categorized, and the run ends `succeeded` with the number of lines categorized

#### Scenario: A failing run does not stop the worker

- **WHEN** a queued run raises during execution and another run is queued behind
  it
- **THEN** the first run is `failed` with its error and the second still runs

#### Scenario: Two workers never share a run

- **WHEN** two workers poll at the same moment with one run queued
- **THEN** exactly one of them executes it

#### Scenario: An interrupted run is not left running

- **WHEN** the worker starts and finds a run in `running`
- **THEN** that run is marked `failed` with an error saying the worker stopped

### Requirement: The worker reads pending documents on its own

When no run is queued, the worker SHALL read `pending` documents without being
asked, so a sync or a Reprocess click is followed by a read with no command
typed.

- It SHALL read at most a configured number of documents per poll
  (`WORKER_DOCUMENT_BATCH`, default 5), so a requested run never waits behind a
  long backlog for more than one batch.
- It SHALL record each batch that read at least one document as a
  `read_documents` run for that company with `requested_by = "system"`, so the
  company's latest run shows the automatic work too. A poll that finds nothing
  SHALL record nothing.
- It SHALL wait `WORKER_POLL_SECONDS` (default 5) between polls that found no
  work.

#### Scenario: A reprocessed document is read without a command

- **WHEN** an invoice is returned to `pending` and the worker is running with no
  run queued
- **THEN** the worker reads it and records a `system` `read_documents` run for
  its company

#### Scenario: An idle poll leaves no trace

- **WHEN** the worker polls and finds no queued run and no pending document
- **THEN** no run is recorded
