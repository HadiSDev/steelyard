"""Pipeline runs requested for a company."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from web_api.db.models import PipelineRunKind, PipelineRunStatus


class PipelineRunCreate(BaseModel):
    kind: PipelineRunKind


class PipelineRunRead(BaseModel):
    """A run and, once the worker has executed it, its outcome."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    kind: PipelineRunKind
    status: PipelineRunStatus
    requested_by: str
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: dict | None = None
    error: str | None = None
