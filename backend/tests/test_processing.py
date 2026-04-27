from datetime import UTC, datetime, timedelta

from app.activitywatch import NormalizedEvent
from app.classifier import ClassificationRule
from app.services import _build_processed_blocks


def test_afk_overlap_reduces_duration_and_merges():
    classifier = type(
        "StubClassifier",
        (),
        {
            "classify": lambda self, app, title, domain: type(
                "Result",
                (),
                {
                    "category": "development",
                    "is_work": True,
                    "confidence": 0.8,
                    "label": "Software development",
                },
            )()
        },
    )()
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    events = [
        NormalizedEvent(
            source_bucket="aw-watcher-window_test",
            event_type="window",
            start=start,
            end=start + timedelta(minutes=10),
            duration_seconds=600,
            app="Code",
            title="Project",
            url_or_domain=None,
        ),
        NormalizedEvent(
            source_bucket="aw-watcher-window_test",
            event_type="window",
            start=start + timedelta(minutes=10, seconds=30),
            end=start + timedelta(minutes=20, seconds=30),
            duration_seconds=600,
            app="Code",
            title="Project",
            url_or_domain=None,
        ),
    ]
    afk = [
        NormalizedEvent(
            source_bucket="aw-watcher-afk_test",
            event_type="afk",
            start=start + timedelta(minutes=5),
            end=start + timedelta(minutes=7),
            duration_seconds=120,
            app="AFK",
            title="AFK",
            url_or_domain=None,
        )
    ]
    blocks = _build_processed_blocks(events, afk, classifier)
    assert len(blocks) == 1
    assert int(blocks[0].duration_seconds) == 1080
