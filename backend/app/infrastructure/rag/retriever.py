"""
Retriever: ponto de entrada para busca semântica nas bulas.

Orquestra embedder → vector store → RetrievedChunk com metadados.
Também expõe uma factory que lê as Settings para montar o retriever correto.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from app.domain.models.rag import RetrievedChunk
from app.infrastructure.rag.embedder import Embedder, build_embedder
from app.infrastructure.rag.vector_store import BulaVectorStore

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5


class BulaRetriever:
    def __init__(self, vector_store: BulaVectorStore) -> None:
        self._store = vector_store

    def retrieve(self, query: str, k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
        """
        Recupera os k trechos mais relevantes para a query.

        Retorna lista vazia e loga aviso quando o índice está vazio.
        Nunca lança exceção — o chamador trata ausência de resultados.
        """
        if not query or not query.strip():
            return []
        try:
            return self._store.search(query.strip(), k=k)
        except Exception:
            logger.exception("Falha no retrieval da query: %r", query)
            return []

    @property
    def is_ready(self) -> bool:
        """True se o índice tem ao menos um chunk indexado."""
        return self._store.count > 0


# ---------------------------------------------------------------------------
# Factory singleton — carregado uma vez por processo
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def build_retriever(
    embedding_provider: str,
    openai_api_key: str | None,
    vector_store_path: str,
    gemini_api_key: str | None = None,
) -> BulaRetriever:
    """
    Constrói e cacheia o BulaRetriever para o processo atual.

    Parâmetros primitivos para compatibilidade com lru_cache.
    """
    embedder: Embedder = build_embedder(
        embedding_provider,
        openai_api_key,
        gemini_api_key,
    )
    store = BulaVectorStore(
        store_path=Path(vector_store_path),
        embedder=embedder,
    )
    retriever = BulaRetriever(vector_store=store)
    if not retriever.is_ready:
        logger.warning(
            "BulaRetriever inicializado mas o índice está vazio. "
            "Execute: python scripts/ingest_bulas.py"
        )
    else:
        logger.info("BulaRetriever pronto. Chunks indexados: %d", store.count)
    return retriever


def get_retriever() -> BulaRetriever:
    """Retorna o retriever configurado pelas Settings da aplicação."""
    from app.infrastructure.config.settings import get_settings
    s = get_settings()
    return build_retriever(
        embedding_provider=s.embedding_provider,
        openai_api_key=s.openai_api_key,
        vector_store_path=str(s.vector_store_path),
        gemini_api_key=s.gemini_api_key,
    )
