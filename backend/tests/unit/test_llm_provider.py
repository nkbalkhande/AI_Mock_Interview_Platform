"""Tests for LiteLLM model-id and credential resolution."""

from __future__ import annotations

import pytest

from app.ai.llm.provider import (
    credentials_for,
    normalize_model_id,
    provider_from_model,
    temperature_kwargs,
    token_limit_kwargs,
    uses_max_completion_tokens,
)
from app.core.config import get_settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("gpt-5", "openai/gpt-5"),
        ("openai/gpt-5", "openai/gpt-5"),
        ("gpt-4o-mini", "openai/gpt-4o-mini"),
        ("azure/gpt-4o", "azure/gpt-4o"),
        ("anthropic/claude-sonnet-4-5", "anthropic/claude-sonnet-4-5"),
        ("claude-sonnet-4-5", "anthropic/claude-sonnet-4-5"),
        ("gemini/gemini-2.0-flash", "gemini/gemini-2.0-flash"),
        ("gemini-2.0-flash", "gemini/gemini-2.0-flash"),
        ("text-embedding-3-small", "openai/text-embedding-3-small"),
    ],
)
def test_normalize_model_id(raw: str, expected: str) -> None:
    assert normalize_model_id(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("openai/gpt-4o-mini", "openai"),
        ("azure/gpt-4o", "azure"),
        ("claude-sonnet-4-5", "anthropic"),
        ("gemini/gemini-2.0-flash", "gemini"),
        ("google/gemini-2.0-flash", "gemini"),
    ],
)
def test_provider_from_model(raw: str, expected: str) -> None:
    assert provider_from_model(raw) == expected


def test_openai_credentials_come_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.ai.llm.provider.settings.OPENAI_API_KEY", "sk-test-openai"
    )
    creds = credentials_for("openai/gpt-4o-mini")
    assert creds == {"api_key": "sk-test-openai"}


def test_azure_credentials_include_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.ai.llm.provider.settings.AZURE_OPENAI_API_KEY", "sk-azure"
    )
    monkeypatch.setattr(
        "app.ai.llm.provider.settings.AZURE_OPENAI_ENDPOINT",
        "https://example.openai.azure.com",
    )
    creds = credentials_for("azure/gpt-4o")
    assert creds["api_key"] == "sk-azure"
    assert creds["api_base"] == "https://example.openai.azure.com"
    assert creds["api_version"] == get_settings().llm.providers.azure.api_version


def test_missing_key_explains_which_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ai.llm.provider.settings.ANTHROPIC_API_KEY", None)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        credentials_for("anthropic/claude-sonnet-4-5")


@pytest.mark.parametrize(
    ("model", "expected_key"),
    [
        ("openai/gpt-5", "max_completion_tokens"),
        ("gpt-5-mini", "max_completion_tokens"),
        ("azure/gpt-5", "max_completion_tokens"),
        ("o3-mini", "max_completion_tokens"),
        ("openai/gpt-4o-mini", "max_tokens"),
        ("anthropic/claude-sonnet-4-5", "max_tokens"),
        ("gemini/gemini-2.0-flash", "max_tokens"),
    ],
)
def test_token_limit_kwargs_match_model_family(model: str, expected_key: str) -> None:
    payload = token_limit_kwargs(model, 8192)
    assert payload == {expected_key: 8192}
    assert uses_max_completion_tokens(model) is (expected_key == "max_completion_tokens")


def test_gpt5_omits_custom_temperature() -> None:
    assert temperature_kwargs("openai/gpt-5", 0.4) == {}
    assert temperature_kwargs("o3-mini", 0.2) == {}
    assert temperature_kwargs("openai/gpt-4o-mini", 0.4) == {"temperature": 0.4}
