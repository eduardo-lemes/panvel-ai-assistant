# Panvel AI Assistant

Assistente conversacional para o case tecnico de IA Generativa da Panvel.

## Escopo atual

O projeto esta sendo construido para atender dois tipos de pergunta:

- perguntas farmacologicas com base em bulas reais via RAG;
- perguntas sobre filiais do Parana via tool calling sobre dados estruturados.

Nesta etapa, apenas o backend base em FastAPI foi iniciado.

Endpoints atuais:

- `GET /health`
- `POST /chat/stream`

## Estrutura

```text
backend/   API FastAPI e testes
data/      insumos do case: parquet, dicionario e bulas
frontend/  interface de chat
docs/      notas internas e documentacao futura
prompts/   prompts produtivos quando fizerem parte do produto
```

## Rodar o backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Health check:

```text
GET http://localhost:8000/health
```

Streaming SSE:

```text
POST http://localhost:8000/chat/stream
```

## Variaveis de ambiente

As variaveis iniciais ficam em `.env.example`.

## LLM provider

O backend suporta provider substituivel por variavel de ambiente.

- `LLM_PROVIDER=mock` para desenvolvimento local sem chave
- `LLM_PROVIDER=openai` para usar a API da OpenAI

Variaveis principais:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OPENAI_API_KEY`
