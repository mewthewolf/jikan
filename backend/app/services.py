from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .activitywatch import ActivityWatchClient, NormalizedEvent, overlap_duration
from .classifier import RuleClassifier
from .config import get_settings
from .models import ProcessedBlockRecord, RawEventRecord, ReportRecord, SessionRecord
from .reporting import generate_report_markdown, write_report_file
from .schemas import ActivityBlock


MERGE_GAP_SECONDS = 90


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_active_session(db: Session) -> SessionRecord | None:
    return db.scalar(select(SessionRecord).where(SessionRecord.status.in_(["active", "processing"])).order_by(SessionRecord.id.desc()))


def start_session(db: Session) -> SessionRecord:
    existing = get_active_session(db)
    if existing and existing.status == "active":
        raise HTTPException(status_code=409, detail="A session is already active.")
    session = SessionRecord(started_at=utcnow(), status="active", updated_at=utcnow(), created_at=utcnow())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def stop_session(db: Session) -> tuple[SessionRecord, ReportRecord]:
    session = db.scalar(select(SessionRecord).where(SessionRecord.status == "active").order_by(SessionRecord.id.desc()))
    if session is None:
        raise HTTPException(status_code=404, detail="No active session found.")

    settings = get_settings()
    session.ended_at = utcnow()
    session.status = "processing"
    session.updated_at = utcnow()
    db.commit()
    db.refresh(session)

    try:
        report = _process_session(db, session, settings.activitywatch_base_url)
        session.status = "completed"
        session.updated_at = utcnow()
        db.commit()
        db.refresh(session)
        return session, report
    except Exception as exc:  # noqa: BLE001
        session.status = "error"
        session.error_message = str(exc)
        session.updated_at = utcnow()
        db.commit()
        raise


def _process_session(db: Session, session: SessionRecord, activitywatch_base_url: str) -> ReportRecord:
    if session.ended_at is None:
        raise RuntimeError("Session must have an end time before processing.")

    db.query(RawEventRecord).filter(RawEventRecord.session_id == session.id).delete()
    db.query(ProcessedBlockRecord).filter(ProcessedBlockRecord.session_id == session.id).delete()
    db.query(ReportRecord).filter(ReportRecord.session_id == session.id).delete()
    db.commit()

    aw_client = ActivityWatchClient(activitywatch_base_url)
    window_events = aw_client.fetch_window_events(session.started_at, session.ended_at)
    afk_events = aw_client.fetch_afk_events(session.started_at, session.ended_at)

    for event in [*window_events, *afk_events]:
        db.add(
            RawEventRecord(
                session_id=session.id,
                source_bucket=event.source_bucket,
                event_type=event.event_type,
                start=event.start,
                end=event.end,
                duration_seconds=event.duration_seconds,
                app=event.app,
                title=event.title,
                url_or_domain=event.url_or_domain,
                payload_json=event.payload_json,
            )
        )
    db.commit()

    classifier = RuleClassifier.from_database(db)
    processed_blocks = _build_processed_blocks(window_events, afk_events, classifier)
    for block in processed_blocks:
        db.add(
            ProcessedBlockRecord(
                session_id=session.id,
                start=block.start,
                end=block.end,
                duration_seconds=block.duration_seconds,
                app=block.app,
                context=block.context,
                category=block.category,
                is_work=block.is_work,
                confidence=block.confidence,
            )
        )
    db.commit()

    work_blocks = [block for block in processed_blocks if block.is_work]
    excluded_non_work_seconds = sum(block.duration_seconds for block in processed_blocks if not block.is_work)

    settings = get_settings()
    markdown = generate_report_markdown(
        settings=settings,
        session_id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        work_blocks=work_blocks,
        excluded_non_work_seconds=excluded_non_work_seconds,
    )
    created_at = utcnow()
    file_path = write_report_file(settings.reports_dir, session.id, markdown, created_at)
    report = ReportRecord(
        session_id=session.id,
        created_at=created_at,
        markdown=markdown,
        file_path=str(file_path.resolve()),
        excluded_non_work_seconds=excluded_non_work_seconds,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _build_processed_blocks(
    window_events: list[NormalizedEvent],
    afk_events: list[NormalizedEvent],
    classifier: RuleClassifier,
) -> list[ActivityBlock]:
    blocks: list[ActivityBlock] = []
    for event in window_events:
        overlap = overlap_duration(event.start, event.end, afk_events)
        adjusted_duration = max(0.0, event.duration_seconds - overlap)
        if adjusted_duration <= 0:
            continue
        classification = classifier.classify(event.app, event.title, event.url_or_domain)
        context = event.title or event.url_or_domain
        candidate = ActivityBlock(
            start=event.start,
            end=event.end,
            duration_seconds=adjusted_duration,
            app=event.app,
            context=context,
            category=classification.category,
            is_work=classification.is_work,
            confidence=classification.confidence,
            label=classification.label,
        )
        if blocks and _can_merge(blocks[-1], candidate):
            previous = blocks[-1]
            previous.end = candidate.end
            previous.duration_seconds += candidate.duration_seconds
            previous.confidence = max(previous.confidence, candidate.confidence)
            if previous.context is None:
                previous.context = candidate.context
            continue
        blocks.append(candidate)
    return blocks


def _can_merge(existing: ActivityBlock, candidate: ActivityBlock) -> bool:
    gap = (candidate.start - existing.end).total_seconds()
    return (
        gap <= MERGE_GAP_SECONDS
        and existing.app == candidate.app
        and existing.context == candidate.context
        and existing.category == candidate.category
        and existing.is_work == candidate.is_work
    )
