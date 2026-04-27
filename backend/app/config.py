from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Jikan Backend"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = "sqlite:///./data/jikan.db"
    activitywatch_base_url: str = "http://127.0.0.1:5600/api/0"
    reports_dir: Path = Path("./reports")
    classification_rules_path: Path = Path("./app/classification_rules.json")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4.1-mini"
    report_prompt_template: str = (
        "You are generating a concise professional work session report from structured "
        "activity blocks. Focus on work activity, summarize outcomes, group related work, "
        "and mention excluded non-work time only briefly. Return Markdown."
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.classification_rules_path.parent.mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    return settings
