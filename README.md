# 🟦 Panvel AI Assistant

> Assistente virtual inteligente para o Grupo Panvel — combina RAG sobre bulas de medicamentos com Tool Calling para localização de filiais em tempo real, entregue via SSE com observabilidade estruturada.

---

## 📌 Visão Geral

O **Panvel AI Assistant** é um sistema de IA conversacional construído para demonstrar a integração de técnicas modernas de LLM em um contexto farmacêutico real:

| Capacidade | Tecnologia |
|---|---|
| Perguntas sobre medicamentos | **RAG** com ChromaDB + Embeddings |
| Localização de filiais Panvel | **Tool Calling** estruturado |
| Respostas em tempo real | **SSE** (Server-Sent Events) |
| Auditoria de cada atendimento | **Observabilidade** com Traces |
| Interface web responsiva | **React + Vite** |

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
│   │   │   ├── rag/           # Retriever ChromaDB + Embeddings
│   │   │   ├── prompts/       # Loader de prompts Jinja2
│   │   │   └── repositories/  # Repositório de dados de filiais
│   │   ├── observability/
│   │   │   └── traces.py      # Modelo Trace + TraceRepository em memória
│   │   └── main.py            # Entrypoint FastAPI + CORS
│   └── tests/                 # Suíte Pytest
├── frontend/                  # Interface React (Vite)
│   └── src/
│       ├── App.jsx            # Componente principal com SSE consumer
│       └── index.css          # Design system dark premium
├── data/                      # Bulas de medicamentos (PDF)
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
      ├─► [RAG]  ChromaDB.similarity_search()  →  recupera chunks de bulas
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
```bash
cp .env.example .env
# Edite o .env com sua chave de API
```

### 2. Suba tudo com um único comando
```bash
docker compose up --build
```

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Docs Swagger | http://localhost:8000/docs |

> **Nota:** Na primeira execução, o backend detecta automaticamente que o vector store não existe e roda a ingestão das bulas. Isso pode levar alguns minutos dependendo da sua chave de API.

---

## ☁️ Deploy no Railway (produção)

### Passo 1 — Criar conta e projeto
1. Acesse [railway.app](https://railway.app) e faça login com GitHub
2. Clique em **New Project → Deploy from GitHub repo**
3. Selecione este repositório

### Passo 2 — Criar o serviço de Backend
1. No projeto, clique em **New Service → GitHub Repo**
2. Selecione o repo e configure:
   - **Root Directory:** `backend`
   - **Build:** Railway detecta o `Dockerfile` automaticamente
3. Em **Variables**, adicione todas as variáveis do seu `.env`:
   ```
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-2.0-flash
   GEMINI_API_KEY=sua_chave_aqui
   EMBEDDING_PROVIDER=gemini
   ```
4. Em **Settings → Networking**, clique em **Generate Domain** e copie a URL gerada (ex: `https://panvel-backend.up.railway.app`)

### Passo 3 — Criar o serviço de Frontend
1. No mesmo projeto, clique em **New Service → GitHub Repo**
2. Configure:
   - **Root Directory:** `frontend`
   - **Build:** Railway detecta o `Dockerfile` automaticamente
3. Em **Variables**, adicione:
   ```
   VITE_API_BASE_URL=https://panvel-backend.up.railway.app
   ```
   *(Use a URL do backend gerada no Passo 2)*
4. Em **Settings → Networking**, clique em **Generate Domain**

### Passo 4 — Atualizar CORS do backend
Após ter a URL do frontend, adicione-a nas variáveis do serviço de backend:
```
FRONTEND_URL=https://panvel-frontend.up.railway.app
```

Pronto! 🚀 Ambos os serviços fazem deploy automático a cada `git push` na branch `main`.

---

## ⚙️ Como Rodar Localmente (sem Docker)

### Pré-requisitos

- Python 3.12+
- Node.js 20.x

### 1. Clone e configure o ambiente

```bash
git clone <url-do-repositorio>
cd panvel-ai-assistant

# Copie e edite as variáveis de ambiente
cp .env.example .env
```

### 2. Variáveis de Ambiente (`.env`)

```env
# Provedor de LLM: "gemini" | "openai" | "mock"
LLM_PROVIDER=gemini

# Modelo a utilizar
LLM_MODEL=gemini-2.0-flash

# Chave de API do provedor escolhido
GEMINI_API_KEY=sua_chave_aqui
# OPENAI_API_KEY=sk-...

# Provedor de embeddings (herda LLM_PROVIDER por padrão)
EMBEDDING_PROVIDER=gemini

# Caminho do vector store (ChromaDB)
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

# Indexar bulas no ChromaDB (necessário na primeira execução)
python -m scripts.ingest

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
data: {"step": "routing", "message": "Intenção detectada: rag"}

event: source
data: {"arquivo": "losartana.pdf", "pagina": 3, "score": 0.92}

event: token
data: {"token": "A"}

event: token
data: {"token": "losartana"}

event: done
data: {"trace_id": "abc-123", "latency_ms": 1240, "total_tokens": 312}
```

---

## 🧪 Testes

```bash
cd backend

# Rodar toda a suíte
python -m pytest

# Com cobertura
python -m pytest --cov=app --cov-report=term-missing

# Testes específicos de observabilidade
python -m pytest tests/test_observability.py -v
```

---

## 🔍 Decisões Técnicas

### Por que RAG + Tool Calling ao mesmo tempo?
O assistente precisa responder perguntas **farmacológicas** (informação documental → RAG) e também **localizar filiais** (dado estruturado → Tool). A classificação de intenção por regex e keywords é simples mas demonstra o padrão de roteamento sem adicionar uma chamada extra de LLM.

### Por que SSE ao invés de WebSockets?
SSE é unidirecional e mais simples para este caso de uso. A comunicação é sempre `cliente → backend (POST) → stream de volta`. Não há necessidade de canal bidirecional persistente.

### Por que ChromaDB local?
Elimina dependência de serviço externo para demonstração e entrevistas. O vector store é persistido em disco (`backend/.vector_store`) e carregado automaticamente.

### Por que Traces em memória?
Para fins de demonstração, um repositório em memória thread-safe é suficiente e evita complexidade de banco de dados. Em produção, seria substituído por um backend de observabilidade (ex: Langfuse, Phoenix, ou banco relacional).

### Suporte a múltiplos LLMs via Factory Pattern
O `LLMFactory` permite trocar o provedor (Gemini, OpenAI, Mock) via variável de ambiente sem alterar a lógica de negócio. O **Mock provider** garante que o sistema funcione para demonstração mesmo sem chaves de API.

---

## 🗂️ Stack Completa

**Backend:**
- `FastAPI` — framework web assíncrono
- `ChromaDB` — vector store local para RAG
- `google-generativeai` — SDK Gemini
- `openai` — SDK OpenAI (opcional)
- `Pydantic` — validação de dados e settings
- `pytest` — testes automatizados

**Frontend:**
- `React 18` + `Vite 5` — SPA com HMR
- `lucide-react` — ícones
- `Plus Jakarta Sans` / `JetBrains Mono` — tipografia premium

---

## 👨‍💻 Autor

Desenvolvido como projeto de demonstração de capacidades de IA conversacional aplicadas ao setor farmacêutico — integrando RAG, Tool Calling, streaming SSE e observabilidade estruturada em uma stack moderna Python + React.
