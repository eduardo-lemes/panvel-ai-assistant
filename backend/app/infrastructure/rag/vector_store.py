"""
Vector store local baseado em numpy + JSON.

Implementação sem dependências de compilação nativa.
Persiste em disco:
  - embeddings.npy   → matriz de embeddings (float32)
  - metadata.json    → lista de dicts com texto e metadados por chunk

Busca por similaridade coseno em numpy puro (O(n) — adequado para ~5000 chunks de bulas).

Em produção: substituir por Qdrant, pgvector ou outro serviço gerenciado.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from app.domain.models.rag import BulaChunk, RetrievedChunk
from app.infrastructure.rag.embedder import Embedder

logger = logging.getLogger(__name__)

_EMBEDDINGS_FILE = "embeddings.npy"
_METADATA_FILE = "metadata.json"


class BulaVectorStore:
    def __init__(self, store_path: Path, embedder: Embedder) -> None:
        self._path = store_path
        self._path.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder
        self._embeddings: np.ndarray | None = None   # shape (N, D)
        self._metadata: list[dict] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _load(self) -> None:
        emb_file = self._path / _EMBEDDINGS_FILE
        meta_file = self._path / _METADATA_FILE
        if emb_file.exists() and meta_file.exists():
            self._embeddings = np.load(str(emb_file))
            with open(meta_file, encoding="utf-8") as f:
                self._metadata = json.load(f)
            # Auto-fit MockEmbedder if present using the loaded metadata texts
            if hasattr(self._embedder, "fit") and self._metadata:
                texts = [meta["texto"] for meta in self._metadata]
                self._embedder.fit(texts)
            logger.info(
                "Vector store carregado: %d chunks de %s",
                len(self._metadata),
                self._path,
            )

    def _save(self) -> None:
        if self._embeddings is None:
            return
        np.save(str(self._path / _EMBEDDINGS_FILE), self._embeddings)
        with open(self._path / _METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def add_chunks(self, chunks: list[BulaChunk], batch_size: int = 100) -> None:
        """Indexa chunks gerando embeddings em lotes e persiste em disco."""
        if not chunks:
            logger.warning("add_chunks chamado com lista vazia.")
            return

        logger.info("Indexando %d chunks em lotes de %d...", len(chunks), batch_size)
        all_embeddings: list[list[float]] = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.texto for c in batch]
            vecs = self._embedder.embed(texts)
            all_embeddings.extend(vecs)
            logger.info(
                "  Lote %d/%d gerado.",
                i // batch_size + 1,
                -(-len(chunks) // batch_size),
            )

        matrix = np.array(all_embeddings, dtype=np.float32)

        # Normaliza para coseno (||v|| = 1 → produto interno = coseno)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        matrix = matrix / norms

        self._embeddings = matrix
        self._metadata = [
            {
                "texto": c.texto,
                "codigo_item": c.codigo_item,
                "arquivo": c.arquivo,
                "pagina": c.pagina,
                "secao": c.secao,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]
        self._save()
        logger.info("Indexação concluída. Total: %d chunks.", len(self._metadata))

    def clear(self) -> None:
        """Remove o índice em disco e na memória."""
        (self._path / _EMBEDDINGS_FILE).unlink(missing_ok=True)
        (self._path / _METADATA_FILE).unlink(missing_ok=True)
        self._embeddings = None
        self._metadata = []
        logger.info("Vector store limpo em: %s", self._path)

    # ------------------------------------------------------------------
    # Busca
    # ------------------------------------------------------------------

    def search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        """
        Retorna os k chunks mais próximos por similaridade coseno.

        Retorna lista vazia se o índice estiver vazio.
        """
        if self._embeddings is None or len(self._metadata) == 0:
            logger.warning("Vector store vazio. Execute o script de ingestão primeiro.")
            return []

        query_vec = np.array(self._embedder.embed_one(query), dtype=np.float32)
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        # Produto interno = similaridade coseno (embeddings já normalizados)
        scores = self._embeddings @ query_vec
        top_k = min(k, len(self._metadata))
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        results: list[RetrievedChunk] = []
        for idx in top_indices:
            meta = self._metadata[idx]
            chunk = BulaChunk(
                texto=meta["texto"],
                codigo_item=str(meta["codigo_item"]),
                arquivo=str(meta["arquivo"]),
                pagina=int(meta["pagina"]),
                secao=str(meta["secao"]),
                chunk_index=int(meta["chunk_index"]),
            )
            results.append(RetrievedChunk(chunk=chunk, score=round(float(scores[idx]), 4)))

        return results

    @property
    def count(self) -> int:
        return len(self._metadata)

    @property
    def list_files(self) -> list[str]:
        """Retorna os nomes únicos dos arquivos de bula indexados."""
        return sorted(list(set(meta["arquivo"] for meta in self._metadata)))

