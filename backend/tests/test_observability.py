import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.config.settings import Settings
from app.observability.traces import trace_repository


@pytest.fixture(autouse=True)
def clean_repository() -> None:
    trace_repository.clear()


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


def test_observability_records_trace_on_direct_chat(mock_settings: Settings) -> None:
    client = TestClient(app)

    # 1. Send chat message
    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-obs-direct",
            "message": "Olá assistente!",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    # 2. Extract trace_id from the first trace event
    trace_id = None
    for line in body.split("\n"):
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "trace_id" in data:
                trace_id = data["trace_id"]
                break

    assert trace_id is not None

    # 3. Retrieve trace via API GET endpoint
    trace_response = client.get(f"/chat/traces/{trace_id}")
    assert trace_response.status_code == 200
    trace_data = trace_response.json()

    assert trace_data["trace_id"] == trace_id
    assert trace_data["conversation_id"] == "conv-obs-direct"
    assert trace_data["prompt"] == "Olá assistente!"
    assert "Olá!" in trace_data["answer"]
    assert trace_data["model"] == "gpt-4o-mini"
    assert trace_data["provider"] == "mock"
    assert trace_data["latency_total_ms"] > 0
    assert "routing" in trace_data["latencies"]
    assert "llm" in trace_data["latencies"]
    assert trace_data["input_tokens"] is not None
    assert trace_data["output_tokens"] is not None
    assert trace_data["total_tokens"] is not None


def test_observability_records_trace_on_rag_chat(mock_settings: Settings) -> None:
    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-obs-rag",
            "message": "Para que serve a losartana?",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    trace_id = None
    for line in body.split("\n"):
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "trace_id" in data:
                trace_id = data["trace_id"]
                break

    assert trace_id is not None

    trace_response = client.get(f"/chat/traces/{trace_id}")
    assert trace_response.status_code == 200
    trace_data = trace_response.json()

    assert len(trace_data["documents_retrieved"]) > 0
    assert "retrieval" in trace_data["latencies"]
    assert trace_data["fallback"] is False  # Found documents
    # Should have identified the citations
    assert len(trace_data["sources_cited"]) > 0


def test_observability_records_trace_on_tool_chat(mock_settings: Settings) -> None:
    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        json={
            "conversation_id": "conv-obs-tool",
            "message": "Quais filiais em Curitiba?",
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    trace_id = None
    for line in body.split("\n"):
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "trace_id" in data:
                trace_id = data["trace_id"]
                break

    assert trace_id is not None

    trace_response = client.get(f"/chat/traces/{trace_id}")
    assert trace_response.status_code == 200
    trace_data = trace_response.json()

    assert len(trace_data["tool_calls"]) == 1
    assert trace_data["tool_calls"][0]["tool_name"] == "buscar_filiais"
    assert "tool_call" in trace_data["latencies"]


def test_observability_list_traces(mock_settings: Settings) -> None:
    client = TestClient(app)

    # Trigger two chats to have traces in the repository
    client.post("/chat/stream", json={"conversation_id": "conv1", "message": "Oi 1"})
    client.post("/chat/stream", json={"conversation_id": "conv2", "message": "Oi 2"})

    list_response = client.get("/chat/traces")
    assert list_response.status_code == 200
    traces = list_response.json()
    assert len(traces) == 2
    assert traces[0]["prompt"] == "Oi 1"
    assert traces[1]["prompt"] == "Oi 2"
