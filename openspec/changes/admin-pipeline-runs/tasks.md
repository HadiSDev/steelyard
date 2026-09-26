## 1. Run record (web-api)

- [x] 1.1 Add `PipelineRunKind` and `PipelineRunStatus` enums and the `PipelineRun` model (company FK, kind, status, requested_by, requested/started/finished times, summary JSON, error) under `db/models/`
- [x] 1.2 Write migration `0012_pipeline_runs` with indexes on `(company_id, requested_at)` and `status`; confirm `tests/db/test_migrations.py` still passes
- [x] 1.3 Delete a company's runs in `company_deletion.delete_company`, with a test

## 2. Run API (web-api)

- [x] 2.1 Add `PipelineRunRead` and `PipelineRunCreate` schemas
- [x] 2.2 Write failing tests for `POST /companies/{id}/runs`: system admin gets 201 queued run; org admin gets 403 and nothing recorded; unknown company 404; unknown kind 422; sync with no connected integration 409; a second request of the same kind returns 200 with the existing run
- [x] 2.3 Implement the POST endpoint behind `require_system_admin`
- [x] 2.4 Write failing tests for `GET /companies/{id}/runs`: newest first, default limit 20, `?limit=` capped at 100, 403 for non-system-admins
- [x] 2.5 Implement the GET endpoint

## 3. Shared categorization (ai-api)

- [x] 3.1 Move the categorize step (tree candidates, index, `_categorize_pending`) from `sync/runner.py` into `ai_api/categorization/company.py` as `categorize_integration(session, integration_id, company_id, invoice_ids=None)`, returning the same stats including `skipped`
- [x] 3.2 Add `categorize_company(session, company_id, invoice_ids=None)` that runs it for each connected integration and sums the stats, with tests
- [x] 3.3 Point the sync's step 3 at `categorize_integration`; the existing sync tests pass unchanged

## 4. Document reads categorize their lines (ai-api)

- [x] 4.1 Write failing tests: a processed read leaves no line `uncategorized`; a failed read categorizes nothing; no tree leaves lines `uncategorized` and reports categorization skipped
- [x] 4.2 Call `categorize_company(..., invoice_ids=[invoice.id])` after a `processed` outcome in `run_documents`, and add the categorization counts to its report

## 5. Worker (ai-api)

- [x] 5.1 `ai_api/worker/claims.py`: `recover_interrupted`, `claim_next` (conditional `queued → running` update), `finish(run, summary | error)`, with tests including two claimers racing for one run
- [x] 5.2 `ai_api/worker/executors.py`: `sync`, `read_documents` and `categorize` executors returning summary dicts, with tests against the fake connector
- [x] 5.3 `ai_api/worker/loop.py`: one tick = run one queued run, else read up to `WORKER_DOCUMENT_BATCH` pending documents recording a `system` run per company that had any, else report idle; tests for each branch and for an idle tick recording nothing
- [x] 5.4 `python -m ai_api.worker [--once]` entry point with `WORKER_POLL_SECONDS` and `WORKER_DOCUMENT_BATCH` settings; a failing run is marked `failed` and the loop continues
- [x] 5.5 Add the settings to `.env.example` and the worker command to the README's run instructions

## 6. Frontend (web)

- [x] 6.1 Add `PipelineRun` types and `companyRunsQueryOptions` / `requestRunMutation` in `lib/api/`, polling every 3 s while the newest run is queued or running, with tests
- [x] 6.2 Build the company row Run menu (Sync from ERP, Read documents, Categorize lines) shown only to system admins; Sync hidden without a connected ERP; toast on queued, error on refusal
- [x] 6.3 Build the latest-run line (kind, status badge, relative time, counts or error, "automatic" for system runs), shown only to system admins
- [x] 6.4 Component tests: menu and status absent for non-system-admins; actions request the right kind; in-progress action not offered again; failed run shows its error; no Sync without ERP

## 7. Verify

- [x] 7.1 Run all suites (web-api, ai-api, mock-erp pytest; vitest, tsc, eslint, prettier) with no regressions
- [x] 7.2 Run the worker with `--once` against a scratch database seeded through the API to confirm a queued categorize run ends `succeeded`
