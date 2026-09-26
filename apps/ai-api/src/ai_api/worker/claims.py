"""Moving pipeline runs through their one-way lifecycle."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import update
from sqlmodel import Session, select

from web_api.db.models import (
    SYSTEM_REQUESTER,
    PipelineRun,
    PipelineRunKind,
    PipelineRunStatus,
)

INTERRUPTED = "the worker stopped before the run finished"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def recover_interrupted(session: Session) -> int:
    """Fail every run a previous worker left `running`. Returns how many."""
    result = session.exec(
        update(PipelineRun)
        .where(PipelineRun.status == PipelineRunStatus.RUNNING.value)
        .values(status=PipelineRunStatus.FAILED.value, finished_at=_now(), error=INTERRUPTED)
    )
    session.commit()
    return result.rowcount


def claim(session: Session, run_id: str) -> PipelineRun | None:
    """Move one run from `queued` to `running`, or None when someone else took it."""
    result = session.exec(
        update(PipelineRun)
        .where(
            PipelineRun.id == run_id,
            PipelineRun.status == PipelineRunStatus.QUEUED.value,
        )
        .values(status=PipelineRunStatus.RUNNING.value, started_at=_now())
    )
    session.commit()
    if result.rowcount != 1:
        return None
    return session.get(PipelineRun, run_id)


def claim_next(session: Session) -> PipelineRun | None:
    """Claim the oldest queued run, or None when nothing is waiting."""
    queued = session.exec(
        select(PipelineRun.id)
        .where(PipelineRun.status == PipelineRunStatus.QUEUED.value)
        .order_by(PipelineRun.requested_at, PipelineRun.id)
    ).all()
    for run_id in queued:
        run = claim(session, run_id)
        if run is not None:
            return run
    return None


def start_system_run(session: Session, company_id: str, kind: PipelineRunKind) -> PipelineRun:
    """Record a run the worker started on its own, already `running`."""
    now = _now()
    run = PipelineRun(
        company_id=company_id,
        kind=kind.value,
        status=PipelineRunStatus.RUNNING.value,
        requested_by=SYSTEM_REQUESTER,
        requested_at=now,
        started_at=now,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def finish(
    session: Session,
    run_id: str,
    *,
    summary: dict | None = None,
    error: str | None = None,
) -> bool:
    """End a running run as `succeeded` with its summary, or `failed` with its error."""
    status = PipelineRunStatus.FAILED if error is not None else PipelineRunStatus.SUCCEEDED
    result = session.exec(
        update(PipelineRun)
        .where(
            PipelineRun.id == run_id,
            PipelineRun.status == PipelineRunStatus.RUNNING.value,
        )
        .values(status=status.value, finished_at=_now(), summary=summary, error=error)
    )
    session.commit()
    return result.rowcount == 1
