from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.application.interfaces.llm import LLMProvider
from app.domain.models.llm import LLMCompletionResult
from app.infrastructure.config.settings import get_settings
from app.infrastructure.llm.factory import build_llm_provider


def test_chat_stream_emits_trace_token_and_done_events(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path
    from app.infrastructure.config.settings import Settings

    mock_settings = Settings(
        app_name="Panvel AI Assistant API",
        app_version="0.1.0",
        environment="test",
        debug=False,
        log_level="INFO",
        llm_provider="mock",
        llm_model="gpt-4o-mini",
        openai_api_key=None,
        embedding_provider="mock",
        vector_store_path=Path("/tmp/test_vector_store"),
    )
    monkeypatch.setattr("app.application.services.chat.get_settings", lambda: mock_settings)

    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-123",
            "message": "Quais filiais atendem em Curitiba?",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: trace" in body
    assert "event: token" in body
    assert "event: done" in body
    assert '"trace_id":' in body
    assert '"conversation_id": "conv-123"' in body
    assert '"provider": "mock"' in body
    assert '"model": "gpt-4o-mini"' in body


def test_chat_stream_emits_error_event_when_provider_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingProvider(LLMProvider):
        def complete(self, message: str, system_prompt: str) -> LLMCompletionResult:
            del message, system_prompt
            raise RuntimeError("forced provider failure")

    monkeypatch.setattr(
        "app.application.services.chat.build_llm_provider",
        lambda settings: FailingProvider(),
    )

    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-err",
            "message": "Teste de erro",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    assert response.status_code == 200
    assert "event: trace" in body
    assert "event: error" in body
    assert "event: done" in body
    assert '"error_code": "RuntimeError"' in body
