"""Which ERP integrations are connected and so take part in the pipeline."""
from __future__ import annotations

from sqlmodel import Session, select

from web_api.db.models import ErpIntegration


def connected_integrations(
    session: Session,
    integration_id: str | None = None,
    *,
    company_id: str | None = None,
) -> list[ErpIntegration]:
    """Every integration that should be synced, optionally narrowed to one or one company."""
    statement = select(ErpIntegration).where(ErpIntegration.disconnected_at.is_(None))  # type: ignore[union-attr]
    if integration_id is not None:
        statement = statement.where(ErpIntegration.id == integration_id)
    if company_id is not None:
        statement = statement.where(ErpIntegration.company_id == company_id)
    rows = session.exec(statement.order_by(ErpIntegration.created_at, ErpIntegration.id)).all()
    if integration_id is not None and not rows:
        raise ValueError(
            f"No connected ERP integration with id {integration_id!r}. "
            "The runner only syncs integrations that already exist and are connected."
        )
    return list(rows)
