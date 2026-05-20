"""
Testes do retriever de bulas.

Usa MockEmbedder (TF-IDF) para rodar sem chave de API.
Cria um ChromaDB temporário em memória/tmp para isolamento.
"""

import tempfile
from pathlib import Path

import pytest

from app.domain.models.rag import BulaChunk, RetrievedChunk
from app.infrastructure.rag.embedder import MockEmbedder
from app.infrastructure.rag.retriever import BulaRetriever
from app.infrastructure.rag.vector_store import BulaVectorStore

CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "corpus_bulas"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_chunks() -> list[BulaChunk]:
    """Cria chunks sintéticos para testes de retriever sem depender dos PDFs."""
    return [
        BulaChunk(
            texto="A losartana é indicada para tratamento de hipertensão arterial e insuficiência cardíaca.",
            codigo_item="950220",
            arquivo="950220_zart_losartana.pdf",
            pagina=1,
            secao="INDICAÇÕES",
            chunk_index=0,
        ),
        BulaChunk(
            texto="Rocefin ceftriaxona é contraindicado em pacientes com hipersensibilidade a cefalosporinas.",
            codigo_item="27049",
            arquivo="27049_rocefin_ceftriaxona.pdf",
            pagina=2,
            secao="CONTRAINDICAÇÕES",
            chunk_index=0,
        ),
        BulaChunk(
            texto="Ritalina metilfenidato pode causar insônia, perda de apetite e nervosismo.",
            codigo_item="927100",
            arquivo="927100_ritalina_metilfenidato.pdf",
            pagina=3,
            secao="REAÇÕES ADVERSAS",
            chunk_index=0,
        ),
        BulaChunk(
            texto="Pregabalina é utilizada no tratamento de dor neuropática e epilepsia.",
            codigo_item="114471",
            arquivo="114471_pregabalina.pdf",
            pagina=1,
            secao="INDICAÇÕES",
            chunk_index=0,
        ),
    ]


@pytest.fixture()
def retriever_com_chunks() -> BulaRetriever:
    """Retorna um BulaRetriever com chunks sintéticos e ChromaDB temporário."""
    chunks = _make_chunks()
    embedder = MockEmbedder()
    embedder.fit([c.texto for c in chunks])

    with tempfile.TemporaryDirectory() as tmp_dir:
        store = BulaVectorStore(store_path=Path(tmp_dir), embedder=embedder)
        store.add_chunks(chunks)
        yield BulaRetriever(vector_store=store)


@pytest.fixture()
def retriever_vazio() -> BulaRetriever:
    """Retorna um BulaRetriever com índice vazio."""
    embedder = MockEmbedder()
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = BulaVectorStore(store_path=Path(tmp_dir), embedder=embedder)
        yield BulaRetriever(vector_store=store)


# ---------------------------------------------------------------------------
# Testes de is_ready
# ---------------------------------------------------------------------------

def test_retriever_vazio_nao_esta_pronto(retriever_vazio: BulaRetriever):
    assert retriever_vazio.is_ready is False


def test_retriever_com_chunks_esta_pronto(retriever_com_chunks: BulaRetriever):
    assert retriever_com_chunks.is_ready is True


# ---------------------------------------------------------------------------
# Testes de retrieve
# ---------------------------------------------------------------------------

def test_retrieve_retorna_lista_nao_vazia(retriever_com_chunks: BulaRetriever):
    results = retriever_com_chunks.retrieve("para que serve a losartana")
    assert isinstance(results, list)
    assert len(results) > 0


def test_retrieve_retorna_retrieved_chunks(retriever_com_chunks: BulaRetriever):
    results = retriever_com_chunks.retrieve("losartana hipertensão")
    for item in results:
        assert isinstance(item, RetrievedChunk)


def test_retrieve_chunks_tem_metadados(retriever_com_chunks: BulaRetriever):
    results = retriever_com_chunks.retrieve("losartana")
    for item in results:
        assert item.arquivo
        assert item.codigo_item
        assert item.pagina >= 1
        assert item.secao
        assert item.texto


def test_retrieve_com_query_vazia_retorna_vazia(retriever_com_chunks: BulaRetriever):
    assert retriever_com_chunks.retrieve("") == []


def test_retrieve_com_query_whitespace_retorna_vazia(retriever_com_chunks: BulaRetriever):
    assert retriever_com_chunks.retrieve("   ") == []


def test_retrieve_vazio_retorna_lista_vazia(retriever_vazio: BulaRetriever):
    results = retriever_vazio.retrieve("losartana")
    assert results == []


def test_retrieve_score_entre_zero_e_um(retriever_com_chunks: BulaRetriever):
    results = retriever_com_chunks.retrieve("contraindicações rocefin")
    for item in results:
        assert 0.0 <= item.score <= 1.0, f"Score fora do intervalo: {item.score}"


def test_retrieve_respeita_limite_k(retriever_com_chunks: BulaRetriever):
    results = retriever_com_chunks.retrieve("medicamento", k=2)
    assert len(results) <= 2


# ---------------------------------------------------------------------------
# Teste de integração com PDFs reais (skip se corpus ausente)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not CORPUS_PATH.exists(), reason="Corpus não encontrado")
def test_retrieve_real_losartana():
    """Smoke test com PDFs reais: losartana deve aparecer no top-5."""
    from app.infrastructure.rag.chunker import extract_chunks_from_directory

    chunks = extract_chunks_from_directory(CORPUS_PATH)
    embedder = MockEmbedder()
    embedder.fit([c.texto for c in chunks])

    with tempfile.TemporaryDirectory() as tmp_dir:
        store = BulaVectorStore(store_path=Path(tmp_dir), embedder=embedder)
        store.add_chunks(chunks)
        retriever = BulaRetriever(vector_store=store)

        results = retriever.retrieve("para que serve a losartana", k=5)
        assert len(results) > 0
        arquivos = [r.arquivo for r in results]
        assert any("losartana" in a for a in arquivos), (
            f"losartana não apareceu no top-5: {arquivos}"
        )
