## Why

The AI stages only run when someone types a command. The sync queues documents
but never reads them, the document reader never categorizes the lines it
creates, and the Reprocess button only marks an invoice `pending`. In practice,
new vouchers sit with no invoice number and uncategorized lines until an
operator remembers to run the right commands in the right order — and nobody
can start any of it from the app.

## What Changes

- A **pipeline run** becomes a stored record: which company, which kind of run
  (**Sync from ERP**, **Read documents**, **Categorize lines**), who asked,
  and its status (`queued → running → succeeded | failed`) with counts and any
  error.
- The web API gains endpoints to request a run for a company and to list a
  company's recent runs. Requesting is **system-admin only**. The web API only
  records the request: it never imports `ai_api` and never runs AI itself.
- A new long-running **`ai_api` worker** (`python -m ai_api.worker`) executes
  requested runs one at a time, and — when nothing is requested — reads any
  `pending` documents on its own, so a sync or a Reprocess click is followed by
  a read without anyone typing a command.
- A document read **categorizes the lines it just created**, so a read no longer
  leaves its lines `uncategorized` until the next sync.
- **Settings → Companies** gains, for system admins only, a run menu on each
  company row and the status of the company's latest run, which updates while a
  run is in progress. Everyone else sees neither.
- The existing CLI commands (`ai_api.sync.runner`, `ai_api.documents.runner`)
  keep working unchanged.

## Capabilities

### New Capabilities

- `pipeline-runs`: the run record, the system-admin API to request and list
  runs, and the worker that executes requested runs and drains pending
  documents.

### Modified Capabilities

- `invoice-document-processing`: pending documents are read automatically by the
  worker, and a successful read categorizes the lines it created.
- `frontend-settings`: system admins can trigger each run kind from a company's
  row and see its latest run.

## Impact

- **Database:** new `pipeline_runs` table (Alembic migration `0012`).
- **web-api:** new model, schemas and router (`/api/v1/companies/{id}/runs`),
  guarded by the existing system-admin dependency.
- **ai-api:** new `ai_api.worker` package; the categorize step and the document
  stage become callable for one company without the CLI; the document stage
  categorizes after a successful read.
- **web:** company row run menu, latest-run status and polling query, visible
  only when `is_system_admin`.
- **Operations:** one more process to run in development and deployment, next
  to the web API. Documented in the README.
