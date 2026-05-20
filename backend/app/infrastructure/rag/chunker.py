"""
Chunker de bulas da Anvisa.

Estratégia:
- Extrai texto página a página com pypdf
- Detecta seção heurística pelo início da linha (maiúsculas)
- Divide em chunks de ~500 tokens com overlap de ~50 tokens
- Preserva metadados: codigo_item, arquivo, pagina, secao, chunk_index
"""

import re
from pathlib import Path

from pypdf import PdfReader

from app.domain.models.rag import BulaChunk

# Palavras típicas de início de seção em bulas da Anvisa
_SECTION_PATTERN = re.compile(
    r"^([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÀÇ][A-ZÁÉÍÓÚÂÊÎÔÛÃÕÀÇ\s\-]{4,})$",
    re.MULTILINE,
)

CHUNK_SIZE = 500    # tokens aproximados (palavras)
CHUNK_OVERLAP = 50  # overlap entre chunks


def _extract_codigo_item(filename: str) -> str:
    """Extrai o código numérico do nome do arquivo. Ex: '950220_zart_losartana.pdf' → '950220'."""
    stem = Path(filename).stem
    parts = stem.split("_")
    return parts[0] if parts else stem


def _detect_section(text: str) -> str:
    """Retorna o último cabeçalho de seção encontrado no texto, ou 'GERAL'."""
    matches = _SECTION_PATTERN.findall(text)
    if matches:
        return matches[-1].strip()
    return "GERAL"


def _tokenize(text: str) -> list[str]:
    """Divide texto em tokens (palavras + pontuação). Simples e sem dependência de NLTK."""
    return text.split()


def _chunk_tokens(tokens: list[str], size: int, overlap: int) -> list[list[str]]:
    """Divide lista de tokens em janelas com overlap."""
    if not tokens:
        return []
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + size
        chunks.append(tokens[start:end])
        if end >= len(tokens):
            break
        start = end - overlap
    return chunks


def extract_chunks_from_pdf(pdf_path: Path) -> list[BulaChunk]:
    """
    Extrai todos os BulaChunk de um único PDF.

    Preserva página e detecta seção heuristicamente.
    Chunks muito curtos (< 20 tokens) são descartados.
    """
    filename = pdf_path.name
    codigo_item = _extract_codigo_item(filename)

    reader = PdfReader(str(pdf_path))
    chunks: list[BulaChunk] = []
    chunk_index = 0
    current_section = "GERAL"

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if not page_text.strip():
            continue

        # Atualiza seção detectada nesta página
        detected = _detect_section(page_text)
        if detected != "GERAL":
            current_section = detected

        tokens = _tokenize(page_text)
        page_chunks = _chunk_tokens(tokens, CHUNK_SIZE, CHUNK_OVERLAP)

        for token_chunk in page_chunks:
            if len(token_chunk) < 20:
                continue  # descarta fragmentos muito pequenos
            texto = " ".join(token_chunk)
            chunks.append(
                BulaChunk(
                    texto=texto,
                    codigo_item=codigo_item,
                    arquivo=filename,
                    pagina=page_num,
                    secao=current_section,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return chunks


def extract_chunks_from_directory(corpus_path: Path) -> list[BulaChunk]:
    """Extrai chunks de todos os PDFs em um diretório."""
    pdf_files = sorted(corpus_path.glob("*.pdf"))
    all_chunks: list[BulaChunk] = []
    for pdf_path in pdf_files:
        file_chunks = extract_chunks_from_pdf(pdf_path)
        all_chunks.extend(file_chunks)
    return all_chunks
