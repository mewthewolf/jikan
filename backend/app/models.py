from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    raw_events: Mapped[list["RawEventRecord"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    processed_blocks: Mapped[list["ProcessedBlockRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class RawEventRecord(Base):
    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    source_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    app: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_or_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[SessionRecord] = relationship(back_populates="raw_events")


class ProcessedBlockRecord(Base):
    __tablename__ = "processed_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    app: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    is_work: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    session: Mapped[SessionRecord] = relationship(back_populates="processed_blocks")


class ClassificationRuleRecord(Base):
    __tablename__ = "classification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    match_app: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    is_work: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    label_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    excluded_non_work_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    session: Mapped[SessionRecord] = relationship(back_populates="reports")
