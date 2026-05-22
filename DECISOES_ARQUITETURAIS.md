A arquitetura foi separada em camadas (domínio, aplicação, infraestrutura e API) pra deixar o projeto mais organizado e fácil de manter. Isso facilita trocar coisas como o provedor de IA sem mexer na regra de negócio.

Preferi fazer a orquestração em Python puro ao invés de usar LangChain ou LlamaIndex, porque dá mais controle, menos complexidade e facilita debug.

Como a base de bulas era pequena, usei busca vetorial em memória com NumPy ao invés de banco vetorial. Ficou mais leve e rápido pro tamanho atual do projeto.

O roteamento das intenções foi feito com regras e regex, sem usar LLM pra classificar mensagem. Isso evita gastar tokens e reduz bastante a latência.

Pra streaming das respostas usei SSE ao invés de WebSocket, porque o fluxo é simples e SSE já resolve bem com menos complexidade.

Na busca de filiais adicionei paginação e total de resultados pra evitar jogar informação demais no prompt e gastar token desnecessário.

Também tratei consultas mais gerais do RAG direto no backend, porque busca vetorial funciona melhor pra contexto específico do que perguntas amplas.

Como a base era pequena, cerca de 20 PDFs e uns 600 chunks, eu optei por não usar banco vetorial tipo ChromaDB ou Qdrant porque seria uma complexidade desnecessária pro cenário.

A busca vetorial foi feita em memória usando NumPy com similaridade cosseno, que já entregava resposta praticamente instantânea nessa escala.

Usar um banco vetorial adicionaria mais infraestrutura, mais consumo de recurso e mais setup local, sem trazer ganho real de performance pro tamanho atual do projeto.

A arquitetura ficou desacoplada, então se no futuro a quantidade de documentos crescer bastante, seria simples trocar essa camada por um banco vetorial dedicado.

Nos testes usei mocks das LLMs pra conseguir validar tudo offline sem depender de API externa. Hoje o projeto tem testes automatizados.

E cada requisição gera traces com métricas de latência, tokens e etapas executadas, ajudando bastante no monitoramento e debug. 
