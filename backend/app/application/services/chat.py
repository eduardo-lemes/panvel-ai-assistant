import json
import logging
import time
from collections.abc import Iterator
from uuid import uuid4

from app.domain.models.chat import ChatEvent, ChatEventType, ChatRequest
from app.infrastructure.config.settings import get_settings
from app.infrastructure.llm.factory import build_llm_provider
from app.infrastructure.prompts.loader import load_prompt


logger = logging.getLogger(__name__)


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
    try:
        completion = provider.complete(payload.message, system_prompt)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception("LLM provider request failed", exc_info=exc)
        error_event = ChatEvent(
            event=ChatEventType.ERROR,
            data={
                "trace_id": trace_id,
                "conversation_id": payload.conversation_id,
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "error_code": exc.__class__.__name__,
                "message": _build_error_message(exc),
            },
        )
        yield _format_sse_event(error_event)

        done_event = ChatEvent(
            event=ChatEventType.DONE,
            data={
                "trace_id": trace_id,
                "conversation_id": payload.conversation_id,
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "latency_ms": f"{latency_ms}",
                "input_tokens": "",
                "output_tokens": "",
                "total_tokens": "",
            },
        )
        yield _format_sse_event(done_event)
        return

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


def _build_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if "insufficient_quota" in message.lower():
        return "O provider LLM retornou falta de quota. Verifique billing, limites ou troque para LLM_PROVIDER=mock."
    return message or "Falha ao chamar o provider LLM."
