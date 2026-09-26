"""Helpers for the worker tests: recording and reading pipeline runs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from web_api.db.models import Company, PipelineRun, PipelineRunStatus
from web_api.spend_trees import service

_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def assign_default_tree(engine, company_id: str) -> None:
    with Session(engine) as s:
        company = s.get(Company, company_id)
        tree = service.ensure_default_tree(s, company.organization_id)
        company.spend_tree_id = tree.id
        s.add(company)
        s.commit()


def add_run(
    engine,
    company_id: str,
    kind: str,
    *,
    status: PipelineRunStatus = PipelineRunStatus.QUEUED,
    minutes_ago: int = 0,
) -> str:
    """Record a run the way the web API does, and return its id."""
    with Session(engine) as s:
        run = PipelineRun(
            company_id=company_id,
            kind=kind,
            status=status.value,
            requested_by="user_admin",
            requested_at=_EPOCH - timedelta(minutes=minutes_ago),
        )
        s.add(run)
        s.commit()
        return run.id


def get_run(engine, run_id: str) -> PipelineRun:
    with Session(engine) as s:
        return s.get(PipelineRun, run_id)


def all_runs(engine) -> list[PipelineRun]:
    with Session(engine) as s:
        return list(s.exec(select(PipelineRun).order_by(PipelineRun.requested_at)).all())
