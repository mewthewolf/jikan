from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ClassificationRuleRecord


@dataclass(slots=True)
class ClassificationRule:
    rule_id: str
    name: str
    match_app: str | None
    match_domain: str | None
    match_title: str | None
    category: str
    is_work: bool
    label_override: str | None
    priority: int


@dataclass(slots=True)
class ClassificationResult:
    category: str
    is_work: bool
    confidence: float
    label: str | None = None


class RuleClassifier:
    def __init__(self, rules: list[ClassificationRule]) -> None:
        self.rules = sorted(rules, key=lambda rule: rule.priority, reverse=True)

    @classmethod
    def from_database(cls, db: Session) -> "RuleClassifier":
        rules = db.scalars(select(ClassificationRuleRecord)).all()
        return cls(
            [
                ClassificationRule(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    match_app=rule.match_app,
                    match_domain=rule.match_domain,
                    match_title=rule.match_title,
                    category=rule.category,
                    is_work=rule.is_work,
                    label_override=rule.label_override,
                    priority=rule.priority,
                )
                for rule in rules
            ]
        )

    @staticmethod
    def load_rule_file(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("Classification rules file must contain a list.")
        return data

    @classmethod
    def sync_rule_file_to_database(cls, db: Session, path: Path) -> int:
        raw_rules = cls.load_rule_file(path)
        db.query(ClassificationRuleRecord).delete()
        for item in raw_rules:
            db.add(
                ClassificationRuleRecord(
                    rule_id=item["rule_id"],
                    name=item["name"],
                    match_app=(item.get("match_app") or None),
                    match_domain=(item.get("match_domain") or None),
                    match_title=(item.get("match_title") or None),
                    category=item["category"],
                    is_work=bool(item["is_work"]),
                    label_override=(item.get("label_override") or None),
                    priority=int(item.get("priority", 0)),
                )
            )
        db.commit()
        return len(raw_rules)

    def classify(self, app: str, title: str | None, domain: str | None) -> ClassificationResult:
        normalized_app = (app or "").casefold()
        normalized_title = (title or "").casefold()
        normalized_domain = (domain or "").casefold()

        best_match: tuple[int, ClassificationRule] | None = None
        for rule in self.rules:
            specificity = 0
            if rule.match_title:
                if rule.match_title.casefold() not in normalized_title:
                    continue
                specificity = max(specificity, 3)
            if rule.match_domain:
                if rule.match_domain.casefold() not in normalized_domain:
                    continue
                specificity = max(specificity, 2)
            if rule.match_app:
                if rule.match_app.casefold() not in normalized_app:
                    continue
                specificity = max(specificity, 1)
            if specificity == 0:
                continue
            candidate = (specificity, rule)
            if best_match is None or candidate[0] > best_match[0] or (
                candidate[0] == best_match[0] and rule.priority > best_match[1].priority
            ):
                best_match = candidate

        if best_match is None:
            return ClassificationResult(category="uncategorized", is_work=True, confidence=0.1)

        specificity, rule = best_match
        confidence = {1: 0.5, 2: 0.75, 3: 0.95}[specificity]
        if not rule.is_work:
            confidence = max(confidence, 0.9)
        return ClassificationResult(
            category=rule.category,
            is_work=rule.is_work,
            confidence=confidence,
            label=rule.label_override,
        )
