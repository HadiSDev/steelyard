"""A requested or automatic run of one pipeline stage for one company."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, String
from sqlmodel import Field, SQLModel

from ._base import _ts, _uuid

SYSTEM_REQUESTER = "system"


class PipelineRunKind(str, Enum):
    """Which stage a run executes."""

    SYNC = "sync"
    READ_DOCUMENTS = "read_documents"
    CATEGORIZE = "categorize"


class PipelineRunStatus(str, Enum):
    """Where a run is in its one-way lifecycle."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PipelineRun(SQLModel, table=True):
    """The request for a stage run and, once executed, its outcome."""

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        Index("ix_pipeline_runs_company_requested", "company_id", "requested_at"),
        Index("ix_pipeline_runs_status", "status"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    company_id: str = Field(sa_type=String, foreign_key="companies.id", nullable=False)
    kind: str = Field(sa_type=String, nullable=False)
    status: str = Field(sa_type=String, nullable=False, default=PipelineRunStatus.QUEUED.value)
    requested_by: str = Field(sa_type=String, nullable=False)
    requested_at: datetime = Field(sa_column=_ts())
    started_at: Optional[datetime] = Field(sa_type=DateTime(timezone=True), nullable=True)
    finished_at: Optional[datetime] = Field(sa_type=DateTime(timezone=True), nullable=True)
    summary: Optional[dict] = Field(sa_type=JSON, nullable=True)
    error: Optional[str] = Field(sa_type=String, nullable=True)
