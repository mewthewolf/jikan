from pathlib import Path

from app.classifier import RuleClassifier
from app.db import Base, SessionLocal, engine


def setup_module():
    Base.metadata.create_all(bind=engine)
    RuleClassifier.sync_rule_file_to_database(SessionLocal(), Path("app/classification_rules.json"))


def test_domain_rule_beats_app_rule():
    db = SessionLocal()
    classifier = RuleClassifier.from_database(db)
    result = classifier.classify(app="Code", title="YouTube video", domain="youtube.com")
    assert result.category == "non-work"
    assert result.is_work is False


def test_default_falls_back_to_uncategorized():
    db = SessionLocal()
    classifier = RuleClassifier.from_database(db)
    result = classifier.classify(app="Unknown", title="Misc", domain=None)
    assert result.category == "uncategorized"
    assert result.is_work is True
