# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Égua Assist** is a browser extension for the Égua IDE that teaches programming logic to visually impaired students via voice recognition and LLM-powered code generation/explanation. All UI text, comments, and documentation are in **Portuguese**.

## Architecture

The app is a static HTML/JS frontend (`index.html`) that communicates with a fleet of Python Flask/FastAPI microservices running on localhost. Each LLM provider/task has its own server process.

**Frontend** — no build step; served directly (raw HTML/JS/CSS). ES modules via `js/package.json` (only dependency: `fast-levenshtein`). The selected model is persisted in `localStorage`; JS files make `fetch()` requests to the appropriate localhost port.

**Backend microservices** — each is a standalone Python file:

| Feature | Provider | Port |
|---|---|---|
| Code generation | Gemini | 4000 |
| Code generation | GPT-4o-mini | 4100 |
| Code generation | Phi-2 (local) | 4300 |
| Code generation | Llama-3 (local) | 4400 |
| Code generation | Qwen2 (local) | 4500 |
| Code generation | Transformer (local) | 6969 |
| Code explanation | Gemini | 5000 |
| Code explanation | GPT-4o-mini | 5100 |
| Code explanation | Phi (local) | 5200 |
| Code explanation | Llama-3 (local) | 5300 |
| Code explanation | Qwen2 (local) | 5400 |
| Block constructor | Gemini | 7000 |
| Block constructor | GPT-4o-mini | 7100 |
| Block constructor | Phi-2 (local) | 7200 |
| Block constructor | Llama-3 (local) | 7300 |
| Block constructor | Qwen2 (local) | 7400 |
| Transcription | Whisper (local) | 3000 |
| Number converter | deep_translator | 5050 |

## Environment Variables

Copy `.env.example` to `.env` at the repo root (loaded via `python-dotenv` in Python services, and via `vlucas/phpdotenv` in PHP).

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API (Whisper, GPT-4o-mini, embeddings) |
| `GOOGLE_API_KEY` | Google Gemini API |
| `OPENAI_CURL` | Whisper endpoint URL (default: `https://api.openai.com/v1/audio/transcriptions`) |

## Startup

There is no single start command. Start services individually as needed:

```sh
# Start a backend service (example — pick the one matching the selected model)
python servers/code_generation/gemini_code_generator.py

# Start the PHP dev server (loads .env and serves index.html)
php -S localhost:8080
```

Then open `http://localhost:8080` in a browser.

## Linting

```sh
# JS (from js/ directory)
cd js && npm run lint

# Python (from repo root)
uv run ruff check servers/
uv run ruff check servers/ --fix   # auto-fix safe issues
```

Python deps are managed with **uv** via `pyproject.toml`. Install core deps with `uv sync`; add `--extra local-models` to include Llama/Phi/Qwen2/Whisper/Transformer dependencies.

## Gotchas

- **Hardcoded local model paths**: Local LLM services (Llama, Phi, Qwen2) contain absolute paths like `/home/victor_santiago/...` that must be updated for the current machine. Search for `gpt4all.GPT4All(` calls to find them.
- **FAISS indices**: Built at server startup from the JSONL files in `rag/`. The generated index files land in `rag/faiss_indexes/` (gitignored) and can be large. Missing indices trigger a warning but don't crash the server.
- **Local models require .gguf files**: Llama/Phi/Qwen2 services load multi-GB model files locally; they will fail without them.
- **No tests**: There is no test suite. Validation is manual.
- **PHP is only for dotenv**: The PHP server exists solely to load `.env` via Composer's `phpdotenv`. If you're not using PHP, you need another way to serve `index.html` with env vars available to `transcribe.php`.
- **CORS is open**: All Python services use `flask_cors.CORS(app)` with default settings (allow all origins).
