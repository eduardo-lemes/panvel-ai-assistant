"""
Testes do chunker de bulas.

Usa PDFs reais de data/corpus_bulas/ — não cria mocks de PDF.
Valida metadados, tamanho de chunks e extração de codigo_item.
"""

from pathlib import Path

import pytest

from app.infrastructure.rag.chunker import (
    CHUNK_SIZE,
    _extract_codigo_item,
    extract_chunks_from_directory,
    extract_chunks_from_pdf,
)

CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "corpus_bulas"
LOSARTANA_PDF = CORPUS_PATH / "950220_zart_losartana.pdf"
RITALINA_PDF = CORPUS_PATH / "927100_ritalina_metilfenidato.pdf"


# ---------------------------------------------------------------------------
# Testes de _extract_codigo_item
# ---------------------------------------------------------------------------

def test_extract_codigo_item_normal():
    assert _extract_codigo_item("950220_zart_losartana.pdf") == "950220"


def test_extract_codigo_item_sem_underscore():
    assert _extract_codigo_item("ritalina.pdf") == "ritalina"


# ---------------------------------------------------------------------------
# Testes de extract_chunks_from_pdf
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not LOSARTANA_PDF.exists(), reason="PDF da losartana não encontrado")
def test_losartana_gera_chunks():
    chunks = extract_chunks_from_pdf(LOSARTANA_PDF)
    assert len(chunks) > 0, "Deve gerar ao menos um chunk"


@pytest.mark.skipif(not LOSARTANA_PDF.exists(), reason="PDF da losartana não encontrado")
def test_losartana_metadados_presentes():
    chunks = extract_chunks_from_pdf(LOSARTANA_PDF)
    for chunk in chunks:
        assert chunk.codigo_item == "950220"
        assert chunk.arquivo == "950220_zart_losartana.pdf"
        assert chunk.pagina >= 1
        assert isinstance(chunk.secao, str) and chunk.secao
        assert chunk.chunk_index >= 0


@pytest.mark.skipif(not LOSARTANA_PDF.exists(), reason="PDF da losartana não encontrado")
def test_chunks_nao_sao_muito_curtos():
    chunks = extract_chunks_from_pdf(LOSARTANA_PDF)
    for chunk in chunks:
        tokens = chunk.texto.split()
        assert len(tokens) >= 20, f"Chunk muito curto: {len(tokens)} tokens"


@pytest.mark.skipif(not LOSARTANA_PDF.exists(), reason="PDF da losartana não encontrado")
def test_chunks_nao_excedem_tamanho_maximo():
    chunks = extract_chunks_from_pdf(LOSARTANA_PDF)
    # Permite margem mínima: último chunk pode ser menor que CHUNK_SIZE
    for chunk in chunks:
        tokens = chunk.texto.split()
        assert len(tokens) <= CHUNK_SIZE, f"Chunk excede tamanho máximo: {len(tokens)} tokens"


@pytest.mark.skipif(not LOSARTANA_PDF.exists(), reason="PDF da losartana não encontrado")
def test_chunk_index_sequencial():
    chunks = extract_chunks_from_pdf(LOSARTANA_PDF)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks))), "chunk_index deve ser sequencial"


# ---------------------------------------------------------------------------
# Testes de extract_chunks_from_directory
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not CORPUS_PATH.exists(), reason="Corpus não encontrado")
def test_corpus_completo_gera_chunks():
    chunks = extract_chunks_from_directory(CORPUS_PATH)
    assert len(chunks) > 100, "Corpus de 20 bulas deve gerar mais de 100 chunks"


@pytest.mark.skipif(not CORPUS_PATH.exists(), reason="Corpus não encontrado")
def test_corpus_tem_multiplos_arquivos():
    chunks = extract_chunks_from_directory(CORPUS_PATH)
    arquivos = {c.arquivo for c in chunks}
    assert len(arquivos) >= 10, "Deve ter chunks de ao menos 10 bulas diferentes"


@pytest.mark.skipif(not CORPUS_PATH.exists(), reason="Corpus não encontrado")
def test_todos_chunks_tem_codigo_item_numerico():
    chunks = extract_chunks_from_directory(CORPUS_PATH)
    for chunk in chunks:
        assert chunk.codigo_item.isdigit(), (
            f"codigo_item deve ser numérico: {chunk.codigo_item!r} em {chunk.arquivo}"
        )
