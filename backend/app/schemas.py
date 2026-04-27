from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionStartResponse(BaseModel):
    session_id: int
    status: str
    started_at: datetime


class SessionStopResponse(BaseModel):
    session_id: int
    status: str
    ended_at: datetime
    report_id: int | None = None


class ReportSummary(BaseModel):
    id: int
    session_id: int
    created_at: datetime
    file_path: str


class SessionResponse(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    error_message: str | None = None
    latest_report: ReportSummary | None = None


class ActiveSessionResponse(BaseModel):
    active_session: SessionResponse | None


class ReportResponse(BaseModel):
    id: int
    session_id: int
    created_at: datetime
    markdown: str
    file_path: str
    excluded_non_work_seconds: float


class ClassificationReloadResponse(BaseModel):
    rule_count: int
    source_path: str


class ActivityBlock(BaseModel):
    start: datetime
    end: datetime
    duration_seconds: float
    app: str
    context: str | None
    category: str
    is_work: bool
    confidence: float
    label: str | None = Field(default=None)
