"""Application-level settings via pydantic-settings."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sensor_db_path: str = "sensor_data.db"
    metrics_db_path: str = "metrics.db"
    schema_path: str = "sensor_schema.json"

    llm_provider: Literal["claude", "ollama"] = "claude"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"


def get_settings() -> Settings:
    return Settings()
