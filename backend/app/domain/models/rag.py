from dataclasses import dataclass


@dataclass(frozen=True)
class BulaChunk:
    """Um trecho de texto extraído de uma bula da Anvisa."""

    texto: str
    codigo_item: str  # extraído do nome do arquivo (ex: "950220")
    arquivo: str      # nome do PDF (ex: "950220_zart_losartana.pdf")
    pagina: int       # página do PDF (1-indexed)
    secao: str        # seção heurística (ex: "INDICAÇÕES", "CONTRAINDICAÇÕES")
    chunk_index: int  # posição do chunk dentro do documento


@dataclass(frozen=True)
class RetrievedChunk:
    """Chunk recuperado por similaridade semântica."""

    chunk: BulaChunk
    score: float  # similaridade coseno (0.0 a 1.0 no ChromaDB = distância invertida)

    @property
    def texto(self) -> str:
        return self.chunk.texto

    @property
    def codigo_item(self) -> str:
        return self.chunk.codigo_item

    @property
    def arquivo(self) -> str:
        return self.chunk.arquivo

    @property
    def pagina(self) -> int:
        return self.chunk.pagina

    @property
    def secao(self) -> str:
        return self.chunk.secao
