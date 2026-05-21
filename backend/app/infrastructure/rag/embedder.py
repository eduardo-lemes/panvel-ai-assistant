"""
Embedder: converte texto em vetores numéricos.

- OpenAIEmbedder: usa text-embedding-3-small (requer OPENAI_API_KEY)
- MockEmbedder: TF-IDF com sklearn, funciona sem chave — para dev/testes
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Converte uma lista de textos em vetores de embedding."""

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


# ---------------------------------------------------------------------------
# OpenAI Embedder
# ---------------------------------------------------------------------------

class OpenAIEmbedder(Embedder):
    MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str) -> None:
        from openai import OpenAI
        if not api_key:
            raise ValueError("OPENAI_API_KEY é obrigatório para embedding_provider=openai.")
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # A API aceita até 2048 inputs por chamada; bulas raramente passam disso
        response = self._client.embeddings.create(
            model=self.MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Mock Embedder (TF-IDF cosine — sem chave, para dev e testes)
# ---------------------------------------------------------------------------

class MockEmbedder(Embedder):
    """
    Embedder local baseado em TF-IDF.

    Não requer chave de API. Usado quando EMBEDDING_PROVIDER=mock.
    Qualidade inferior ao OpenAI, mas suficiente para validar o pipeline.
    """

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vectorizer = TfidfVectorizer(
            max_features=1024,
            strip_accents="unicode",
            analyzer="word",
            ngram_range=(1, 2),
        )
        self._fitted = False
        self._corpus: list[str] = []

    def fit(self, texts: list[str]) -> None:
        """Treina o vocabulário TF-IDF. Deve ser chamado antes do primeiro embed."""
        self._vectorizer.fit(texts)
        self._fitted = True
        logger.info("MockEmbedder TF-IDF treinado com %d documentos.", len(texts))

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            # Auto-fit com os próprios textos (usado em queries isoladas)
            self.fit(texts)
        matrix = self._vectorizer.transform(texts)
        return matrix.toarray().tolist()


# ---------------------------------------------------------------------------
# Gemini Embedder
# ---------------------------------------------------------------------------

class GeminiEmbedder(Embedder):
    MODEL = "gemini-embedding-2"

    def __init__(self, api_key: str) -> None:
        from openai import OpenAI
        if not api_key:
            raise ValueError("GEMINI_API_KEY é obrigatório para embedding_provider=gemini.")
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_embedder(
    embedding_provider: str,
    openai_api_key: str | None,
    gemini_api_key: str | None = None,
) -> Embedder:
    if embedding_provider == "openai":
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY é necessário quando EMBEDDING_PROVIDER=openai."
            )
        logger.info("Usando OpenAIEmbedder (text-embedding-3-small).")
        return OpenAIEmbedder(api_key=openai_api_key)

    if embedding_provider == "gemini":
        if not gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY é necessário quando EMBEDDING_PROVIDER=gemini."
            )
        logger.info("Usando GeminiEmbedder (gemini-embedding-2).")
        return GeminiEmbedder(api_key=gemini_api_key)

    if embedding_provider == "mock":
        logger.info("Usando MockEmbedder (TF-IDF local). Para embeddings reais, defina EMBEDDING_PROVIDER=openai ou gemini.")
        return MockEmbedder()

    raise ValueError(f"Unsupported embedding provider: {embedding_provider}")
