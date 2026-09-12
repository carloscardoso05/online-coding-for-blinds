# Análise de fluxos e comunicação com LLMs — Égua Assist

> Documento de referência para a reescrita do projeto. Descreve como o sistema
> funcionava na arquitetura legada e como está no estado atual.
>
> - **Arquitetura legada analisada:** commit `84191eb` (microserviços Flask/Node/PHP)
> - **Estado atual analisado:** branch `rewrite/servidor-unico`, commit `3d4549f` (FastAPI único)
>
> Convenção de caminhos: arquivos como `js/*.js`, `servers/code_generation/*`,
> `servers/code_explainer/*`, `servers/block_constructor/*` e `transcribe.php`
> existem apenas no commit legado `84191eb`. Caminhos como `frontend/js/*`,
> `servers/api/*`, `servers/core/*`, `servers/providers/*`, `app.py` e `start.py`
> referem-se ao estado atual (`3d4549f`).

---

## 1. Visão geral

O Égua Assist é uma IDE web de ensino de lógica de programação para pessoas com
deficiência visual, baseada na linguagem **Égua** (https://egua.dev). A interação
é guiada por voz (TTS pt-BR + entrada por microfone), com atalhos de teclado e
`aria-label` em todos os controles. O sistema usa LLMs para três tarefas
distintas — **gerar código**, **traduzir JSON estruturado em código** e
**explicar a execução** — e um modelo de transcrição para converter fala em
texto.

Princípios que regem todos os fluxos:

- A LLM **nunca executa código**. O interpretador Égua roda no navegador
  (`js/explain-code.js:83` no legado).
- Toda chamada de LLM é **síncrona, sem streaming**, tanto no legado quanto no
  estado atual.
- O RAG (retrieval + few-shot) é usado em todas as tarefas para ancorar a LLM
  na sintaxe da linguagem Égua.

---

## 2. Diagrama geral

```
Microfone ──► [TRANSCRIÇÃO] ──► texto ──► [GERAÇÃO DE CÓDIGO] ──► código Égua ──► editor
                  │                              ▲                                    │
                  │ (construtor)                 │ RAG (docs + exemplos few-shot)     │ Executar
                  ▼                              │                                    ▼
      [perguntas guiadas por voz] ──► JSON ──► [TRADUÇÃO JSON→CÓDIGO]        [INTERPRETADOR ÉGUA]
                  │                                                                   │
                  ▼                                                                   ▼
      [converter extenso→número :5050]                                      tokens/AST/output
                  │                                                                   │
                  └───────────────────────────────────────────────────────────────────┤
                                                                                      ▼
                                                                            [EXPLICAÇÃO PEDAGÓGICA]
                                                                                      │
                                                                                      ▼
                                                                            resposta markdown ──► TTS
```

---

## 3. Fluxos (arquitetura legada `84191eb`)

### 3.1 Fluxo 1 — Ditado livre: voz → transcrição → código

1. `#startButton` (`index.html:617`) lê o engine em `getTranscriptionModel()`
   (`js/translate-models.js:62`). Com `web-speech-api` usa o browser; senão grava
   via `MediaRecorder` e chama `sendAudioToServer` (`js/translate-models.js:70`).
2. `sendAudioToServer` envia `FormData` com campo `audio` para `transcribeURLS`
   (`js/translate-models.js:53`):
   - `whisper-local` → `localhost:3000/transcrever` (FastAPI, `whisper-turbo`,
     pt) → JSON `{"transcricao"}` (o front lê como texto puro — inconsistência);
   - `whisper-api` → `transcribe.php` (proxy OpenAI `whisper-1`) → texto puro;
   - `gemini-speech` → `localhost:2000/transcribe` (Node + Gemini) → texto puro.
3. O texto passa por `formatText` (quebra em linhas de ~100 caracteres) e vai
   para `sendData` (`js/translate-models.js:886`): **POST JSON**
   `{prompt, codigo_atual}` para `modelURLs` (`:877`): Gemini 4000, GPT 4100,
   phi 4300, llama 4400, qwen2 4500, transformer 6969.
4. O servidor monta um prompt único (o Gemini antigo achatava system+user; o GPT
   separava em `system`/`user`): bloco fixo de regras ("Você é um assistente
   especialista na linguagem Égua... responda APENAS o próximo trecho";
   normalização de nomes, aspas duplas, números por extenso→numérico,
   "baseie-se fortemente nos exemplos", "entrada inválida → não retorne nada")
   + RAG injetado como texto (`--- INFORMAÇÕES DE REFERÊNCIA ---` com docs e
   exemplos "Prompt/Código") + código atual + instrução do usuário +
   `--- PRÓXIMO TRECHO DE CÓDIGO ---`.
5. Parâmetros: Gemini `temperature=0`, `max_output_tokens=256`; GPT
   `temperature=0`, `max_tokens=256`; locais GPT4All `temp=0.1`,
   `max_tokens=256`. Retorno `text/plain` com `.strip()` (alguns fazem
   `.replace("`","").replace("égua","")`).
6. `sendDataCallback` → `addCodeToBox` (`js/translate-models.js:202`) insere no
   editor e fala feedback via `feedbackAudio`.

### 3.2 Fluxo 2 — Construtor guiado: JSON estruturado → código

1. Botões chamam `criarVariavel` (`js/constructor.js:405`), `operacao` (`:559`),
   `condicional` (`:703`) e `escrever` (`:501`).
2. `perguntarComVoz` (`:249`) fala a pergunta, grava 5 s, transcreve e corrige a
   resposta por Levenshtein contra um vocabulário fechado (`:385`).
3. Monta um JSON por ação e chama `enviarParaServidor` (`:747`) nas portas
   7000–7400 (construtores Flask):
   - `{"acao":"criarVariavel","tipo":"numérica","nome":"idade","valor":"25"}`
   - `{"acao":"criarVariavel","tipo":"vetor de numérica","nome":"notas","quantidade":3,"valores":[...]}`
   - `{"acao":"operacao","tipo":"matemática","expressao":"a + b","guardarEm":"soma"}`
   - `{"acao":"condicional","se":{"condicao":"...","acoes":[...]},"senao":{"acoes":[...]}}`
   - `{"acao":"escrever","tipo":"texto","conteudo":"..."}`
4. **System prompt idêntico nos 5 construtores** (Gemini, GPT, phi2, llama,
   qwen2): "Você é um expert na linguagem Égua e sua única tarefa é traduzir um
   objeto JSON para o código correspondente" + as mesmas regras do gerador. O
   JSON inteiro é serializado no prompt; o few-shot vem exclusivamente do RAG
   híbrido (`# JSON de Entrada` / `# Código Égua de Saída`). Parâmetros:
   temp 0 (cloud) / 0.1 (locais), max 256–300 tokens, síncrono, `text/plain`.
5. Números por extenso usam um desvio **não-LLM**: `textoParaNumero`
   (`js/constructor.js:42`) → `servers/translate_number.py:5050`
   (`GoogleTranslator` pt→en) → biblioteca `words-to-numbers` no cliente.

### 3.3 Fluxo 3 — Executar → explicar (RAG sobre a execução)

1. `runCode` (`js/explain-code.js:83`) instancia `Egua.Egua`, roda
   Lexer/Parser/`runBlock`; `console.log` é sobrescrito e capturado em `#output`
   (`js/index.js:143`).
2. `sendDataToExplain` (`:167`) envia **POST JSON**
   `{codigo, tokens, ast, output}` para 5000–5400.
3. Prompt pedagógico: "Se a execução foi bem-sucedida, confirme e parabenize; se
   houve erro, explique em qual linha ocorreu, descreva o problema e sugira uma
   correção" + RAG com o dataset `{codigo, tokens, ast, interpretador}` e docs,
   e o fecho `--- DADOS DO USUÁRIO ---` + `--- FEEDBACK PEDAGÓGICO ---`. O
   Gemini força 1 exemplo + 1 doc além do top-k. Parâmetros: temp 0.2,
   400–500 tokens, `text/plain` (markdown).
4. A resposta volta em markdown; `processarRespostaCompleta`
   (`js/explain-code.js:3`) separa texto de blocos de código, converte `{`/`}`
   em "abre chaves"/"fecha chaves" e fala via `feedbackAudio`
   (`js/assist.js:25`).

### 3.4 Fluxo 4 — Acessibilidade (TTS, atalhos, menus)

- Voz via Web Speech API, com seleção em `#seletor-voz` e sliders de velocidade
  e tom (`js/assist.js:25-52`).
- Leitura por caractere/palavra/linha, menu audível, ajuda falada e atalhos
  globais (`js/translate-models.js:649-871`).
- Estado do editor em `sessionStorage` (`codigoEditorEgua`); limpo no
  `beforeunload` (`index.html:588`).

---

## 4. Contratos com LLM (consolidado)

| Etapa | Entrada | Prompt | RAG (dataset) | Modelos / parâmetros | Saída |
|---|---|---|---|---|---|
| Transcrição | áudio (multipart, campo `audio`) | Gemini: "transcreva com precisão; números por extenso; sem comentários" | — | whisper-1 / whisper-turbo / gemini-2.0-flash | texto puro ou `{"transcricao"}` |
| Geração de código | `{prompt, codigo_atual}` | 1 prompt achatado (Gemini) ou system+user (GPT) | `RAG_exemplos_codigo.jsonl` + `docs.txt`, k=5 | gemini-2.0-flash / gpt-4o-mini / gpt4all / seq2seq | `text/plain` (código) |
| Explicação | `{codigo, tokens, ast, output}` | system pedagógico + dados do usuário | `RAG_token_parser_interpreter_examples.jsonl` + docs, k=3 | mesmos, temp 0.2 | `text/plain` (markdown) |
| Construtor JSON→código | JSON por ação | system "traduza o JSON" + JSON no user | `RAG_exemplos_hibrido.jsonl` + docs, k=3–5 | mesmos, temp 0–0.1 | `text/plain` (código) |
| Extenso→número | `{texto}` | **não usa LLM** (GoogleTranslator + heurística JS) | — | — | `{"translated_en"}` |

### 4.1 Transcrição — detalhes dos provedores

- **PHP (`transcribe.php`):** `POST` multipart, campo `audio`; usa
  `OPENAI_CURL` e `OPENAI_API_KEY` do `.env`; envia `whisper-1`; devolve texto
  puro (`$result['text']`).
- **Whisper local (`servers/transcription/whisper-local.py`):** FastAPI :3000,
  `openai-whisper` com modelo `turbo`, `language="pt"`; devolve
  `{"transcricao": ...}`.
- **Gemini Speech (`servers/transcription/gemini/gemini-transcribe.js`):**
  Express :2000, `gemini-2.0-flash`, áudio inline base64; prompt literal:
  > "Por favor, transcreva o seguinte áudio com precisão. Se no áudio existirem
  > valores numéricos, escreva-os por extenso. Retorne apenas o áudio
  > transcrito, sem comentários, pontuações nem nada."

### 4.2 Geração — prompt (literais)

System/regras (idêntico em todos os geradores):

```
Você é um assistente de programação especialista na linguagem 'Égua'.
Sua tarefa é completar o código do usuário com base no prompt dele e no contexto do que já foi escrito.
Responda APENAS com o próximo trecho de código Égua. Não adicione explicações, comentários ou qualquer texto extra.

### REGRAS GERAIS ###
1. Normalização de Nomes: sem acentos, cedilha, espaços → underscores...
2. Strings: sempre entre aspas duplas.
3. Saída Limpa: apenas o código Égua.
4. Números por extenso: transforme em valores numéricos.
5. Baseie-se Fortemente nos Exemplos recuperados.
6. Entradas inválidas: NÃO RETORNE NADA.
```

Mensagem de usuário (GPT / locais; Gemini achatava tudo em um único prompt):

```
--- SITUAÇÃO ATUAL DO USUÁRIO ---
Código no editor:
```egu
{codigo_atual}
```

Instrução do usuário: '{prompt}'

--- PRÓXIMO TRECHO DE CÓDIGO ---
```

### 4.3 Explicação — prompt

```
Você é um assistente pedagógico para a linguagem de programação 'Égua'.
O usuário executou o seguinte código e obteve um output do console, junto com os tokens e a AST.
Sua tarefa:
- Se a execução foi bem-sucedida, confirme se a saída faz sentido e parabenize o usuário.
- Se houve erro, explique em qual linha ocorreu, descreva o problema e sugira uma correção
  com base no código, tokens, AST e a saída do console.
Responda de forma clara, objetiva e amigável.
```

### 4.4 Construtor — prompt

```
Você é um expert na linguagem de programação "Égua" e sua única tarefa é traduzir
um objeto JSON para o código Égua correspondente.

### REGRAS GERAIS ### (mesmas 5 regras + normalização)
```

Prompt final: `SYSTEM_PROMPT` + RAG + "Agora, com base nas regras e nos exemplos
acima, traduza o seguinte JSON para código Égua:" + `json.dumps(json_data)`.

---

## 5. RAG

Datasets (versionados em `rag/`):

| Arquivo | Linhas | Campos | Usado por |
|---|---|---|---|
| `RAG_exemplos_codigo.jsonl` | 396 | `{prompt, codigo}` | geração de código |
| `RAG_exemplos_hibrido.jsonl` | 389 | `{json_input, codigo_gerado}` | construtor (191 `criarVariavel`, 112 `condicional`, 51 `escrever`, 35 `operacao`) |
| `RAG_token_parser_interpreter_examples.jsonl` | 50 | `{id, codigo, tokens, ast, interpretador}` | explicação |
| `docs.txt` | 242 | documentação da linguagem, chunks por `\n\n` (73 chunks) | todas as tarefas |

No legado, **cada servidor** tinha seu próprio embedder e índice FAISS em
`faiss_indexes/<modelo>_<tarefa>/`:

- Gemini: `embedding-001` (768d), `IndexFlatIP` normalizado;
- OpenAI: `text-embedding-3-small` (1536d), `IndexFlatL2` sem normalização;
- locais: `all-MiniLM-L6-v2` (384d), `IndexFlatIP` normalizado;
- top-k 5 (geração), 3 (explicação/construtor); sem threshold de score.

Observações: os índices não são versionados e são reconstruídos no primeiro
boot; `docs.txt` aparenta estar em Latin-1/CP1252 e é lido como UTF-8.

No estado atual (`3d4549f`), o RAG é unificado em `servers/core/rag.py`: um único
`SentenceTransformer("all-MiniLM-L6-v2")` e três índices `unified_generator`,
`unified_explainer`, `unified_constructor`, reconstruídos automaticamente quando
os fontes são mais novos que o índice (staleness por mtime).

---

## 6. Estado atual (`rewrite/servidor-unico`, commit `3d4549f`)

- Um único processo FastAPI na porta 3000 (`app.py` → `servers/main.py`), que
  serve o frontend estático e toda a API sob `/api`.
- Preflight fail-fast (`servers/core/preflight.py`): ffmpeg, Ollama + modelos,
  Whisper e RAG validados antes de abrir a porta; provedores cloud sem chave
  ficam apenas "desativados".
- `servers/providers/` normaliza o acesso a LLMs com a assinatura
  `chat(provedor, sistema, usuario, modelo, max_tokens, temperature, top_p)`:
  - `ollama.py` → Ollama via SDK OpenAI (`http://localhost:11434/v1`);
  - `openai_provider.py` → `gpt-4o-mini` (chat + `whisper-1`);
  - `gemini_provider.py` → `gemini-2.0-flash-latest` (chat + transcrição).
- Prompts centralizados por caso de uso: `SISTEMA_GERAR` (`servers/api/gerar.py:15`),
  `SISTEMA_CONSTRUIR` (`servers/api/construir.py`), `SISTEMA_EXPLICAR`
  (`servers/api/explicar.py`). O RAG é concatenado ao system prompt e a mensagem
  de usuário é montada separadamente.
- Endpoints: `/api/transcrever`, `/api/gerar-codigo`, `/api/explicar`,
  `/api/construir`, `/api/converter-extenso`, `/api/modelos`, `/api/health`,
  `/api/logs`, `/api/log/cliente`. Erros sempre JSON `{erro, detalhes}`.
- Transcrição unificada em `POST /api/transcrever` (campo `model`), com
  dispatch em `servers/providers/__init__.py:70`; Whisper local migrado de
  `openai-whisper` para `faster-whisper` (`servers/core/whisper.py`).
- Frontend reescrito em módulos ES (`frontend/js/`): `api.js` (cliente HTTP
  central), `store.js`, `generator.js`, `explainer.js`, `constructors.js`,
  `transcription.js`, `tts.js`, `menu.js`, `keyboard.js`, `dialogo.js`, etc.
- Logging completo com request-id (`servers/core/logging_setup.py`), middleware
  de request, logs rotativos e endpoint para logs do cliente.
- Testes smoke (`tests/test_api.py`): 14 testes com `fastapi.testclient`,
  preflight fake — não dependem de Whisper/Ollama.

O que **ainda não** mudou em relação ao legado: sem streaming, sem structured
output, sem validação do código gerado (o Lexer/Parser Égua fica só no
navegador), RAG sem reranking/threshold, sem timeouts/retries/cancelamento.

---

## 7. Dívidas técnicas e inconsistências (a resolver na reescrita)

1. Contratos heterogêneos entre os 4 transcritores (JSON vs texto; 200 vs 201);
   o front legado não parseia de forma uniforme.
2. Prompts duplicados em ~17 arquivos no legado; Gemini achatava system+user.
3. Pós-processamento frágil: `.replace("`","").replace("égua","")` pode
   corromper código; nenhuma validação sintática antes de exibir/falar.
4. Erros retornados como código (`// Erro ao gerar código`) misturados ao fluxo
   normal.
5. RAG sem score/threshold, top-k fixo, embeddings/índices fragmentados e não
   versionados; `docs.txt` com encoding suspeito.
6. Zero streaming/retry/timeout/cancelamento — crítico para UX por voz.
7. Chaves/caminhos hardcoded, `debug=True`, `print` como log (parcialmente
   resolvido na rewrite).
8. Estado do editor em `sessionStorage`; parsing de markdown e TTS no cliente;
   caminhos de áudio quebrados (`js/constructor.js:267` usava `../audio/`).
9. Sem separação entre "texto para exibição" e "texto para áudio" no backend.
10. Sem avaliação/regressão dos prompts (só evidência anedótica).

---

## 8. Implicações para a reescrita com stack moderna

- **Gateway único com contratos tipados** (OpenAPI + pydantic/zod; ou tRPC se o
  front for TS), providers como adapters, um contrato só para transcrição,
  geração, explicação e construção.
- **Streaming de ponta a ponta**: SSE/WebSocket para tokens e TTS incremental
  (fila de fala com cancelamento), essencial para acessibilidade.
- **Structured outputs/function calling** para o construtor (a LLM devolve JSON
  validado e o backend compila o código) e para a geração, no lugar de texto
  livre.
- **Validação do código Égua no servidor**: reutilizar Lexer/Parser para checar o
  output da LLM antes de falar/executar e usar a AST para reparo automático.
- **RAG moderno**: um índice (pgvector/Qdrant/FAISS persistido), chunks com
  metadata, reranking, threshold, cache e avaliação offline dos prompts.
- **Transcrição**: streaming com VAD (faster-whisper stream ou API realtime) e
  contrato único; fallback Web Speech.
- **Observabilidade**: OpenTelemetry, tokens/custo por request, logs
  estruturados com request-id e testes de contrato com providers mockados.
- **Config/segurança**: segredos só em `.env`/secret manager, caminhos de
  modelos relativos ao projeto, sem `debug=True`.
- **Estado**: gerenciamento de estado no front (store) e/ou backend, histórico
  de conversa por sessão, undo/redo no editor.
