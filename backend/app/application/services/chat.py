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

# Observability Imports
from app.observability.traces import Trace, trace_repository

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


def _is_bula_meta_query(message: str) -> bool:
    msg = message.lower()
    meta_patterns = [
        r"quais\s+(são\s+as\s+)?bulas",
        r"quais\s+(são\s+os\s+)?medicamentos",
        r"quais\s+(são\s+os\s+)?remédios",
        r"quais\s+(são\s+os\s+)?remedios",
        r"quais\s+(medicamentos|remédios|remedios|bulas)\s+(você|vc)\s+(tem|conhece|possui|acesso)",
        r"lista\s+de\s+(bulas|medicamentos|remédios|remedios)",
        r"quantas\s+bulas",
        r"quantos\s+(medicamentos|remédios|remedios)",
        r"(só|so)\s+tem\s+(isso|essas|esses)\s+de\s+(bula|medicamento|remédio|remedio)",
        r"(só|so)\s+tem\s+essas\s+bulas",
        r"quais\s+(estão|estao)\s+disponíveis",
        r"quais\s+(estão|estao)\s+cadastrados",
        r"tem\s+(outro|outra|outros|outras)\s+(bula|medicamento|remédio|remedio)",
    ]
    return any(re.search(pat, msg) for pat in meta_patterns)



def stream_chat_events(payload: ChatRequest) -> Iterator[str]:
    trace_id = str(uuid4())
    settings = get_settings()
    provider = build_llm_provider(settings)
    system_prompt = load_prompt("system-assistant.md")

    # Fetch recent conversation history from trace repository
    recent_traces = trace_repository.get_conversation_history(payload.conversation_id, limit=3)
    history = []
    for t in recent_traces:
        history.append({"role": "user", "content": t.prompt})
        history.append({"role": "assistant", "content": t.answer})

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
    
    # Initialize observability trace object
    trace = Trace(
        trace_id=trace_id,
        conversation_id=payload.conversation_id,
        prompt=payload.message,
        provider=settings.llm_provider,
        model=settings.llm_model,
    )
    
    tokens_accumulated = []

    try:
        prompt_sent = system_prompt
        # 1. Routing
        routing_start = time.perf_counter()
        intent = _classify_intent(payload.message)
        trace.latencies["routing"] = round((time.perf_counter() - routing_start) * 1000, 2)
        
        yield _format_sse_event(ChatEvent(
            event=ChatEventType.TRACE,
            data={
                "trace_id": trace_id,
                "conversation_id": payload.conversation_id,
                "step": "routing",
                "message": f"Intencao detectada: {intent}",
            }
        ))

        # 2. Flow execution
        if intent == "rag":
            retrieval_start = time.perf_counter()
            retriever = get_retriever()
            
            if _is_bula_meta_query(payload.message):
                yield _format_sse_event(ChatEvent(
                    event=ChatEventType.TRACE,
                    data={
                        "trace_id": trace_id,
                        "conversation_id": payload.conversation_id,
                        "step": "retrieval",
                        "message": "Listando todos os medicamentos disponíveis no sistema...",
                    }
                ))
                all_bulas = retriever.list_files
                trace.latencies["retrieval"] = round((time.perf_counter() - retrieval_start) * 1000, 2)
                
                bula_list_str = "\n".join(f"- {b}" for b in all_bulas)
                context_text = f"O sistema possui as seguintes bulas de medicamentos cadastradas e indexadas disponíveis para consulta:\n{bula_list_str}"
            else:
                yield _format_sse_event(ChatEvent(
                    event=ChatEventType.TRACE,
                    data={
                        "trace_id": trace_id,
                        "conversation_id": payload.conversation_id,
                        "step": "retrieval",
                        "message": "Buscando informações nas bulas...",
                    }
                ))
                chunks = retriever.retrieve(payload.message, k=3)
                trace.latencies["retrieval"] = round((time.perf_counter() - retrieval_start) * 1000, 2)
                
                if not chunks:
                    trace.fallback = True
                
                # Emit source events and save metadata to trace
                for chunk in chunks:
                    doc_meta = {
                        "arquivo": chunk.arquivo,
                        "pagina": chunk.pagina,
                        "secao": chunk.secao,
                        "score": chunk.score,
                    }
                    trace.documents_retrieved.append(doc_meta)
                    
                    yield _format_sse_event(ChatEvent(
                        event=ChatEventType.SOURCE,
                        data={
                            "trace_id": trace_id,
                            "conversation_id": payload.conversation_id,
                            **doc_meta,
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
            
            llm_start = time.perf_counter()
            stream_generator = provider.stream(payload.message, full_system_prompt, history=history)
            prompt_sent = full_system_prompt

            
        elif intent == "detalhes_filial":
            tool_start = time.perf_counter()
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
            trace.latencies["tool_call"] = round((time.perf_counter() - tool_start) * 1000, 2)
            
            # Record tool call in trace
            trace.tool_calls.append({
                "tool_name": "detalhes_filial",
                "arguments": tool_input.model_dump(),
                "result": tool_result.model_dump(),
            })
            
            if tool_result.error or not tool_result.filial:
                trace.fallback = True
            
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
            
            llm_start = time.perf_counter()
            stream_generator = provider.stream(payload.message, full_system_prompt, history=history)
            prompt_sent = full_system_prompt
            
        elif intent == "buscar_filiais":
            tool_start = time.perf_counter()
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
            trace.latencies["tool_call"] = round((time.perf_counter() - tool_start) * 1000, 2)
            
            # Record tool call in trace
            trace.tool_calls.append({
                "tool_name": "buscar_filiais",
                "arguments": tool_input.model_dump(),
                "result": tool_result.model_dump(),
            })
            
            if tool_result.error or not tool_result.filiais:
                trace.fallback = True
            
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
            
            llm_start = time.perf_counter()
            stream_generator = provider.stream(payload.message, full_system_prompt, history=history)
            prompt_sent = full_system_prompt
            
        else:
            llm_start = time.perf_counter()
            stream_generator = provider.stream(payload.message, system_prompt, history=history)
            prompt_sent = system_prompt
            
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        
        # Save LLM usage info (will finalize outputs after streaming)
        trace.model = settings.llm_model
        prompt_words = len(prompt_sent.split()) + len(payload.message.split())
        trace.input_tokens = int(prompt_words * 1.3)
        trace.output_tokens = 0
        trace.total_tokens = trace.input_tokens
        
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception("Orchestration pipeline failed", exc_info=exc)
        
        # Save error and latency inside trace
        trace.errors.append(f"{exc.__class__.__name__}: {str(exc)}")
        trace.latency_total_ms = latency_ms
        trace_repository.save(trace)
        
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

    # Yield tokens and accumulate them for the trace response
    # We measure true LLM latency (Time to First Token) on the first token received
    try:
        for token in stream_generator:
            if not tokens_accumulated:
                trace.latencies["llm"] = round((time.perf_counter() - llm_start) * 1000, 2)
            tokens_accumulated.append(token)
            token_event = ChatEvent(
                event=ChatEventType.TOKEN,
                data={
                    "trace_id": trace_id,
                    "conversation_id": payload.conversation_id,
                    "token": token,
                },
            )
            yield _format_sse_event(token_event)
    except Exception as exc:
        logger.exception("Error during LLM streaming", exc_info=exc)
        trace.errors.append(f"StreamingError: {str(exc)}")
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

    # Reconstruct answer and search for sources cited
    answer_text = "".join(tokens_accumulated)
    trace.answer = answer_text
    
    for doc in trace.documents_retrieved:
        filename = doc["arquivo"]
        name_no_ext = filename.split(".")[0]
        if filename.lower() in answer_text.lower() or name_no_ext.lower() in answer_text.lower():
            if filename not in trace.sources_cited:
                trace.sources_cited.append(filename)

    trace.output_tokens = len(tokens_accumulated)
    trace.total_tokens = trace.input_tokens + trace.output_tokens
    
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    trace.latency_total_ms = latency_ms
    trace_repository.save(trace)

    done_event = ChatEvent(
        event=ChatEventType.DONE,
        data={
            "trace_id": trace_id,
            "conversation_id": payload.conversation_id,
            "provider": settings.llm_provider,
            "model": trace.model,
            "latency_ms": f"{latency_ms}",
            "input_tokens": _stringify_optional_int(trace.input_tokens),
            "output_tokens": _stringify_optional_int(trace.output_tokens),
            "total_tokens": _stringify_optional_int(trace.total_tokens),
        },
    )
    yield _format_sse_event(done_event)


def _format_sse_event(event: ChatEvent) -> str:
    return f"event: {event.event.value}\ndata: {json.dumps(event.data)}\n\n"


def _stringify_optional_int(value: int | None) -> str:
    return "" if value is None else str(value)


def _build_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if "insufficient_quota" in message.lower() or "quota" in message.lower() or "limit" in message.lower():
        return f"Limite de quota excedido no provedor LLM. Verifique o faturamento (billing) e limites da sua chave de API. Detalhes: {message}"
    return message or "Falha ao chamar o provider LLM."
