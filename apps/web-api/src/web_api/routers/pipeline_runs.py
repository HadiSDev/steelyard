"""System-admin requests for pipeline runs, which the ai_api worker executes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from web_api.db.models import ErpIntegration, PipelineRun, PipelineRunKind, PipelineRunStatus
from ..auth.deps import TenantScope, get_managed_company, get_session, require_system_admin
from ..schemas import PipelineRunCreate, PipelineRunRead

router = APIRouter(prefix="/api/v1", tags=["pipeline-runs"])

_IN_FLIGHT = (PipelineRunStatus.QUEUED.value, PipelineRunStatus.RUNNING.value)


def _run_in_flight(session: Session, company_id: str, kind: PipelineRunKind) -> PipelineRun | None:
    """The company's queued or running run of this kind, if there is one."""
    return session.exec(
        select(PipelineRun)
        .where(
            PipelineRun.company_id == company_id,
            PipelineRun.kind == kind.value,
            PipelineRun.status.in_(_IN_FLIGHT),  # type: ignore[attr-defined]
        )
        .order_by(PipelineRun.requested_at.desc())  # type: ignore[attr-defined]
    ).first()


def _has_connected_erp(session: Session, company_id: str) -> bool:
    return session.exec(
        select(ErpIntegration.id).where(
            ErpIntegration.company_id == company_id,
            ErpIntegration.disconnected_at.is_(None),  # type: ignore[union-attr]
        )
    ).first() is not None


@router.post("/companies/{company_id}/runs", response_model=PipelineRunRead,
             status_code=status.HTTP_201_CREATED)
def request_run(
    company_id: str,
    body: PipelineRunCreate,
    response: Response,
    scope: TenantScope = Depends(require_system_admin),
    session: Session = Depends(get_session),
) -> PipelineRun:
    """Queue a run for the worker, or return the one of this kind already waiting."""
    company = get_managed_company(session, scope, company_id)

    existing = _run_in_flight(session, company.id, body.kind)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    if body.kind == PipelineRunKind.SYNC and not _has_connected_erp(session, company.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This company has no connected ERP integration to sync from.",
        )

    run = PipelineRun(company_id=company.id, kind=body.kind.value, requested_by=scope.user_id)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


@router.get("/companies/{company_id}/runs", response_model=list[PipelineRunRead])
def list_runs(
    company_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    scope: TenantScope = Depends(require_system_admin),
    session: Session = Depends(get_session),
) -> list[PipelineRun]:
    """The company's runs, newest first."""
    company = get_managed_company(session, scope, company_id)
    return list(
        session.exec(
            select(PipelineRun)
            .where(PipelineRun.company_id == company.id)
            .order_by(PipelineRun.requested_at.desc(), PipelineRun.id.desc())  # type: ignore[attr-defined]
            .limit(limit)
        ).all()
    )
