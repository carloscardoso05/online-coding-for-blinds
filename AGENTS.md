# AGENTS.md

Égua Assist — voice-driven coding assistant for visually impaired students (IDE Égua). All UI text, comments, and docs are in **Portuguese**; write new code in Portuguese.

## How to run

**All-local (recommended, no API keys)**: run `python3 start.py` (any OS — legacy Windows-only `start.ps1` still works) — it starts Ollama (if needed), the unified server, and the PHP frontend. Then select **"Ollama (local)"** in the UI config for translation/assistant/constructor (transcription stays "Whisper (local)"). Any Ollama model works: `ollama pull <modelo>` and pick it in the UI — no restarts needed.

The app is a static frontend plus localhost microservices. **`app.py` does not exist** (README is stale); cloud providers (Gemini/GPT) require a manually created `.env` (`.env.example` does not exist): `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_CURL` (Whisper endpoint, default `https://api.openai.com/v1/audio/transcriptions`).

1. Install deps: `uv sync --extra local-models --python 3.12` — **`--extra local-models` needs Python 3.12**: `torchtext==0.18.0` ships wheels only through cp312, so the sync fails on 3.13+ (verified). Always pass `--extra local-models`; plain `uv sync` uninstalls gpt4all/torch/whisper (`uv run` leaves them in place). If the env is base-only, `uv run python servers/local_assistant.py` fails with `ModuleNotFoundError: torch`. `composer install` for PHP (needed only for `transcribe.php`).
2. **Unified server** (`servers/local_assistant.py`, FastAPI, port 3000) replaces whisper-local + the gpt4all triads + translate_number: transcription (**faster-whisper**, CTranslate2 — faster and lighter than the old openai-whisper), RAG+Ollama for code gen/explain/construct, local PT number-to-words (no Google Translate). Requires **ffmpeg on PATH** and **Ollama running** on 11434. Env: `OLLAMA_MODEL` (default `llama3.2`), `WHISPER_MODEL` (default `turbo`). On Linux/macOS: `uv run --extra local-models --python 3.12 python servers/local_assistant.py`.
3. Frontend: `php -S localhost:8080` then open `http://localhost:8080`. PHP exists **only** to load `.env` for `transcribe.php` (the `whisper-api` option).
4. Legacy per-provider servers (`servers/code_*/*.py`, `servers/block_constructor/*.py`, `translate_number.py`) still work but are no longer used by the UI default; each is a separate Flask process.

## Port mapping (frontend ↔ backend, in `js/*.js`)

| Port | Service |
|---|---|
| 3000 | **Unified local server** (`servers/local_assistant.py`): `/transcrever`, `/gerar-codigo`, `/explicar`, `/construir`, `/converter-extenso`, `GET /modelos` |
| 2000 | Transcription, Gemini (`servers/transcription/gemini/gemini-transcribe.js`, **Node**) |
| 4000/4100/4300/4400/4500/6969 | Code generation: Gemini/GPT-4o-mini/Phi-2/Llama-3/Qwen2/Transformer (legacy) |
| 5000/5100/5200/5300/5400 | Code explanation: Gemini/GPT/Phi/Llama/Qwen2 (legacy) |
| 7000/7100/7200/7300/7400 | Block constructor: Gemini/GPT/Phi-2/Llama/Qwen2 (legacy) |
| 5050 | Number-to-words converter (`servers/translate_number.py`, uses Google Translate — legacy) |

The UI's selected models are persisted in `localStorage` under `transcriptionModel`, `translationModel`, `assistantModel`, `constructorModel`, `ollamaModel`. The "Ollama (local)" option sends `model` (from `ollamaModel`) in the payload; the model list is fetched from `GET /modelos` when the config modal opens.

## Gotchas

- **Ollama is the LLM engine for local models** — not gpt4all anymore. The unified server calls `http://localhost:11434/v1` (OpenAI-compatible) via the `openai` lib. Errors say "Falha ao chamar o modelo ... no Ollama": check `ollama serve` and `ollama pull <modelo>`.
- **Whisper needs ffmpeg** on PATH; transcription uses `faster-whisper` (not `openai-whisper`), first run downloads the model (~1.6 GB, from HuggingFace — internet once, no key).
- **RAG/FAISS indices are cached, not auto-rebuilt**: `rag/faiss_indexes/unified_*` (gitignored) is loaded as-is when present; after editing `rag/*.jsonl` or `rag/docs.txt`, delete those dirs to rebuild. (Legacy gpt4all servers write to `../../faiss_indexes/` which resolves **outside the repo** — don't replicate that pattern.)
- **`converter-extenso` is now local** in the unified server: PT-BR number words → digits. The legacy `translate_number.py` still uses Google Translate (external API) — don't use it for offline setups.
- **CORS is wide open** (`flask_cors.CORS(app)` default / FastAPI CORSMiddleware `*`) — don't add CORS config.
- **No test suite** — validation is manual.
- Frontend is plain `<script src>` tags in `index.html` (no bundler, no `type="module"`; `js/package.json` `"type": "module"` only affects ESLint). Scripts share cross-file globals — don't add `import`/`export` or "fix" the disabled `no-undef`.
- `js/index.js` overrides `console.log`/`console.error` to render into the `#output` div. Vendored `*.min.js` (CodeFlask, `js/egua/egua.min.js` interpreter, words-to-numbers) are ESLint-ignored — don't edit them.
- **Transformer service (port 6969) is broken with current deps**: it needs `torchtext.legacy`, removed in torchtext 0.18. Ignore it.
- `DOCUMENTACAO.md` is the full user/architecture guide but predates the unified server (stale ports, e.g. 4600/5050); verify against `js/*.js` and this file.

## Lint / verify

- Python: `uv run ruff check servers/` (auto-fix: `--fix`). `ruff.toml` ignores `E501` everywhere and `F401` in `servers/**`.
- JS: from `js/`: `npm run lint` (ESLint flat config; `*.min.js` ignored, `no-unused-vars` is warn, `no-console` off).
