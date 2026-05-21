import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.config.settings import Settings


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    settings = Settings(
        app_name="Panvel AI Assistant API",
        app_version="0.1.0",
        environment="test",
        debug=False,
        log_level="INFO",
        llm_provider="mock",
        llm_model="gpt-4o-mini",
        openai_api_key=None,
        embedding_provider="mock",
        vector_store_path=Path(__file__).resolve().parents[1] / ".vector_store",
    )
    monkeypatch.setattr("app.application.services.chat.get_settings", lambda: settings)
    return settings


def test_chat_orchestration_rag_flow(mock_settings: Settings) -> None:
    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-rag",
            "message": "Para que serve a losartana?",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    assert response.status_code == 200
    assert "event: trace" in body
    assert '"step": "routing"' in body
    assert 'rag' in body
    
    assert '"step": "retrieval"' in body
    
    # Check that we got sources
    assert "event: source" in body
    assert '"arquivo":' in body
    
    # Final done event
    assert "event: done" in body
    assert '"provider": "mock"' in body


def test_chat_orchestration_buscar_filiais_flow(mock_settings: Settings) -> None:
    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-tool-buscar",
            "message": "Quais filiais em Curitiba têm Panvel Clinic?",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    assert response.status_code == 200
    assert "event: trace" in body
    assert '"step": "routing"' in body
    assert 'buscar_filiais' in body
    assert '"step": "tool_call"' in body
    
    # Should emit tool_call event
    assert "event: tool_call" in body
    assert '"tool_name": "buscar_filiais"' in body
    assert '"cidade": "Curitiba"' in body
    assert '"panvel_clinic": true' in body
    
    # Final response
    assert "event: token" in body
    assert "event: done" in body


def test_chat_orchestration_detalhes_filial_flow(mock_settings: Settings) -> None:
    client = TestClient(app)

    # Let's request details for filial 822 (which exists in standard PR dataset)
    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-tool-detalhes",
            "message": "Me mostre os detalhes da filial de código 822",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    assert response.status_code == 200
    assert "event: trace" in body
    assert '"step": "routing"' in body
    assert 'detalhes_filial' in body
    assert '"step": "tool_call"' in body
    
    # Should emit tool_call event
    assert "event: tool_call" in body
    assert '"tool_name": "detalhes_filial"' in body
    
    # Final response
    assert "event: token" in body
    assert "event: done" in body


def test_chat_orchestration_direct_flow(mock_settings: Settings) -> None:
    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-direct",
            "message": "Olá, tudo bem?",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    assert response.status_code == 200
    assert "event: trace" in body
    assert '"step": "routing"' in body
    assert 'direct' in body
    
    # No tool calls or sources should be present
    assert "event: tool_call" not in body
    assert "event: source" not in body
    
    # Tokens and done
    assert "event: token" in body
    assert "event: done" in body
