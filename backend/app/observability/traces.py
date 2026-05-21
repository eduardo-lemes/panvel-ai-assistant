import logging
import threading
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Trace(BaseModel):
    """
    Modelo de dados para auditoria de cada turno de atendimento.
    Armazena latências, tokens consumidos, chamadas de tools e fontes do RAG.
    """
    trace_id: str
    conversation_id: str
    prompt: str
    answer: str = ""
    model: str = ""
    provider: str = ""
    latency_total_ms: float = 0.0
    latencies: dict[str, float] = Field(default_factory=dict)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    documents_retrieved: list[dict[str, Any]] = Field(default_factory=list)
    sources_cited: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    fallback: bool = False


class TraceRepository:
    """
    Repositório thread-safe em memória para armazenar os traces das interações.
    Em produção, deve persistir no banco de dados ou serviço de APM.
    """
    def __init__(self) -> None:
        self._traces: dict[str, Trace] = {}
        self._lock = threading.Lock()

    def save(self, trace: Trace) -> None:
        with self._lock:
            self._traces[trace.trace_id] = trace
            logger.info("Trace %s salvo com sucesso no repositório.", trace.trace_id)

    def get(self, trace_id: str) -> Optional[Trace]:
        with self._lock:
            return self._traces.get(trace_id)

    def list_all(self, limit: int = 100) -> list[Trace]:
        with self._lock:
            # Retorna os traces mais recentes em ordem de inserção
            return list(self._traces.values())[-limit:]

    def get_conversation_history(self, conversation_id: str, limit: int = 5) -> list[Trace]:
        with self._lock:
            # Filter completed traces for a conversation
            completed_traces = [
                t for t in self._traces.values()
                if t.conversation_id == conversation_id and t.answer
            ]
            return completed_traces[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._traces.clear()


# Instância global do repositório
trace_repository = TraceRepository()
