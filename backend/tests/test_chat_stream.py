from fastapi.testclient import TestClient

from app.main import app


def test_chat_stream_emits_trace_token_and_done_events() -> None:
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
