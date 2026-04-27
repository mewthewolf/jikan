from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from .config import Settings
from .schemas import ActivityBlock


def build_structured_summary(
    session_id: int,
    started_at: datetime,
    ended_at: datetime,
    work_blocks: list[ActivityBlock],
    excluded_non_work_seconds: float,
) -> str:
    lines = [
        f"Session ID: {session_id}",
        f"Start: {started_at.astimezone(timezone.utc).isoformat()}",
        f"End: {ended_at.astimezone(timezone.utc).isoformat()}",
        "",
        "Work blocks:",
    ]
    category_totals: dict[str, float] = defaultdict(float)
    for block in work_blocks:
        category_totals[block.category] += block.duration_seconds
        lines.append(
            "- "
            f"{block.category}: {block.app} | {block.context or 'No context'} | "
            f"{int(block.duration_seconds // 60)} minutes"
        )
    lines.append("")
    lines.append("Category totals:")
    for category, seconds in sorted(category_totals.items()):
        lines.append(f"- {category}: {int(seconds // 60)} minutes")
    lines.append("")
    lines.append(f"Excluded non-work minutes: {int(excluded_non_work_seconds // 60)}")
    return "\n".join(lines)


def fallback_report(
    session_id: int,
    started_at: datetime,
    ended_at: datetime,
    work_blocks: list[ActivityBlock],
    excluded_non_work_seconds: float,
) -> str:
    summary = build_structured_summary(session_id, started_at, ended_at, work_blocks, excluded_non_work_seconds)
    return (
        f"# Session Report\n\n"
        f"- Session: `{session_id}`\n"
        f"- Start: `{started_at.isoformat()}`\n"
        f"- End: `{ended_at.isoformat()}`\n"
        f"- Work blocks: `{len(work_blocks)}`\n"
        f"- Excluded non-work: `{int(excluded_non_work_seconds // 60)} minutes`\n\n"
        f"## Structured Summary\n\n{summary}\n"
    )


def generate_report_markdown(
    settings: Settings,
    session_id: int,
    started_at: datetime,
    ended_at: datetime,
    work_blocks: list[ActivityBlock],
    excluded_non_work_seconds: float,
) -> str:
    if not settings.openai_api_key:
        return fallback_report(session_id, started_at, ended_at, work_blocks, excluded_non_work_seconds)

    client = OpenAI(api_key=settings.openai_api_key)
    structured_summary = build_structured_summary(
        session_id=session_id,
        started_at=started_at,
        ended_at=ended_at,
        work_blocks=work_blocks,
        excluded_non_work_seconds=excluded_non_work_seconds,
    )
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": settings.report_prompt_template}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": structured_summary}],
            },
        ],
    )
    text = getattr(response, "output_text", "").strip()
    if not text:
        return fallback_report(session_id, started_at, ended_at, work_blocks, excluded_non_work_seconds)
    return text


def write_report_file(reports_dir: Path, session_id: int, markdown: str, created_at: datetime) -> Path:
    filename = f"session-{session_id}-{created_at.strftime('%Y%m%d-%H%M%S')}.md"
    path = reports_dir / filename
    path.write_text(markdown, encoding="utf-8")
    return path
