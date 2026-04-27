from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .classifier import RuleClassifier
from .config import get_settings
from .db import Base, engine, get_db
from .models import ReportRecord, SessionRecord
from .schemas import (
    ActiveSessionResponse,
    ClassificationReloadResponse,
    ReportResponse,
    ReportSummary,
    SessionResponse,
    SessionStartResponse,
    SessionStopResponse,
)
from .services import get_active_session, start_session, stop_session


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    RuleClassifier.sync_rule_file_to_database(Session(bind=engine), settings.classification_rules_path)
    yield


app = FastAPI(title="Jikan Backend", lifespan=lifespan)


def build_report_summary(report: ReportRecord | None) -> ReportSummary | None:
    if report is None:
        return None
    return ReportSummary(
        id=report.id,
        session_id=report.session_id,
        created_at=report.created_at,
        file_path=report.file_path,
    )


def build_session_response(session: SessionRecord) -> SessionResponse:
    latest_report = max(session.reports, key=lambda report: report.created_at) if session.reports else None
    return SessionResponse(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        error_message=session.error_message,
        latest_report=build_report_summary(latest_report),
    )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sessions/start", response_model=SessionStartResponse)
def create_session(db: Session = Depends(get_db)) -> SessionStartResponse:
    session = start_session(db)
    return SessionStartResponse(session_id=session.id, status=session.status, started_at=session.started_at)


@app.post("/sessions/stop", response_model=SessionStopResponse)
def close_session(db: Session = Depends(get_db)) -> SessionStopResponse:
    session, report = stop_session(db)
    if session.ended_at is None:
        raise HTTPException(status_code=500, detail="Session stop did not record an end timestamp.")
    return SessionStopResponse(
        session_id=session.id,
        status=session.status,
        ended_at=session.ended_at,
        report_id=report.id,
    )


@app.get("/sessions/active", response_model=ActiveSessionResponse)
def read_active_session(db: Session = Depends(get_db)) -> ActiveSessionResponse:
    session = get_active_session(db)
    if session is None:
        return ActiveSessionResponse(active_session=None)
    db.refresh(session)
    return ActiveSessionResponse(active_session=build_session_response(session))


@app.get("/sessions/{session_id}", response_model=SessionResponse)
def read_session(session_id: int, db: Session = Depends(get_db)) -> SessionResponse:
    session = db.scalar(select(SessionRecord).where(SessionRecord.id == session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.refresh(session)
    return build_session_response(session)


@app.get("/reports/latest", response_model=ReportResponse | None)
def read_latest_report(db: Session = Depends(get_db)) -> ReportResponse | None:
    report = db.scalar(select(ReportRecord).order_by(ReportRecord.created_at.desc()))
    if report is None:
        return None
    return ReportResponse(
        id=report.id,
        session_id=report.session_id,
        created_at=report.created_at,
        markdown=report.markdown,
        file_path=report.file_path,
        excluded_non_work_seconds=report.excluded_non_work_seconds,
    )


@app.get("/reports/{report_id}", response_model=ReportResponse)
def read_report(report_id: int, db: Session = Depends(get_db)) -> ReportResponse:
    report = db.scalar(select(ReportRecord).where(ReportRecord.id == report_id))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return ReportResponse(
        id=report.id,
        session_id=report.session_id,
        created_at=report.created_at,
        markdown=report.markdown,
        file_path=report.file_path,
        excluded_non_work_seconds=report.excluded_non_work_seconds,
    )


@app.post("/classifications/reload", response_model=ClassificationReloadResponse)
def reload_classifications(db: Session = Depends(get_db)) -> ClassificationReloadResponse:
    settings = get_settings()
    count = RuleClassifier.sync_rule_file_to_database(db, settings.classification_rules_path)
    return ClassificationReloadResponse(rule_count=count, source_path=str(settings.classification_rules_path.resolve()))
