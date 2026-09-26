"""The worker's loop: requested runs first, then automatic document reads."""
from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Callable
from enum import Enum

from sqlmodel import Session

from web_api.db.models import PipelineRunKind
from web_api.db.session import engine

from ..documents import runner as documents_runner
from .claims import claim_next, finish, recover_interrupted, start_system_run
from .executors import execute

logger = logging.getLogger("ai_api.worker")


class TickOutcome(str, Enum):
    """What one pass of the loop found to do."""

    RAN = "ran"
    READ = "read"
    IDLE = "idle"


def _error_text(exc: Exception) -> str:
    return str(exc) or type(exc).__name__


def _run_claimed() -> bool:
    """Claim and execute one queued run. Returns whether there was one."""
    with Session(engine) as session:
        run = claim_next(session)
        if run is None:
            return False
        run_id, kind, company_id = run.id, run.kind, run.company_id
        logger.info("run %s: %s for company %s", run_id, kind, company_id)
        try:
            summary = execute(session, kind, company_id)
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            logger.exception("run %s failed", run_id)
            finish(session, run_id, error=_error_text(exc))
            return True
        finish(session, run_id, summary=summary)
        logger.info("run %s succeeded: %s", run_id, summary)
        return True


def _pending_by_company(document_batch: int) -> Counter[str]:
    """How many of the next ``document_batch`` pending documents each company holds."""
    with Session(engine) as session:
        pending = documents_runner.pending_invoices(session, limit=document_batch)
        return Counter(invoice.company_id for invoice in pending)


def _read_for(company_id: str, count: int) -> None:
    """Read up to ``count`` of the company's pending documents as a `system` run."""
    with Session(engine) as session:
        run = start_system_run(session, company_id, PipelineRunKind.READ_DOCUMENTS)
        run_id = run.id
        logger.info("run %s: automatic read of %d document(s) for company %s",
                    run_id, count, company_id)
        try:
            summary = documents_runner.run_documents(company_id=company_id, limit=count)
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            logger.exception("run %s failed", run_id)
            finish(session, run_id, error=_error_text(exc))
            return
        finish(session, run_id, summary=summary)


def _read_pending(document_batch: int) -> bool:
    """Read the next batch of pending documents. Returns whether there were any."""
    by_company = _pending_by_company(document_batch)
    for company_id, count in by_company.items():
        _read_for(company_id, count)
    return bool(by_company)


def tick(document_batch: int) -> TickOutcome:
    """One pass: run one queued run, else read pending documents, else nothing."""
    if _run_claimed():
        return TickOutcome.RAN
    if _read_pending(document_batch):
        return TickOutcome.READ
    return TickOutcome.IDLE


def recover() -> int:
    """Fail the runs a previous worker left `running`."""
    with Session(engine) as session:
        recovered = recover_interrupted(session)
    if recovered:
        logger.warning("marked %d interrupted run(s) failed", recovered)
    return recovered


def run_worker(
    *,
    poll_seconds: float,
    document_batch: int,
    once: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> TickOutcome:
    """Recover interrupted runs, then tick until stopped (or once)."""
    recover()
    while True:
        try:
            outcome = tick(document_batch)
        except Exception:  # noqa: BLE001
            logger.exception("worker tick failed; retrying after the poll interval")
            outcome = TickOutcome.IDLE
        if once:
            return outcome
        if outcome == TickOutcome.IDLE:
            sleep(poll_seconds)
