"""Application configuration.

Tunables are loaded from ``settings/config.yaml`` at the repo root.
Secrets and local overrides come from environment variables / ``.env``.

Import the singleton ``settings`` object everywhere instead of reading
``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, PostgresDsn, computed_field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

# backend/app/core/config.py → repo root is parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_YAML_PATH = _REPO_ROOT / "settings" / "config.yaml"
LLM_YAML_PATH = _REPO_ROOT / "settings" / "llm.yaml"


class AppSettings(BaseModel):
    name: str = "AI Mock Interview Platform"
    env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    default_page_size: int = 20
    max_page_size: int = 100

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}


class AzureProviderSettings(BaseModel):
    api_base: str | None = None
    api_version: str = "2024-08-01-preview"


class LLMProviders(BaseModel):
    openai: dict[str, Any] = Field(default_factory=dict)
    azure: AzureProviderSettings = Field(default_factory=AzureProviderSettings)
    anthropic: dict[str, Any] = Field(default_factory=dict)
    gemini: dict[str, Any] = Field(default_factory=dict)


class LLMSettings(BaseModel):
    provider: str = "litellm"
    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.4
    max_completion_tokens: int = 2000
    timeout: float = 45.0
    kwargs: dict[str, Any] = Field(default_factory=dict)
    providers: LLMProviders = Field(default_factory=LLMProviders)


class EmbeddingSettings(BaseModel):
    provider: str = "litellm"
    model: str = "openai/text-embedding-3-small"
    dimensions: int = 1536
    timeout: float = 60.0


class QdrantSettings(BaseModel):
    host: str = "localhost"
    port: int = 6533
    timeout: float = 120.0
    dense_dim: int = 1536
    https: bool = False


class VectorDBSettings(BaseModel):
    provider: str = "qdrant"
    collection: str = "resume_chunks"
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)


class PostgresSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    db: str = "AI_Interview_DB"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0


class CelerySettings(BaseModel):
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"


class AuthSettings(BaseModel):
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    access_cookie_name: str = "session"
    refresh_cookie_name: str = "refresh_token"


class StorageSettings(BaseModel):
    backend: str = "local"
    root: str = "./storage"
    max_upload_size_mb: int = 10


class VoiceSettings(BaseModel):
    stt_model: str = "whisper-large-v3-turbo"
    tts_voice: str = "af_heart"
    tts_speed: float = 1.0
    max_audio_upload_mb: int = 25


class ResumeSettings(BaseModel):
    chunk_size_chars: int = 20000
    chunk_overlap_chars: int = 500
    ingestion_timeout_seconds: int = 600
    snapshot_char_limit: int = 12000


class DurationBand(BaseModel):
    max_minutes: int
    questions: int


class DurationOption(BaseModel):
    minutes: int
    label: str


class InterviewSettings(BaseModel):
    duration_min_minutes: int = 15
    duration_max_minutes: int = 90
    default_duration_minutes: int = 30
    hard_question_cap: int = 20
    jd_min_chars: int = 200
    jd_max_chars: int = 20000
    evaluation_lease_minutes: int = 5
    access_open_minutes_before: int = 5
    access_close_minutes_after_duration: int = 10
    role_requirements_max_items: int = 20
    role_requirement_max_chars: int = 300
    role_skills_max_items: int = 30
    role_skill_max_chars: int = 100
    extra_question_every_minutes: int = 15
    duration_question_counts: list[DurationBand] = Field(
        default_factory=lambda: [
            DurationBand(max_minutes=15, questions=8),
            DurationBand(max_minutes=30, questions=14),
            DurationBand(max_minutes=45, questions=15),
            DurationBand(max_minutes=60, questions=15),
        ]
    )
    duration_options: list[DurationOption] = Field(
        default_factory=lambda: [
            DurationOption(minutes=15, label="15 min"),
            DurationOption(minutes=30, label="30 min"),
            DurationOption(minutes=45, label="45 min"),
            DurationOption(minutes=60, label="60 min"),
        ]
    )

    def target_questions(self, duration_minutes: int) -> int:
        """Map interview duration onto the planned question count."""
        duration = max(1, int(duration_minutes))
        bands = sorted(self.duration_question_counts, key=lambda item: item.max_minutes)
        for band in bands:
            if duration <= band.max_minutes:
                return band.questions
        last = bands[-1] if bands else DurationBand(max_minutes=60, questions=9)
        extra = (duration - last.max_minutes) // max(
            1, self.extra_question_every_minutes
        )
        return min(self.hard_question_cap - 2, last.questions + extra)


class LoggingSettings(BaseModel):
    level: str = "INFO"
    file_path: str | None = None


class LlmYamlSettingsSource(PydanticBaseSettingsSource):
    """Load ``settings/llm.yaml`` into the ``llm`` / ``embedding`` fields."""

    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False

    def __call__(self) -> dict[str, Any]:
        if not LLM_YAML_PATH.is_file():
            return {}
        raw = yaml.safe_load(LLM_YAML_PATH.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"{LLM_YAML_PATH} must be a mapping")
        payload: dict[str, Any] = {}
        embedding = raw.pop("embedding", None)
        if embedding is not None:
            payload["embedding"] = embedding
        if raw:
            payload["llm"] = raw
        return payload


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
        yaml_file=str(CONFIG_YAML_PATH),
        yaml_file_encoding="utf-8",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    vectordb: VectorDBSettings = Field(default_factory=VectorDBSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    resume: ResumeSettings = Field(default_factory=ResumeSettings)
    interview: InterviewSettings = Field(default_factory=InterviewSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # Secrets and connection-string overrides — environment only.
    OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    POSTGRES_PASSWORD: str = "postgres"
    JWT_SECRET_KEY: str = "change-me-in-production"
    QDRANT_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    DATABASE_URL: str | None = None
    SYNC_DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_source = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=str(CONFIG_YAML_PATH),
            yaml_file_encoding="utf-8",
        )
        llm_yaml_source = LlmYamlSettingsSource(settings_cls)
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            llm_yaml_source,
            yaml_source,
            file_secret_settings,
        )

    @model_validator(mode="after")
    def _check_embedding_dim_matches_qdrant(self) -> Settings:
        if self.embedding.dimensions != self.vectordb.qdrant.dense_dim:
            raise ValueError(
                "embedding.dimensions must match vectordb.qdrant.dense_dim "
                f"({self.embedding.dimensions} != {self.vectordb.qdrant.dense_dim})."
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        """SQLAlchemy async URL (asyncpg) used by the application at runtime."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres.user,
                password=self.POSTGRES_PASSWORD,
                host=self.postgres.host,
                port=self.postgres.port,
                path=self.postgres.db,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Synchronous URL (psycopg) used by Alembic migrations."""
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.postgres.user,
                password=self.POSTGRES_PASSWORD,
                host=self.postgres.host,
                port=self.postgres.port,
                path=self.postgres.db,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return (
            f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"
        )

    @property
    def is_production(self) -> bool:
        return self.app.is_production

    def public_config(self) -> dict[str, Any]:
        """Non-secret values the frontend needs to stay in lockstep with YAML."""
        interview = self.interview
        return {
            "app_name": self.app.name,
            "interview": {
                "jd_min_chars": interview.jd_min_chars,
                "jd_max_chars": interview.jd_max_chars,
                "default_duration_minutes": interview.default_duration_minutes,
                "duration_min_minutes": interview.duration_min_minutes,
                "duration_max_minutes": interview.duration_max_minutes,
                "role_requirements_max_items": interview.role_requirements_max_items,
                "role_requirement_max_chars": interview.role_requirement_max_chars,
                "role_skills_max_items": interview.role_skills_max_items,
                "role_skill_max_chars": interview.role_skill_max_chars,
                "duration_options": [
                    {
                        "minutes": option.minutes,
                        "label": option.label,
                        "question_count": interview.target_questions(option.minutes),
                    }
                    for option in interview.duration_options
                ],
            },
        }


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (single load per process)."""
    return Settings()


settings = get_settings()
