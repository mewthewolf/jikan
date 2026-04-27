from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx


@dataclass(slots=True)
class NormalizedEvent:
    source_bucket: str
    event_type: str
    start: datetime
    end: datetime
    duration_seconds: float
    app: str
    title: str | None
    url_or_domain: str | None
    payload_json: str | None = None


class ActivityWatchClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_buckets(self) -> list[dict[str, Any]]:
        response = httpx.get(f"{self.base_url}/buckets", timeout=15.0)
        response.raise_for_status()
        return list(response.json().values())

    def get_events(self, bucket_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
        params = {
            "start": start.astimezone(timezone.utc).isoformat(),
            "end": end.astimezone(timezone.utc).isoformat(),
        }
        response = httpx.get(f"{self.base_url}/buckets/{bucket_id}/events", params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def find_bucket_ids(self) -> tuple[list[str], list[str]]:
        buckets = self.get_buckets()
        window_bucket_ids = [bucket["id"] for bucket in buckets if bucket["id"].startswith("aw-watcher-window")]
        afk_bucket_ids = [bucket["id"] for bucket in buckets if bucket["id"].startswith("aw-watcher-afk")]
        return window_bucket_ids, afk_bucket_ids

    def fetch_window_events(self, start: datetime, end: datetime) -> list[NormalizedEvent]:
        window_bucket_ids, _ = self.find_bucket_ids()
        events: list[NormalizedEvent] = []
        for bucket_id in window_bucket_ids:
            for event in self.get_events(bucket_id, start, end):
                events.append(self._normalize_window_event(bucket_id, event))
        return sorted(events, key=lambda event: event.start)

    def fetch_afk_events(self, start: datetime, end: datetime) -> list[NormalizedEvent]:
        _, afk_bucket_ids = self.find_bucket_ids()
        events: list[NormalizedEvent] = []
        for bucket_id in afk_bucket_ids:
            for event in self.get_events(bucket_id, start, end):
                normalized = self._normalize_afk_event(bucket_id, event)
                if normalized is not None:
                    events.append(normalized)
        return sorted(events, key=lambda event: event.start)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _normalize_window_event(self, bucket_id: str, event: dict[str, Any]) -> NormalizedEvent:
        data = event.get("data", {})
        title = data.get("title")
        url = data.get("url")
        app = data.get("app") or data.get("app_name") or "Unknown"
        parsed_domain = urlparse(url).netloc if url else None
        start = self._parse_timestamp(event["timestamp"])
        duration = float(event.get("duration", 0))
        end = start + self._duration_to_delta(duration)
        return NormalizedEvent(
            source_bucket=bucket_id,
            event_type="window",
            start=start,
            end=end,
            duration_seconds=duration,
            app=app,
            title=title,
            url_or_domain=parsed_domain or url,
            payload_json=None,
        )

    def _normalize_afk_event(self, bucket_id: str, event: dict[str, Any]) -> NormalizedEvent | None:
        data = event.get("data", {})
        status = (data.get("status") or "").casefold()
        if status != "afk":
            return None
        start = self._parse_timestamp(event["timestamp"])
        duration = float(event.get("duration", 0))
        end = start + self._duration_to_delta(duration)
        return NormalizedEvent(
            source_bucket=bucket_id,
            event_type="afk",
            start=start,
            end=end,
            duration_seconds=duration,
            app="AFK",
            title="AFK",
            url_or_domain=None,
            payload_json=None,
        )

    @staticmethod
    def _duration_to_delta(duration_seconds: float):
        from datetime import timedelta

        return timedelta(seconds=duration_seconds)


def overlap_duration(start: datetime, end: datetime, afk_events: Iterable[NormalizedEvent]) -> float:
    total = 0.0
    for afk in afk_events:
        overlap_start = max(start, afk.start)
        overlap_end = min(end, afk.end)
        if overlap_end > overlap_start:
            total += (overlap_end - overlap_start).total_seconds()
    return total
