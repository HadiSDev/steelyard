## Context

Three stages turn ERP data into categorized spend, and today each only runs from
a terminal:

- `ai_api.sync.runner` fetches from the ERP, persists postings, bills and lines,
  queues documents (`doc_status = pending`), and categorizes uncategorized lines
  as its step 3.
- `ai_api.documents.runner` reads `pending` documents with the vision model and
  replaces the invoice's lines with the extracted ones, which start
  `uncategorized`. It never categorizes.
- `POST /invoices/{id}/reprocess` only returns an invoice to `pending`.

So the order an operator runs things in decides whether lines end up
categorized, and nothing runs unless someone types a command. The dependency
direction is enforced by packaging: `ai_api` imports `web_api`, never the
reverse, so the web API cannot call a stage directly.

## Goals / Non-Goals

**Goals:**

- A system admin can start a sync, a document read or a categorization for one
  company from Settings, and see how it went.
- Pending documents are read without anyone asking, and a read leaves its lines
  categorized.
- The web API stays free of AI calls and of `ai_api` imports.

**Non-Goals:**

- Scheduled syncs (cron-like "every night"). The run record makes them easy to
  add later; this change does not.
- Letting org admins trigger runs.
- Cancelling a run in progress.
- A run history page. The row shows the latest run; the API lists the last 20.
- Horizontal scaling of the worker. One worker is the deployment; the atomic
  claim only guarantees that a second one never double-runs.

## Decisions

### 1. The database is the queue

`PipelineRun` rows are both the request and the record. The web API inserts a
`queued` row; the worker claims it with
`UPDATE pipeline_runs SET status='running', started_at=now() WHERE id=:id AND status='queued'`
and treats a zero row count as "someone else took it".

*Alternatives:* a message broker (Redis, RabbitMQ) adds infrastructure for a
queue that sees a handful of jobs a day; `BackgroundTasks` in the web API would
put AI calls in the web process and needs an `ai_api` import, which the
packaging forbids; spawning `python -m …` subprocesses from the API is the same
coupling through a shell. A table needs nothing new, survives restarts, and
doubles as the history the UI shows.

### 2. The model lives in `web_api`, the execution in `ai_api`

`PipelineRun` (model, enums, schemas, router, migration `0012`) belongs to
`web_api`, which owns persistence. The worker imports the model like every other
`ai_api` stage. The router depends on `require_system_admin`, the existing
platform gate used by company deletion.

Columns: `id`, `company_id` (FK), `kind`, `status`, `requested_by`,
`requested_at`, `started_at`, `finished_at`, `summary` (JSON), `error`.
Index on `(company_id, requested_at)` for the row's latest-run query and on
`status` for the worker's claim.

### 3. One categorization, three callers

The categorize step moves out of `sync/runner.py` (1,171 lines) into
`ai_api/categorization/company.py`:

- `categorize_integration(session, integration_id, company_id, invoice_ids=None)`
  is today's `_categorize_pending` plus the tree-candidate and index setup from
  step 3, returning the same stats dict, including `skipped` when there is no
  usable tree.
- `categorize_company(session, company_id, invoice_ids=None)` runs it for each
  of the company's connected integrations and sums the stats.

The sync calls `categorize_integration` exactly as before. The document stage
calls `categorize_company(session, invoice.company_id, invoice_ids=[invoice.id])`
after a `processed` outcome, so only that invoice's new lines are categorized.
The worker's `categorize` run calls `categorize_company` for all lines.

*Alternative:* have the worker queue a `categorize` run after each read. It
needs no refactor, but it leaves the CLI's reads uncategorized, which is the gap
the user hit.

### 4. The worker is a small loop over two sources of work

`ai_api/worker/` holds:

- `claims.py`: `recover_interrupted()`, `claim_next()`, `finish()`.
- `executors.py`: one function per kind, each returning the summary dict.
  `sync` calls `run_sync(integration_id=…)` per connected integration;
  `read_documents` calls `run_documents(company_id=…)`; `categorize` calls
  `categorize_company`.
- `loop.py` and `__main__.py`: `python -m ai_api.worker [--once]`. Each tick
  first claims and runs one queued run; if there was none, it reads up to
  `WORKER_DOCUMENT_BATCH` pending documents, grouped by company, recording a
  `system` `read_documents` run per company that had any; if both found
  nothing, it sleeps `WORKER_POLL_SECONDS`. `--once` runs a single tick for
  tests and cron-style use.

Requested runs are checked before automatic reads each tick, so a click waits
for at most one batch.

### 5. Requests are idempotent per company and kind

`POST /companies/{id}/runs` returns the existing `queued`/`running` run of the
same kind with `200` instead of inserting a second one. It does not lock, so two
simultaneous clicks can still insert two rows; the second simply runs after the
first and finds little to do. That is acceptable and avoids a partial unique
index that SQLite (the test database) handles differently from Postgres.

### 6. The frontend polls only while something is in flight

A `companyRunsQueryOptions(api, companyId)` query fetches the latest runs, with
`refetchInterval` of 3 s while any listed run is `queued` or `running`, and no
polling otherwise. Watching only the newest run would stop polling when a newer
run finishes before an older one, leaving the older one shown in progress. Only rows rendered for a system admin mount the query, so
other users make no requests. The Run menu is a dropdown in the company row;
the latest run is a compact line under the company name: kind, status badge,
relative time, and counts or error.

## Risks / Trade-offs

- **The worker is not running** → requests stay `queued` and nothing happens.
  → The row shows "Queued" with its time, so a stuck queue is visible; the README
  lists the worker next to the web API as a process to start.
- **A long sync blocks automatic reads and other requests** → one worker runs one
  thing at a time. → Acceptable at current volumes; a second worker is safe
  thanks to the atomic claim if it is ever needed.
- **The worker dies mid-run** → the run stays `running`. → `recover_interrupted`
  marks such runs `failed` on start. A run that died mid-document leaves that
  invoice `processing`; the existing document stage already treats
  `processing` as claimed, so reprocessing it stays a manual step, as today.
- **Automatic reads spend model calls without a click** → only documents already
  `pending` are read, the same set the CLI would read; batches are bounded by
  `WORKER_DOCUMENT_BATCH`.
- **Categorization inside the document stage makes reads slower** → only the
  invoice's own new lines are categorized, typically one to ten lines.

## Migration Plan

1. Deploy the migration (`0012_pipeline_runs`); it only adds a table.
2. Deploy web-api and web; the Run menu appears for system admins. Requests queue
   until the worker runs.
3. Start `python -m ai_api.worker`. It drains the queue and any pending
   documents.

Rollback: stop the worker and revert the deploy; `alembic downgrade 0011` drops
the table. The CLI commands keep working throughout.

## Open Questions

- Whether the worker should also run a periodic sync per company (e.g. hourly).
  Left out here; it would be a new automatic run source in the same loop.
