# 🟦 Panvel AI Assistant

> Assistente virtual inteligente para o Grupo Panvel — combina RAG sobre bulas de medicamentos com Tool Calling para localização de filiais em tempo real, entregue via SSE com observabilidade estruturada.

---

## 📌 Visão Geral

O **Panvel AI Assistant** é um sistema de IA conversacional construído para demonstrar a integração de técnicas modernas de LLM em um contexto farmacêutico real:

| Capacidade | Tecnologia |
|---|---|
| Perguntas sobre medicamentos | **RAG** com vector store local + Embeddings Gemini |
| Localização de filiais Panvel | **Tool Calling** estruturado (Parquet) |
| Respostas em tempo real | **SSE** (Server-Sent Events) |
| Histórico de conversa | **Context window** com últimas 3 turns |
| Auditoria de cada atendimento | **Observabilidade** com Traces em memória |
| Interface web responsiva | **React + Vite** com Markdown renderizado |

---

## 🏗️ Arquitetura

```
panvel-ai-assistant/
├── backend/                   # API FastAPI (Python 3.12)
│   ├── app/
│   │   ├── api/               # Endpoints REST + SSE
│   │   │   └── routes/
│   │   │       ├── chat.py    # POST /chat/stream (SSE)
│   │   │       ├── traces.py  # GET /chat/traces
│   │   │       └── health.py  # GET /health
│   │   ├── application/
│   │   │   └── services/
│   │   │       ├── chat.py    # Orquestrador principal do pipeline
│   │   │       └── filial_tools.py  # Tools de busca de filiais
│   │   ├── domain/
│   │   │   └── models/        # Modelos Pydantic (ChatEvent, Trace, etc.)
│   │   ├── infrastructure/
│   │   │   ├── config/        # Settings via Pydantic + dotenv
│   │   │   ├── llm/           # Factory de provedores LLM (Gemini / OpenAI / Mock)
│   │   │   ├── rag/           # Retriever vetorial + Embeddings
│   │   │   ├── prompts/       # Loader de prompts Markdown
│   │   │   └── repositories/  # Repositório de filiais (Parquet)
│   │   ├── observability/
│   │   │   └── traces.py      # Modelo Trace + TraceRepository em memória
│   │   └── main.py            # Entrypoint FastAPI + CORS
│   ├── scripts/
│   │   └── ingest_bulas.py    # Script de indexação das bulas no vector store
│   └── tests/                 # Suíte Pytest (48 testes)
├── frontend/                  # Interface React (Vite)
│   └── src/
│       ├── App.jsx            # Componente principal com SSE consumer
│       └── index.css          # Design system dark premium
├── data/
│   ├── corpus_bulas/          # PDFs das bulas de medicamentos
│   └── filiais.parquet        # Base de dados das filiais Panvel
├── prompts/                   # System prompts do assistente (Markdown)
└── .env                       # Variáveis de ambiente (não versionado)
```

### Fluxo de uma Requisição

```
[Frontend React]
      │ POST /chat/stream  (SSE)
      ▼
[FastAPI – chat.py]
      │
      ├─► _classify_intent()  →  roteamento por keyword/regex
      │
      ├─► [HISTORY] TraceRepository.get_conversation_history()  →  últimas 3 turns
      │
      ├─► [RAG]  vector_store.search()  →  recupera chunks de bulas
      │          event: source { arquivo, pagina, score }
      │
      ├─► [TOOL] buscar_filiais() / detalhes_filial()
      │          event: tool_call { tool_name, arguments, result }
      │
      ├─► [LLM]  Gemini / OpenAI / Mock  →  streaming de tokens
      │          event: token { token }
      │
      ├─► [TRACE] persiste Trace com latências, tokens, fontes
      │           event: done { trace_id, latency_ms, total_tokens }
      │
      └─► [Frontend] renderiza pipeline visual em tempo real
```

---

## 🐳 Rodar com Docker (recomendado)

### Pré-requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando

### 1. Configure o `.env`

Crie o arquivo `.env` na raiz do projeto com o seguinte conteúdo:

```env
APP_NAME=Panvel AI Assistant API
APP_VERSION=0.1.0
APP_ENV=local
APP_DEBUG=false
LOG_LEVEL=INFO

# Provedor de LLM: "gemini" | "openai" | "mock"
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash

# Chave de API
GEMINI_API_KEY=sua_chave_aqui
# OPENAI_API_KEY=sk-...

# Provedor de embeddings (herda LLM_PROVIDER por padrão)
EMBEDDING_PROVIDER=gemini

# Caminho do vector store dentro do container Docker
VECTOR_STORE_PATH=/app/.vector_store
```

> **Importante:** `VECTOR_STORE_PATH=/app/.vector_store` aponta para onde o Docker monta o volume de persistência. Não altere esse valor ao rodar com Docker.

### 2. Suba tudo com um único comando

```bash
docker compose up --build
```

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Docs Swagger | http://localhost:8000/docs |

> **Nota:** Na primeira execução, o backend detecta automaticamente que o vector store não existe e roda a ingestão das bulas. Isso pode levar **2–5 minutos** dependendo da velocidade da sua chave de API de embeddings.

---

## ⚙️ Como Rodar Localmente (sem Docker)

### Pré-requisitos

- Python 3.12+
- Node.js 20.x

### 1. Clone e configure o ambiente

```bash
git clone <url-do-repositorio>
cd panvel-ai-assistant
```

### 2. Variáveis de Ambiente (`.env`)

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=sua_chave_aqui
EMBEDDING_PROVIDER=gemini

# Para rodar localmente sem Docker, aponte para o diretório local
VECTOR_STORE_PATH=./backend/.vector_store
```

### 3. Backend (FastAPI)

```bash
cd backend

# Criar e ativar virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Instalar dependências
pip install -r requirements.txt

# Indexar bulas no vector store (necessário na primeira execução)
python scripts/ingest_bulas.py

# Iniciar servidor de desenvolvimento
uvicorn app.main:app --reload --port 8000
```

A API estará disponível em: **http://localhost:8000**  
Documentação Swagger: **http://localhost:8000/docs**

### 4. Frontend (React + Vite)

```bash
cd frontend

npm install
npm run dev
```

A interface estará disponível em: **http://localhost:5173**

---

## 🔌 Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Health check do serviço |
| `POST` | `/chat/stream` | Chat com streaming SSE |
| `GET` | `/chat/traces` | Lista todos os traces |
| `GET` | `/chat/traces/{id}` | Detalha um trace específico |

### Exemplo — POST /chat/stream

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "conv-123", "message": "Para que serve a losartana?"}'
```

**Resposta (SSE):**
```
event: trace
data: {"step": "started", "message": "Iniciando atendimento..."}

event: trace
data: {"step": "routing", "message": "Intenção detectada: rag"}

event: source
data: {"arquivo": "950220_zart_losartana.pdf", "pagina": 3, "score": 0.92}

event: token
data: {"token": "A losartana"}

event: done
data: {"trace_id": "abc-123", "latency_ms": 1240, "total_tokens": 312}
```

---

## 🧪 Testes

```bash
cd backend

# Rodar toda a suíte (48 testes)
python -m pytest

# Com cobertura
python -m pytest --cov=app --cov-report=term-missing

# Testes específicos
python -m pytest tests/test_observability.py -v
python -m pytest tests/test_filial_tools.py -v
python -m pytest tests/test_chat_orchestration.py -v
```

---

## 🔍 Decisões Técnicas

### Por que RAG + Tool Calling ao mesmo tempo?
O assistente precisa responder perguntas **farmacológicas** (informação documental → RAG) e também **localizar filiais** (dado estruturado → Tool). A classificação de intenção por regex e keywords é simples mas demonstra o padrão de roteamento sem adicionar uma chamada extra de LLM.

### Por que SSE ao invés de WebSockets?
SSE é unidirecional e mais simples para este caso de uso. A comunicação é sempre `cliente → backend (POST) → stream de volta`. Não há necessidade de canal bidirecional persistente.

### Por que vector store próprio ao invés de ChromaDB?
A implementação usa NumPy + JSON para persistência e similaridade coseno para busca. Elimina dependências de compilação nativa e simplifica o setup em containers. Para produção, seria substituído por Qdrant, pgvector ou similar.

### Por que Traces em memória?
Para fins de demonstração, um repositório em memória thread-safe é suficiente e evita complexidade de banco de dados. Em produção, seria substituído por um backend de observabilidade (ex: Langfuse, Phoenix, ou banco relacional).

### Suporte a múltiplos LLMs via Factory Pattern
O `LLMFactory` permite trocar o provedor (Gemini, OpenAI, Mock) via variável de ambiente sem alterar a lógica de negócio. O **Mock provider** garante que o sistema funcione para demonstração mesmo sem chaves de API.

### Histórico de conversa via TraceRepository
Em vez de manter sessão server-side, o histórico é reconstruído a partir dos últimos 3 traces completos do `conversation_id`. Isso mantém a arquitetura stateless e permite observabilidade natural das turns anteriores.

---

## 🗂️ Stack Completa

**Backend:**
- `FastAPI` — framework web assíncrono
- `NumPy` — vector store local para RAG (similaridade coseno)
- `pypdf` — extração de texto das bulas em PDF
- `openai` — SDK compatível com Gemini e OpenAI
- `pandas` / `pyarrow` — leitura do arquivo Parquet de filiais
- `Pydantic` — validação de dados e settings
- `pytest` — 48 testes automatizados

**Frontend:**
- `React 18` + `Vite 5` — SPA com HMR
- `react-markdown` — renderização de Markdown nas respostas do LLM
- `lucide-react` — ícones
- `Plus Jakarta Sans` / `JetBrains Mono` — tipografia premium

---

## 👨‍💻 Autor

Desenvolvido como projeto de demonstração de capacidades de IA conversacional aplicadas ao setor farmacêutico — integrando RAG, Tool Calling, streaming SSE e observabilidade estruturada em uma stack moderna Python + React.
