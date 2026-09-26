"""One executor per run kind, each returning the summary the run records."""
from __future__ import annotations

from collections.abc import Callable

from sqlmodel import Session

from web_api.db.models import PipelineRunKind

from ..categorization.company import categorize_company
from ..documents import runner as documents_runner
from ..sync import runner as sync_runner
from ..sync.integrations import connected_integrations

Executor = Callable[[Session, str], dict]

_SYNC_COUNTS = ("invoices", "lines", "documents_queued", "standin_lines", "lines_withdrawn")


class RunFailed(RuntimeError):
    """The stage ran but could not do what the run asked."""


def _sync_summary(results: list[dict]) -> dict:
    summary: dict = {"integrations": len(results), "categorized": 0, "categorization_failed": 0}
    for key in _SYNC_COUNTS:
        summary[key] = sum(result.get(key, 0) for result in results)
    for result in results:
        categorization = result.get("categorization", {})
        summary["categorized"] += categorization.get("categorized", 0)
        summary["categorization_failed"] += categorization.get("failed", 0)
        if "skipped" in categorization:
            summary["categorization_skipped"] = categorization["skipped"]
    return summary


def sync(session: Session, company_id: str) -> dict:
    """Sync every connected integration of the company, as the sync CLI does."""
    integrations = connected_integrations(session, company_id=company_id)
    if not integrations:
        raise RunFailed("the company has no connected ERP integration")

    results: list[dict] = []
    for integration in integrations:
        results.extend(sync_runner.run_sync(integration_id=integration.id).values())

    errors = [result["error"] for result in results if result.get("status") == "error"]
    if errors:
        raise RunFailed("; ".join(errors))
    return _sync_summary(results)


def read_documents(session: Session, company_id: str) -> dict:
    """Read the company's pending documents, as the documents CLI does."""
    return documents_runner.run_documents(company_id=company_id)


def categorize(session: Session, company_id: str) -> dict:
    """Categorize the company's uncategorized lines without contacting the ERP."""
    stats = categorize_company(session, company_id)
    if "unavailable" in stats:
        raise RunFailed(f"the categorizer is unavailable: {stats['unavailable']}")
    return stats


EXECUTORS: dict[str, Executor] = {
    PipelineRunKind.SYNC.value: sync,
    PipelineRunKind.READ_DOCUMENTS.value: read_documents,
    PipelineRunKind.CATEGORIZE.value: categorize,
}


def execute(session: Session, kind: str, company_id: str) -> dict:
    """Run the executor for ``kind`` and return its summary."""
    executor = EXECUTORS.get(kind)
    if executor is None:
        raise RunFailed(f"unknown run kind {kind!r}")
    return executor(session, company_id)
