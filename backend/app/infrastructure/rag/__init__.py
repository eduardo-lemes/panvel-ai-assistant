"""
RAG infrastructure module.

Exposes:
    - chunker: extrai e divide bulas PDF em BulaChunk
    - embedder: converte texto em vetores (OpenAI ou mock TF-IDF)
    - vector_store: persiste e busca chunks no ChromaDB local
    - retriever: orquestra busca semântica para uma query
"""
