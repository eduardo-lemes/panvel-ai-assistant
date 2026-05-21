from pathlib import Path

import pytest

from app.infrastructure.config.settings import Settings
from app.infrastructure.llm.factory import build_llm_provider
from app.infrastructure.llm.mock_provider import MockLLMProvider
from app.infrastructure.llm.openai_provider import OpenAILLMProvider


def _make_settings(**overrides) -> Settings:
    """Cria Settings de teste com valores padrão para todos os campos."""
    defaults = dict(
        app_name="Panvel AI Assistant API",
        app_version="0.1.0",
        environment="test",
        debug=False,
        log_level="INFO",
        llm_provider="mock",
        llm_model="mock-model",
        openai_api_key=None,
        embedding_provider="mock",
        vector_store_path=Path("/tmp/test_vector_store"),
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_build_llm_provider_returns_mock_provider() -> None:
    settings = _make_settings(llm_provider="mock", llm_model="mock-model", openai_api_key=None)

    provider = build_llm_provider(settings)

    assert isinstance(provider, MockLLMProvider)


def test_build_llm_provider_requires_api_key_for_openai() -> None:
    settings = _make_settings(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        openai_api_key=None,
    )

    with pytest.raises(ValueError):
        build_llm_provider(settings)


def test_build_llm_provider_returns_openai_provider_when_api_key_exists() -> None:
    settings = _make_settings(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        openai_api_key="test-key",
    )

    provider = build_llm_provider(settings)

    assert isinstance(provider, OpenAILLMProvider)


def test_build_llm_provider_requires_api_key_for_gemini() -> None:
    settings = _make_settings(
        llm_provider="gemini",
        llm_model="gemini-2.0-flash",
        gemini_api_key=None,
    )

    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        build_llm_provider(settings)


def test_build_llm_provider_returns_gemini_provider_when_api_key_exists() -> None:
    from app.infrastructure.llm.gemini_provider import GeminiLLMProvider

    settings = _make_settings(
        llm_provider="gemini",
        llm_model="gemini-2.0-flash",
        gemini_api_key="test-key",
    )

    provider = build_llm_provider(settings)

    assert isinstance(provider, GeminiLLMProvider)

