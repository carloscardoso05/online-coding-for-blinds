# AGENTS.md

Égua Assist — voice-driven coding assistant for visually impaired students (IDE Égua). All UI text, comments, and docs are in **Portuguese**; write new code in Portuguese.

## How to run

There is **no single start command** and **no `app.py`** (README is stale). The app is a static frontend plus many independent localhost microservices; start only the ones matching the models selected in the UI.

1. Create `.env` at repo root (**`.env.example` does not exist** despite docs referencing it). Vars read via `python-dotenv` (`load_dotenv()`) and PHP dotenv: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_CURL` (Whisper endpoint, default `https://api.openai.com/v1/audio/transcriptions`).
2. Install deps: `uv sync` (core) or `uv sync --extra local-models` (gpt4all/torch/whisper/faiss — needed for Llama/Phi/Qwen2/Whisper/Transformer services). **Use Python 3.12**: `uv sync --python 3.12` — the default 3.14 has no wheels for `spacy`/`torch` (project says `>=3.9` but that's wrong in practice). `composer install` for PHP. `npm install` in `js/` and in `servers/transcription/gemini/`.
3. Frontend: `php -S localhost:8080` then open `http://localhost:8080`. PHP exists **only** to load `.env` for `transcribe.php` (needs `vendor/autoload.php`).
4. Backends: one Flask/FastAPI process per feature+provider, e.g. `uv run python servers/code_generation/gemini_code_generator.py`.

## Port mapping (frontend ↔ backend, in `js/*.js`)

| Port | Service |
|---|---|
| 2000 | Transcription, Gemini (`servers/transcription/gemini/gemini-transcribe.js`, **Node**) |
| 3000 | Transcription, Whisper local (`whisper-local.py`) |
| 4000/4100/4300/4400/4500/6969 | Code generation: Gemini/GPT-4o-mini/Phi-2/Llama-3/Qwen2/Transformer |
| 5000/5100/5200/5300/5400 | Code explanation: Gemini/GPT/Phi/Llama/Qwen2 |
| 7000/7100/7200/7300/7400 | Block constructor: Gemini/GPT/Phi-2/Llama/Qwen2 |
| 5050 | Number-to-words converter (`servers/translate_number.py`) |

The UI's selected models are persisted in `localStorage` under `transcriptionModel`, `translationModel`, `assistantModel`, `constructorModel`.

## Gotchas

- **Local LLM services hardcode Linux paths**: `MODEL_PATH = "/home/victor_santiago/Documentos/.../models/*.gguf"` in all gpt4all-based servers. They fail without the `.gguf` files; fix the path for the current machine (this machine is Windows).
- **FAISS indices**: built at server startup from `rag/*.jsonl` into `rag/faiss_indexes/` (gitignored). Missing indices only warn, don't crash.
- **CORS is wide open** (`flask_cors.CORS(app)` default) — don't add CORS config.
- **No test suite** — validation is manual. `js/` has `fast-levenshtein` as its only runtime dep.
- Frontend is vanilla JS ES modules with **cross-file globals** — `no-undef` is disabled in ESLint; don't "fix" that or add module imports to existing globals.

## Lint / verify

- Python: `uv run ruff check servers/` (auto-fix: `--fix`). `ruff.toml` ignores `E501` everywhere and `F401` in `servers/**`.
- JS: from `js/`: `npm run lint` (ESLint flat config; `*.min.js` ignored, `no-unused-vars` is warn, `no-console` off).