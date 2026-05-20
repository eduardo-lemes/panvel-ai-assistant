import json
import time
from collections.abc import Iterator
from uuid import uuid4

from app.domain.models.chat import ChatEvent, ChatEventType, ChatRequest
from app.infrastructure.config.settings import get_settings
from app.infrastructure.llm.factory import build_llm_provider
from app.infrastructure.prompts.loader import load_prompt


def stream_chat_events(payload: ChatRequest) -> Iterator[str]:
    trace_id = str(uuid4())
    settings = get_settings()
    provider = build_llm_provider(settings)
    system_prompt = load_prompt("system-assistant.md")

    trace_event = ChatEvent(
        event=ChatEventType.TRACE,
        data={
            "trace_id": trace_id,
            "conversation_id": payload.conversation_id,
            "provider": settings.llm_provider,
            "model": settings.llm_model,
        },
    )
    yield _format_sse_event(trace_event)

    started_at = time.perf_counter()
    completion = provider.complete(payload.message, system_prompt)
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

    for token in completion.text.split():
        token_event = ChatEvent(
            event=ChatEventType.TOKEN,
            data={
                "trace_id": trace_id,
                "conversation_id": payload.conversation_id,
                "token": token,
            },
        )
        yield _format_sse_event(token_event)

    done_event = ChatEvent(
        event=ChatEventType.DONE,
        data={
            "trace_id": trace_id,
            "conversation_id": payload.conversation_id,
            "provider": settings.llm_provider,
            "model": completion.model,
            "latency_ms": f"{latency_ms}",
            "input_tokens": _stringify_optional_int(completion.usage.input_tokens),
            "output_tokens": _stringify_optional_int(completion.usage.output_tokens),
            "total_tokens": _stringify_optional_int(completion.usage.total_tokens),
        },
    )
    yield _format_sse_event(done_event)


def _format_sse_event(event: ChatEvent) -> str:
    return f"event: {event.event.value}\ndata: {json.dumps(event.data)}\n\n"


def _stringify_optional_int(value: int | None) -> str:
    return "" if value is None else str(value)
