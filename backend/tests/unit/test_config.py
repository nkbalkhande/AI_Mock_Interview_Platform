"""Tests for YAML-backed application settings."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import CONFIG_YAML_PATH, LLM_YAML_PATH, Settings, get_settings, settings
from app.main import create_app


def test_config_yaml_exists() -> None:
    assert CONFIG_YAML_PATH.is_file()
    assert CONFIG_YAML_PATH.name == "config.yaml"
    assert LLM_YAML_PATH.is_file()
    assert LLM_YAML_PATH.name == "llm.yaml"


def test_settings_load_interview_defaults_from_yaml() -> None:
    loaded = get_settings()
    assert loaded.app.name == "AI Mock Interview Platform"
    assert loaded.llm.provider == "litellm"
    assert "/" in loaded.llm.model
    assert loaded.embedding.model
    assert loaded.embedding.dimensions == loaded.vectordb.qdrant.dense_dim
    assert loaded.interview.jd_min_chars == 200
    assert loaded.interview.target_questions(15) == 8
    assert loaded.interview.target_questions(30) == 14
    assert loaded.interview.target_questions(45) == 15
    assert loaded.interview.target_questions(60) == 15
    assert loaded.interview.target_questions(90) == 17


def test_public_config_exposes_no_secrets() -> None:
    payload = settings.public_config()
    blob = str(payload).lower()
    assert "api_key" not in blob
    assert "password" not in blob
    assert "secret" not in blob
    assert payload["interview"]["jd_min_chars"] == 200
    assert payload["interview"]["duration_options"][0]["question_count"] == 8


def test_public_config_endpoint() -> None:
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/v1/config/public")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app_name"] == "AI Mock Interview Platform"
    assert body["interview"]["default_duration_minutes"] == 30
    assert len(body["interview"]["duration_options"]) == 4


def test_env_overrides_yaml_model(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("LLM__MODEL", "gpt-4o")
    get_settings.cache_clear()
    try:
        loaded = Settings()
        assert loaded.llm.model == "gpt-4o"
    finally:
        get_settings.cache_clear()
