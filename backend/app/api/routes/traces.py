from fastapi import APIRouter, HTTPException
from app.observability.traces import Trace, trace_repository

router = APIRouter()


@router.get("/chat/traces/{trace_id}", response_model=Trace, summary="Recupera trace estruturado de um turno do chat")
def get_trace(trace_id: str) -> Trace:
    trace = trace_repository.get(trace_id)
    if not trace:
        raise HTTPException(
            status_code=404,
            detail=f"Trace '{trace_id}' não encontrado no repositório local."
        )
    return trace


@router.get("/chat/traces", response_model=list[Trace], summary="Lista os traces mais recentes do assistente")
def list_traces(limit: int = 100) -> list[Trace]:
    return trace_repository.list_all(limit=limit)
