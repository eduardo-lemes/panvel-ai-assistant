#!/usr/bin/env python
"""
Script de ingestão das bulas da Anvisa.

Uso:
    cd backend
    python scripts/ingest_bulas.py

O script:
  1. Lê todos os PDFs em data/corpus_bulas/
  2. Extrai e divide em chunks com metadados (pagina, secao, codigo_item)
  3. Gera embeddings (OpenAI ou mock TF-IDF conforme EMBEDDING_PROVIDER)
  4. Indexa no ChromaDB local (backend/.chroma/)

Idempotente: limpa a coleção antes de reinserir.
"""

import sys
import time
import logging
from pathlib import Path

# Adiciona backend/ ao path para importar `app`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.config.settings import get_settings
from app.infrastructure.rag.chunker import extract_chunks_from_directory
from app.infrastructure.rag.embedder import MockEmbedder, build_embedder
from app.infrastructure.rag.vector_store import BulaVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest_bulas")


def main() -> None:
    settings = get_settings()
    root = Path(__file__).resolve().parents[2]
    corpus_path = root / "data" / "corpus_bulas"

    if not corpus_path.exists():
        logger.error("Diretório não encontrado: %s", corpus_path)
        sys.exit(1)

    pdf_files = sorted(corpus_path.glob("*.pdf"))
    if not pdf_files:
        logger.error("Nenhum PDF encontrado em: %s", corpus_path)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Iniciando ingestão das bulas")
    logger.info("Corpus: %s", corpus_path)
    logger.info("PDFs encontrados: %d", len(pdf_files))
    logger.info("Embedding provider: %s", settings.embedding_provider)
    logger.info("Vector store path: %s", settings.vector_store_path)
    logger.info("=" * 60)

    # 1. Extração e chunking
    t0 = time.perf_counter()
    logger.info("Extraindo chunks dos PDFs...")
    chunks = extract_chunks_from_directory(corpus_path)
    extraction_time = round(time.perf_counter() - t0, 2)

    logger.info("Chunks extraídos: %d (em %.2fs)", len(chunks), extraction_time)
    if not chunks:
        logger.error("Nenhum chunk extraído. Verifique os PDFs.")
        sys.exit(1)

    # Estatísticas de chunking
    chunk_sizes = [len(c.texto.split()) for c in chunks]
    logger.info(
        "Tamanho médio dos chunks: %.0f tokens | min: %d | max: %d",
        sum(chunk_sizes) / len(chunk_sizes),
        min(chunk_sizes),
        max(chunk_sizes),
    )
    by_file: dict[str, int] = {}
    for c in chunks:
        by_file[c.arquivo] = by_file.get(c.arquivo, 0) + 1
    logger.info("Chunks por arquivo:")
    for fname, count in sorted(by_file.items()):
        logger.info("  %-60s %d chunks", fname, count)

    # 2. Embedder
    embedder = build_embedder(settings.embedding_provider, settings.openai_api_key)

    # Para MockEmbedder, pre-treina o vocabulário com todos os textos
    if isinstance(embedder, MockEmbedder):
        logger.info("Treinando vocabulário TF-IDF com todos os chunks...")
        embedder.fit([c.texto for c in chunks])

    # 3. Vector store — limpa antes de reinserir (idempotente)
    store = BulaVectorStore(store_path=settings.vector_store_path, embedder=embedder)
    logger.info("Limpando coleção existente para reingestão limpa...")
    store.clear()

    # 4. Indexação
    t1 = time.perf_counter()
    logger.info("Indexando no ChromaDB...")
    store.add_chunks(chunks)
    indexing_time = round(time.perf_counter() - t1, 2)

    logger.info("=" * 60)
    logger.info("✓ Ingestão concluída em %.2fs", indexing_time)
    logger.info("✓ Total de chunks indexados: %d", store.count)
    logger.info("✓ Índice salvo em: %s", settings.vector_store_path)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
