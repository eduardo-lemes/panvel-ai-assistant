import json
import logging
import time
import re
from collections.abc import Iterator
from uuid import uuid4

from app.domain.models.chat import ChatEvent, ChatEventType, ChatRequest
from app.infrastructure.config.settings import get_settings
from app.infrastructure.llm.factory import build_llm_provider
from app.infrastructure.prompts.loader import load_prompt

# RAG & Tools Imports
from app.infrastructure.rag.retriever import get_retriever
from app.infrastructure.repositories.filiais import build_default_filial_repository
from app.application.services.filial_tools import buscar_filiais, detalhes_filial
from app.domain.models.tools import BuscarFiliaisInput, DetalhesFilialInput

logger = logging.getLogger(__name__)


def _classify_intent(message: str) -> str:
    msg = message.lower()
    
    # 1. Check for details of a branch (detalhes_filial)
    if any(k in msg for k in ["detalhes", "informações", "cadastro", "filial de", "codigo", "código"]) and re.search(r"\b\d+\b", msg):
        return "detalhes_filial"
    if re.search(r"\bfilial\s+\d+\b", msg) or re.search(r"\bcodigo\s+\d+\b", msg) or re.search(r"\bcódigo\s+\d+\b", msg):
        return "detalhes_filial"
        
    # 2. Check for searching branches (buscar_filiais)
    filial_keywords = ["filial", "filiais", "loja", "lojas", "clinic", "24 horas", "24h", "estacionamento", "delivery", "entrega", "tele"]
    cities = ["curitiba", "londrina", "maringa", "maringá", "porto alegre", "cascavel", "foz do iguacu", "foz do iguaçu", "ponta grossa"]
    if any(k in msg for k in filial_keywords) or any(c in msg for c in cities):
        return "buscar_filiais"
        
    # 3. Check for RAG (meds/bulas)
    rag_keywords = [
        "bula", "medicamento", "remedio", "remédio", "contraindicacao", "contraindicação", 
        "indicado", "indicacao", "indicação", "insonia", "insônia", "efeito", "efeitos colaterais", 
        "serve", "reacao", "reação", "dosagem", "dose", "gravida", "grávida", "gestante",
        "losartana", "rocefin", "ritalina", "pregabalina", "norfloxacino", "ondansetrona", 
        "memantina", "levocetirizina", "ceftriaxona", "hidroxicloroquina", "paroxetina", 
        "celecoxibe", "propafenona", "contraceptivo", "venlafaxina", "metoprolol", 
        "pantoprazol", "bromazepam", "tramadol", "ibuprofeno", "spidufen", "flunitrazepam"
    ]
    if any(k in msg for k in rag_keywords):
        return "rag"
        
    return "direct"


def stream_chat_events(payload: ChatRequest) -> Iterator[str]:
    trace_id = str(uuid4())
    settings = get_settings()
    provider = build_llm_provider(settings)
    system_prompt = load_prompt("system-assistant.md")

    # Trace: starting orchestration
    trace_event = ChatEvent(
        event=ChatEventType.TRACE,
        data={
            "trace_id": trace_id,
            "conversation_id": payload.conversation_id,
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "step": "started",
            "message": "Iniciando atendimento do assistente...",
        },
    )
    yield _format_sse_event(trace_event)

    started_at = time.perf_counter()
    try:
        # 1. Routing
        intent = _classify_intent(payload.message)
        yield _format_sse_event(ChatEvent(
            event=ChatEventType.TRACE,
            data={
                "trace_id": trace_id,
                "conversation_id": payload.conversation_id,
                "step": "routing",
                "message": f"Intenção detectada: {intent}",
            }
        ))

        # 2. Flow execution
        if intent == "rag":
            yield _format_sse_event(ChatEvent(
                event=ChatEventType.TRACE,
                data={
                    "trace_id": trace_id,
                    "conversation_id": payload.conversation_id,
                    "step": "retrieval",
                    "message": "Buscando informações nas bulas...",
                }
            ))
            
            retriever = get_retriever()
            chunks = retriever.retrieve(payload.message, k=3)
            
            # Emit source events
            for chunk in chunks:
                yield _format_sse_event(ChatEvent(
                    event=ChatEventType.SOURCE,
                    data={
                        "trace_id": trace_id,
                        "conversation_id": payload.conversation_id,
                        "arquivo": chunk.arquivo,
                        "pagina": chunk.pagina,
                        "secao": chunk.secao,
                        "score": chunk.score,
                        "texto": chunk.texto,
                    }
                ))
            
            context_parts = []
            for i, chunk in enumerate(chunks):
                context_parts.append(
                    f"Trecho {i+1} (Arquivo: {chunk.arquivo}, Página: {chunk.pagina}, Seção: {chunk.secao}):\n{chunk.texto}"
                )
            context_text = "\n\n".join(context_parts)
            
            rag_rules = load_prompt("rag-answering.md")
            full_system_prompt = f"{system_prompt}\n\n{rag_rules}\n\n=== CONTEXTO DAS BULAS ===\n{context_text}"
            completion = provider.complete(payload.message, full_system_prompt)
            
        elif intent == "detalhes_filial":
            match = re.search(r"\b\d+\b", payload.message)
            codigo_filial = match.group(0) if match else ""
            
            yield _format_sse_event(ChatEvent(
                event=ChatEventType.TRACE,
                data={
                    "trace_id": trace_id,
                    "conversation_id": payload.conversation_id,
                    "step": "tool_call",
                    "message": f"Buscando detalhes da filial {codigo_filial}...",
                }
            ))
            
            repo = build_default_filial_repository()
            tool_input = DetalhesFilialInput(codigo_filial=codigo_filial)
            tool_result = detalhes_filial(tool_input, repo)
            
            yield _format_sse_event(ChatEvent(
                event=ChatEventType.TOOL_CALL,
                data={
                    "trace_id": trace_id,
                    "conversation_id": payload.conversation_id,
                    "tool_name": "detalhes_filial",
                    "arguments": tool_input.model_dump(),
                    "result": tool_result.model_dump(),
                }
            ))
            
            tool_rules = load_prompt("tool-calling.md")
            full_system_prompt = f"{system_prompt}\n\n{tool_rules}\n\n=== RETORNO DA TOOL detalhes_filial ===\n{tool_result.model_dump_json(indent=2)}"
            completion = provider.complete(payload.message, full_system_prompt)
            
        elif intent == "buscar_filiais":
            cidade = None
            for city in ["Curitiba", "Londrina", "Maringa", "Maringá", "Porto Alegre", "Cascavel", "Ponta Grossa", "Foz do Iguaçu", "Foz do Iguacu"]:
                if city.lower() in payload.message.lower():
                    cidade = city
                    break
                    
            panvel_clinic = True if any(k in payload.message.lower() for k in ["clinic", "consultório", "vacina", "atendimento médico"]) else None
            atendimento_24_horas = True if any(k in payload.message.lower() for k in ["24 horas", "24h", "dia e noite", "24 hs"]) else None
            delivery = True if any(k in payload.message.lower() for k in ["delivery", "entrega", "tele"]) else None
            estacionamento = True if any(k in payload.message.lower() for k in ["estacionamento", "vaga", "carro"]) else None
            
            tool_input = BuscarFiliaisInput(
                cidade=cidade,
                panvel_clinic=panvel_clinic,
                atendimento_24_horas=atendimento_24_horas,
                delivery=delivery,
                estacionamento=estacionamento,
            )
            
            yield _format_sse_event(ChatEvent(
                event=ChatEventType.TRACE,
                data={
                    "trace_id": trace_id,
                    "conversation_id": payload.conversation_id,
                    "step": "tool_call",
                    "message": f"Buscando filiais com filtros...",
                }
            ))
            
            repo = build_default_filial_repository()
            tool_result = buscar_filiais(tool_input, repo)
            
            yield _format_sse_event(ChatEvent(
                event=ChatEventType.TOOL_CALL,
                data={
                    "trace_id": trace_id,
                    "conversation_id": payload.conversation_id,
                    "tool_name": "buscar_filiais",
                    "arguments": tool_input.model_dump(),
                    "result": tool_result.model_dump(),
                }
            ))
            
            tool_rules = load_prompt("tool-calling.md")
            full_system_prompt = f"{system_prompt}\n\n{tool_rules}\n\n=== RETORNO DA TOOL buscar_filiais ===\n{tool_result.model_dump_json(indent=2)}"
            completion = provider.complete(payload.message, full_system_prompt)
            
        else:
            completion = provider.complete(payload.message, system_prompt)
            
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception("Orchestration pipeline failed", exc_info=exc)
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
