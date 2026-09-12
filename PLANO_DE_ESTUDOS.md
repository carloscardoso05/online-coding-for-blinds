# Plano de estudos — construir um sistema como o Égua Assist

> Documento de apoio à reescrita do Égua Assist. Reúne as trilhas de
> conhecimento necessárias e um plano prático de 8 semanas, cada semana com um
> mini-projeto entregável. A filosofia é **aprender construindo**, usando o
> próprio repositório como material de referência.
>
> Referências de código: salvo indicação, apontam para a branch `master`
> (servidor unificado em `servers/local_assistant.py`) ou para a branch
> `rewrite/servidor-unico` (`servers/api/`, `servers/providers/`,
> `frontend/js/`).

---

## Parte 1 — Trilhas de conhecimento

### 1. Web moderno (a base)

| Tópico | Por quê aqui |
|---|---|
| HTML semântico + CSS | estrutura da IDE, layout editor/saída |
| JavaScript moderno (ES modules, `fetch`, `async/await`, Promises) | hoje o front usa `<script src>` e globais; a reescrita pede módulos |
| Manipulação de áudio: `MediaRecorder`, `Web Audio API`, `AudioContext` | gravar microfone, bips de feedback (`index.html:601` na legada) |
| Web Speech API (`SpeechSynthesis` + `SpeechRecognition`) | TTS pt-BR e transcrição no browser |
| TypeScript | contratos e menos bugs no front da reescrita |

### 2. Acessibilidade (o coração do produto, não um extra)

- WCAG 2.2 e ARIA: `aria-live`, `aria-label`, roles, foco gerenciado.
- Navegação 100% por teclado e leitores de tela (teste real com NVDA,
  VoiceOver ou TalkBack).
- UX para interação por voz: ordem das falas, confirmação antes de agir,
  tolerância a erro de transcrição (no projeto há correção por Levenshtein,
  `js/constructor.js:385` na legada) e latência percebida.
- Design de áudio: ícones sonoros (`audio/start_record.wav`), TTS com
  velocidade/tom (sliders em `index.html` e `js/assist.js` na legada).

### 3. Áudio e fala (STT/TTS)

- Como funciona reconhecimento de fala: amostragem, WAV/PCM, VAD (detecção de
  fala), streaming vs. arquivo fechado.
- Whisper e `faster-whisper` (usado em `servers/local_assistant.py:47`),
  `ffmpeg`.
- APIs de transcrição em tempo real (OpenAI Realtime, Deepgram, Gemini Live) —
  para substituir o "grava 5 s e para".
- TTS moderno (vozes neurais) e streaming de áudio.

### 4. Backend e APIs

- Python intermediário; `asyncio`.
- FastAPI + Pydantic (contratos tipados) — a `master` já é FastAPI.
- **Streaming**: SSE e WebSocket (a maior lacuna atual, tudo é síncrono).
- HTTP: status codes, multipart, CORS, timeouts, retries, cancelamento.
- Upload de arquivos e erros padronizados (`JSONResponse {erro, detalhes}`).
- Testes com `pytest` + `httpx`/`TestClient` (veja `tests/test_api.py` na
  branch `rewrite`).
- Config e segredos: `.env`, `python-dotenv`, nunca commitar chaves.

### 5. LLMs aplicadas

- Conceitos: tokens, janela de contexto, temperatura, top_p, max_tokens,
  latência, custo, alucinação.
- Prompting: system vs. user, few-shot, regras de saída, diferença entre prompt
  de regras e prompt de dados.
- APIs e SDKs: OpenAI, Gemini, Ollama (local, compatível com OpenAI — é o motor
  da `master`).
- **Structured output/function calling/JSON schema** — o salto de qualidade para
  o construtor (hoje é "traduza este JSON").
- Local vs. cloud: quantização (GGUF), embeddings locais vs. pagos, fallback.
- Evals de prompt: conjunto de testes com respostas esperadas e medição de
  regressões (o projeto não tem nada disso).
- Segurança: prompt injection, limites de custo, conteúdo impróprio.

### 6. RAG (Retrieval-Augmented Generation)

- Embeddings: como funcionam, modelos multilíngues (o `all-MiniLM-L6-v2` atual é
  fraco em português), dimensão e normalização.
- Similaridade: cosseno, produto interno, distância L2.
- Chunking e curadoria de datasets (os `.jsonl` do projeto são exemplos
  curados à mão).
- Vector stores: FAISS (atual), pgvector, Qdrant, LanceDB, sqlite-vec.
- Busca híbrida (BM25 + vetorial), reranking, filtros por metadata e
  **threshold de score** (ausente hoje).
- Avaliação de retrieval: recall@k, MRR, precision; medir se os exemplos
  recuperados são os certos.
- Pipeline de indexação: versionamento e reindexação automática (a `rewrite` já
  compara mtime; a `master` não).

### 7. Linguagens, parsers e interpretadores

- Lexer, tokens, parser, AST e interpretador tree-walking — é o que roda em
  `js/egua/egua.min.js` e alimenta o explicador com `tokens`/`ast`/`output`.
- Bônus valioso para a reescrita: usar o parser **no servidor** para
  validar/corrigir o código gerado pela LLM antes de exibir.

### 8. Arquitetura e engenharia de software

- Padrão **adapter/providers**: uma interface única para LLMs/transcrição (a
  branch `rewrite` já faz isso em `servers/providers/`).
- Separação de camadas: domínio (regras Égua), infraestrutura (LLM, banco,
  áudio) e API.
- Observabilidade: logging estruturado (a `rewrite` tem request-id),
  OpenTelemetry, métricas de tokens/custo/latência.
- Git/GitHub, Docker + Compose, CI (lint `ruff`/`eslint`, testes).
- Contratos: OpenAPI, versionamento e testes de contrato com providers mockados.

### 9. Frontend da nova geração

- Um framework com boa acessibilidade: React, Vue, Svelte ou Solid — todos
  servem se você tratar ARIA/foco com rigor.
- Gerenciamento de estado (store) e streaming de UI (resposta token a token).
- Editor de código acessível: CodeMirror 6 ou Monaco (o atual é CodeFlask);
  avaliar leitura por linha/caractere com leitor de tela.

### Recursos que valem o tempo

- MDN Web Docs (Web Speech, MediaRecorder, ARIA) e W3C WCAG.
- Documentação oficial do FastAPI/Pydantic, Ollama, FAISS, OpenAI e Gemini.
- "Designing Machine Learning Systems" (Chip Huyen) para visão de produto com
  IA; "Speech and Language Processing" (Jurafsky & Martin) para NLP/fala.
- Pratique leitor de tela desde o dia 1 — é o "teste unitário" de
  acessibilidade.

---

## Parte 2 — Plano prático de 8 semanas

Regras do plano:

- 2/3 do tempo é código, 1/3 é leitura/estudo.
- Cada semana termina com um entregável funcionando, por menor que seja.
- Todo entregável é testado com teclado **e** leitor de tela.
- Use o repositório como referência: compare o que você construir com o código
  da `master` e da `rewrite`.
- Os nomes de repositório são sugestões; a stack é um ponto de partida, não uma
  camisa de força.

### Semana 1 — Web + acessibilidade + voz no browser

**Objetivo:** dominar gravação, transcrição e fala no navegador, com
acessibilidade desde o início.

- Tópicos: MediaRecorder, Web Audio, Web Speech API, ARIA live regions, foco,
  WCAG.
- **Projeto:** página acessível que grava áudio do microfone, transcreve com
  Web Speech API, exibe o texto numa `aria-live` e fala a resposta com
  `SpeechSynthesis`, com sliders de velocidade/tom.
- **Repositório sugerido:** `voz-acessivel-web`
- **Stack sugerida:** Vite + TypeScript (sem framework no começo); Web Speech
  API, MediaRecorder e Web Audio API; testes de acessibilidade com Playwright +
  axe-core; leitor de tela (NVDA) desde o primeiro commit.
- **Pronto quando:** um usuário consegue operar tudo só com teclado e leitor de
  tela, com feedback falado em cada ação.
- Referência no repo: `index.html` (handler do microfone) e `js/assist.js`
  (TTS/atalhos) na legada.

### Semana 2 — Backend FastAPI + streaming

**Objetivo:** subir um backend tipado e transmitir resposta token a token.

- Tópicos: FastAPI, Pydantic, `asyncio`, SSE, StreamingResponse, CORS,
  tratamento de erro, logging estruturado.
- **Projeto:** endpoint `POST /chat` que chama o Ollama (`localhost:11434/v1`)
  e devolve a resposta em streaming via SSE; front mínimo que imprime os tokens
  conforme chegam.
- **Repositório sugerido:** `ollama-chat-streaming`
- **Stack sugerida:** Python 3.12 + `uv`; FastAPI + Pydantic v2; SSE com
  `sse-starlette` ou `StreamingResponse`; SDK `openai` apontando para o Ollama;
  front em TypeScript com `EventSource`; Docker Compose opcional.
- **Pronto quando:** a resposta aparece incrementalmente no front e a falha do
  Ollama retorna erro JSON claro, não stack trace.
- Referência no repo: `servers/local_assistant.py:181-200` (chamada Ollama
  síncrona) — sua versão deve ser a evolução streaming dela.

### Semana 3 — Prompting e structured output

**Objetivo:** controlar o que a LLM devolve em vez de confiar em texto livre.

- Tópicos: system/user, few-shot, temperatura/top_p, JSON schema,
  function calling/structured outputs, evals simples.
- **Projeto:** tradutor de frases em português para JSON validado por schema
  (ex.: `{acao, tipo, nome, valor}`). Se o JSON não validar, exibir erro e não
  deixar passar. Monte 20 casos de teste com resultado esperado.
- **Repositório sugerido:** `egua-structured-output`
- **Stack sugerida:** Python + FastAPI; Pydantic para o schema; OpenAI SDK
  (`response_format`/function calling) ou a lib `instructor`; Ollama como
  provedor local; `pytest` para os 20 casos; `promptfoo` para comparar prompts.
- **Pronto quando:** o conjunto de 20 casos passa com consistência e você
  consegue medir a taxa de acerto antes/depois de mudar o prompt.
- Referência no repo: `SISTEMA_CONSTRUIR` e o fluxo do construtor por voz
  (hoje a saída é texto livre; o schema é o upgrade).

### Semana 4 — RAG do zero, parte 1

**Objetivo:** entender cada peça do RAG sem framework.

- Tópicos: embeddings, normalização, similaridade de cosseno, FAISS,
  persistência de índice e metadados.
- **Projeto:** indexar `rag/RAG_exemplos_codigo.jsonl` + `rag/docs.txt` com um
  modelo de embedding **multilíngue**, buscar top-k e devolver os itens com
  score. Endpoint `/buscar`.
- **Repositório sugerido:** `rag-do-zero`
- **Stack sugerida:** Python + `uv`; `sentence-transformers` com
  `intfloat/multilingual-e5-small` ou `paraphrase-multilingual-MiniLM-L12-v2`;
  `faiss-cpu`; NumPy; FastAPI para o endpoint; scripts de indexação em
  `scripts/`.
- **Pronto quando:** dada uma pergunta em português sem palavras em comum com
  os exemplos, a busca recupera um exemplo relevante e você vê o score.
- Referência no repo: `servers/local_assistant.py:51-147` (classe `IndiceRAG`).

### Semana 5 — RAG do zero, parte 2 (qualidade)

**Objetivo:** transformar o RAG de "funciona" em "confiável".

- Tópicos: chunking, threshold de score, busca híbrida (BM25 + vetorial),
  reranking, filtros por metadata (jsonl vs. doc), avaliação (recall@k, MRR).
- **Projeto:** evoluir o `/buscar` da semana 4 com threshold, filtro por tipo e
  um mini-conjunto de avaliação (20 perguntas → item esperado) medindo
  recall@5; comparar com/sem reranking.
- **Repositório sugerido:** `rag-qualidade`
- **Stack sugerida:** reaproveitar a semana 4 + `rank-bm25` (busca híbrida);
  cross-encoder da `sentence-transformers` para reranking; `pytrec_eval` ou
  `ranx` para recall@k/MRR; opcional trocar FAISS por `qdrant-client` ou
  `pgvector` (Postgres) para comparar.
- **Pronto quando:** você tem números antes/depois e sabe justificar cada
  parâmetro do retrieval.
- Referência no repo: os três índices `unified_*` e seus top-k fixos
  (`local_assistant.py:152-176`); a reindexação por mtime da `rewrite`.

### Semana 6 — Interpretador Égua e validação de código

**Objetivo:** parar de confiar cegamente no código que a LLM devolve.

- Tópicos: lexer, parser, AST, interpretador; estudo do `js/egua/egua.min.js`.
- **Projeto:** serviço que recebe código Égua, roda lexer/parser e devolve
  `{ok, tokens, ast, erro}`. Usar isso para validar a saída do gerador e tenho
  um mecanismo de reparo guiado pelo erro de parse.
- **Repositório sugerido:** `egua-parser-service`
- **Stack sugerida:** Node.js + TypeScript reaproveitando o parser de
  `js/egua/egua.min.js` (ou portar para Python com `Lark`/`PLY`); API em
  FastAPI ou Express; testes com `pytest` ou `Vitest`.
- **Pronto quando:** código com erro de sintaxe retorna a linha e a mensagem, e
  o pipeline rejeita (ou corrige) o output inválido da LLM.
- Referência no repo: `js/explain-code.js:83-114` (lexer/parser/`runBlock`) na
  legada; dataset `RAG_token_parser_interpreter_examples.jsonl`.

### Semana 7 — Arquitetura, providers e observabilidade

**Objetivo:** organizar o sistema para crescer sem virar 17 processos.

- Tópicos: adapter/providers, injeção de dependência, config central, segredos,
  logging com request-id, OpenTelemetry, testes de contrato com mocks,
  Docker/Compose.
- **Projeto:** camada `providers/` com uma interface única
  `chat(sistema, usuario, params)` implementada por Ollama/OpenAI/Gemini +
  fake para testes; rotas `/gerar-codigo`, `/explicar`, `/construir` usando
  essa camada; testes que rodam sem rede.
- **Repositório sugerido:** `llm-providers-gateway`
- **Stack sugerida:** Python + FastAPI; `pydantic-settings` para config; SDKs
  `openai` e `google-generativeai` + Ollama; `structlog` ou
  `python-json-logger`; `httpx` + `respx` para mockar provedores;
  OpenTelemetry; `ruff` + `pytest`; Docker Compose.
- **Pronto quando:** trocar de provedor é mudar uma string no payload, os
  testes passam offline e cada request tem log com id, duração e tokens.
- Referência no repo: `servers/providers/` e `servers/api/` da `rewrite`.

### Semana 8 — Integração final (MVP da reescrita)

**Objetivo:** juntar tudo num fluxo ponta a ponta.

- **Projeto:** MVP com o ciclo completo: voz → transcrição → geração de código
  (com RAG) → validação no parser → execução no browser → explicação falada.
  Front acessível (teclado + leitor de tela), backend com streaming de tokens e
  TTS em fila com cancelamento.
- **Repositório sugerido:** `egua-assist-v2` (ou `egua-assist-mvp`)
- **Stack sugerida:** backend FastAPI + camada de providers + RAG da semana 5 +
  validação da semana 6; front em TypeScript com React/Svelte/Solid e
  CodeMirror 6; SSE para tokens e TTS; `faster-whisper`/Web Speech para STT;
  Playwright + axe-core para acessibilidade; GitHub Actions + Docker Compose.
- **Pronto quando:** uma pessoa cega consegue criar, executar e ouvir a
  explicação de um programa simples sem tocar no mouse, e cada etapa tem
  log/métrica.
- Referência no repo: todos os fluxos documentados em
  `ANALISE_FLUXOS_E_LLMS.md`.

---

## Mapa rápido: projeto da semana → trilhas cobertas

| Semana | Projeto | Repositório sugerido | Trilhas |
|---|---|---|---|
| 1 | Voz acessível no browser | `voz-acessivel-web` | 1, 2, 3 |
| 2 | FastAPI + streaming | `ollama-chat-streaming` | 4 |
| 3 | Structured output | `egua-structured-output` | 4, 5 |
| 4 | RAG parte 1 | `rag-do-zero` | 6 |
| 5 | RAG parte 2 (qualidade) | `rag-qualidade` | 5, 6 |
| 6 | Validação Égua (parser) | `egua-parser-service` | 7 |
| 7 | Providers + observabilidade | `llm-providers-gateway` | 4, 8 |
| 8 | MVP integrado | `egua-assist-v2` | 1–9 |

## Hábitos que fazem diferença

- Escreva testes de acessibilidade ("consigo operar isso só com teclado?") em
  todo entregável.
- Meça antes de otimizar prompt/RAG: sem números, toda mudança é achismo.
- Registre custos e latência desde o início — é o que inviabiliza sistemas de
  IA em produção.
- Leia o código do próprio repositório como documentação: `ANALISE_FLUXOS_E_LLMS.md`
  diz onde olhar.
