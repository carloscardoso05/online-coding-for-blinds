# Servidor unificado 100% local — Whisper (transcrição) + RAG (faiss) + Ollama (LLM) + números por extenso.
# Substitui os servidores antigos: whisper-local (3000), code_generation/explication/constructor (gpt4all) e translate_number (5050).
# Uso: uv run python servers/local_assistant.py

import json
import os
import re
import subprocess
import tempfile

import faiss
import numpy as np
import uvicorn
from fastapi import Body, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from faster_whisper import WhisperModel
from openai import OpenAI
from sentence_transformers import SentenceTransformer

# --- Configurações ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
MODELO_PADRAO = os.getenv("OLLAMA_MODEL", "llama3.2")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "turbo")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAG_DIR = os.path.join(RAIZ, "rag")
FAISS_DIR = os.path.join(RAG_DIR, "faiss_indexes")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

print("Carregando modelo de embeddings SentenceTransformers...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
EMB_DIM = embedder.get_sentence_embedding_dimension()
print(f"Modelo de embeddings carregado (dimensão {EMB_DIM}).")

print(f"Carregando modelo Whisper ({WHISPER_MODEL})...")
whisper_model = WhisperModel(WHISPER_MODEL, device="auto", compute_type="auto")
print("Modelo Whisper carregado.")


# --- Helpers RAG ---

def normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


def gerar_embedding(texto: str) -> np.ndarray:
    try:
        embedding = embedder.encode([texto])[0]
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}")
        return np.zeros(EMB_DIM, dtype=np.float32)


def carregar_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        print(f"Aviso: Arquivo de exemplos {path} não encontrado.")
        return []
    exemplos = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                exemplos.append(json.loads(line))
            except Exception as e:
                print(f"Erro ao ler linha JSONL: {e}")
    return exemplos


def carregar_docs(path: str) -> list[str]:
    if not os.path.exists(path):
        print(f"Aviso: Arquivo de documentação {path} não encontrado.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [p.strip() for p in f.read().split("\n\n") if p.strip()]


class IndiceRAG:
    """Índice FAISS com persistência em rag/faiss_indexes/<nome>."""

    def __init__(self, nome: str, jsonl_path: str, texto_exemplo, k_padrao: int):
        self.nome = nome
        self.jsonl_path = jsonl_path
        self.texto_exemplo = texto_exemplo
        self.k_padrao = k_padrao
        self.index, self.metadados = self._construir_ou_carregar()

    def _caminhos(self):
        base = os.path.join(FAISS_DIR, self.nome)
        return os.path.join(base, "index.faiss"), os.path.join(base, "metadados.json")

    def _construir_ou_carregar(self):
        index_path, meta_path = self._caminhos()
        if os.path.exists(index_path) and os.path.exists(meta_path):
            print(f"Carregando índice FAISS existente ({self.nome})...")
            index = faiss.read_index(index_path)
            with open(meta_path, "r", encoding="utf-8") as f:
                metadados = json.load(f)
            return index, metadados

        print(f"Construindo novo índice FAISS ({self.nome})...")
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        index = faiss.IndexFlatIP(EMB_DIM)
        metadados = []

        exemplos_jsonl = carregar_jsonl(self.jsonl_path)
        print(f"Gerando embeddings para {len(exemplos_jsonl)} exemplos ({self.nome})...")
        for ex in exemplos_jsonl:
            emb = normalize(gerar_embedding(self.texto_exemplo(ex)))
            index.add(np.array([emb]))
            metadados.append({"tipo": "jsonl", **ex})

        docs_chunks = carregar_docs(os.path.join(RAG_DIR, "docs.txt"))
        print(f"Gerando embeddings para {len(docs_chunks)} trechos da documentação ({self.nome})...")
        for i, chunk in enumerate(docs_chunks):
            emb = normalize(gerar_embedding(chunk))
            index.add(np.array([emb]))
            metadados.append({"tipo": "doc", "id": f"doc_{i}", "texto": chunk})

        faiss.write_index(index, index_path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadados, f, ensure_ascii=False, indent=2)

        print(f"Índice {self.nome} criado com {index.ntotal} vetores.")
        return index, metadados

    def buscar(self, texto_busca: str, k: int | None = None) -> list[dict]:
        k = k or self.k_padrao
        if self.index.ntotal == 0:
            return []
        emb_user = normalize(gerar_embedding(texto_busca))
        k_valido = min(k, self.index.ntotal)
        _, indices = self.index.search(np.array([emb_user]), k=k_valido)
        return [self.metadados[i] for i in indices[0]]


# --- Pipelines RAG (mesmos arquivos e prompts dos servidores gpt4all) ---

indice_gerador = IndiceRAG(
    "unified_generator",
    os.path.join(RAG_DIR, "RAG_exemplos_codigo.jsonl"),
    lambda ex: f"Prompt do usuário: {ex.get('prompt', '')}\nCódigo Égua resultante: {ex.get('codigo', '')}",
    k_padrao=5,
)

indice_explicador = IndiceRAG(
    "unified_explainer",
    os.path.join(RAG_DIR, "RAG_token_parser_interpreter_examples.jsonl"),
    lambda ex: (
        f"Código:\n{ex.get('codigo', '')}\n\n"
        f"Tokens:\n{ex.get('tokens', '')}\n\n"
        f"AST:\n{ex.get('ast', '')}\n\n"
        f"Saída/Erro do Interpretador:\n{ex.get('interpretador', '')}"
    ),
    k_padrao=3,
)

indice_construtor = IndiceRAG(
    "unified_constructor",
    os.path.join(RAG_DIR, "RAG_exemplos_hibrido.jsonl"),
    lambda ex: json.dumps(ex.get("json_input", {}), ensure_ascii=False),
    k_padrao=3,
)


# --- Chamada ao Ollama ---

def chamar_ollama(system: str, user: str, max_tokens: int, temperature: float, top_p: float, model: str | None = None) -> str:
    modelo = (model or MODELO_PADRAO).strip()
    try:
        resposta = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro na chamada ao Ollama ({modelo}): {e}")
        raise RuntimeError(
            f"Falha ao chamar o modelo '{modelo}' no Ollama. "
            "Verifique se o Ollama está rodando e se o modelo foi baixado com 'ollama pull <modelo>'."
        ) from e


@app.post("/transcrever")
async def transcrever(audio: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        segmentos, _ = whisper_model.transcribe(tmp_path, language="pt")
        transcricao = " ".join(segmento.text.strip() for segmento in segmentos).strip()
        return JSONResponse({"transcricao": transcricao})
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@app.post("/gerar-codigo")
async def gerar_codigo(payload: dict = Body(...)):
    prompt = payload.get("prompt", "")
    codigo_atual = payload.get("codigo_atual", "")
    model = payload.get("model")

    if not prompt:
        return PlainTextResponse("Erro: 'prompt' é obrigatório.", status_code=400)

    texto_busca = f"Contexto do Código Atual:\n{codigo_atual}\n\nPrompt do Usuário:\n{prompt}"
    similares = indice_gerador.buscar(texto_busca)

    contexto = (
        "Você é um assistente de programação especialista na linguagem 'Égua'.\n"
        "Sua tarefa é completar o código do usuário com base no prompt dele e no contexto do que já foi escrito.\n"
        "Responda APENAS com o próximo trecho de código Égua. Não adicione explicações, comentários ou qualquer texto extra.\n\n"
        "### REGRAS GERAIS ###\n"
        "1.  **Normalização de Nomes:** Nomes de variáveis devem ser normalizados: sem acentos, cedilha, e com espaços substituídos por underscores (_). Não coloque underscores no início ou no fim do nome das variáveis.\n"
        "2.  **Strings:** Valores de texto devem sempre estar entre aspas duplas.\n"
        "3.  **Saída Limpa:** Sua resposta deve ser APENAS o código Égua, sem explicações ou formatação extra.\n"
        "4.  **Números por extenso:** Transforme-os em valores numéricos.\n"
        "5.  **Baseie-se Fortemente nos Exemplos:** Use os exemplos recuperados abaixo como sua principal fonte de inspiração para a estrutura e sintaxe do código.\n"
        "6.  **Entradas inválidas:** Se a solicitação do usuário não fizer o menor sentido (no caso de geração de código), NÃO RETORNE NADA. Use esta condição para prevenção de erros.\n"
        "--- INFORMAÇÕES DE REFERÊNCIA RECUPERADAS ---"
    )
    for item in similares:
        if item["tipo"] == "jsonl":
            contexto += f"\n### Exemplo Similar ###\nPrompt: {item.get('prompt', '')}\nCódigo: {item.get('codigo', '')}\n---\n"
        elif item["tipo"] == "doc":
            contexto += f"\n### Documentação Relevante ###\n{item['texto']}\n---\n"

    user = (
        "\n--- SITUAÇÃO ATUAL DO USUÁRIO ---\n"
        f"Código no editor:\n```egu\n{codigo_atual}\n```\n\n"
        f"Instrução do usuário: '{prompt}'\n\n"
        "--- PRÓXIMO TRECHO DE CÓDIGO ---"
    )

    try:
        codigo_gerado = chamar_ollama(contexto, user, max_tokens=256, temperature=0.1, top_p=0.9, model=model)
        return PlainTextResponse(codigo_gerado)
    except RuntimeError as e:
        return PlainTextResponse(str(e), status_code=503)


@app.post("/explicar")
async def explicar(payload: dict = Body(...)):
    codigo_usuario = payload.get("codigo", "")
    tokens_usuario = payload.get("tokens", "")
    ast_usuario = payload.get("ast", "")
    console_output = payload.get("output", "")
    model = payload.get("model")

    texto_busca_usuario = (
        f"Código:\n{codigo_usuario}\n\n"
        f"Tokens:\n{tokens_usuario}\n\n"
        f"AST:\n{ast_usuario}\n\n"
        f"Saída/Erro do Interpretador:\n{console_output}"
    )
    similares = indice_explicador.buscar(texto_busca_usuario)

    contexto = (
        "Você é um assistente pedagógico para a linguagem de programação 'Égua'.\n"
        "O usuário executou o seguinte código e obteve um output do console, junto com os tokens e a AST.\n"
        "Sua tarefa:\n"
        "- Se a execução foi bem-sucedida, confirme se a saída faz sentido e parabenize o usuário.\n"
        "- Se houve erro, explique em qual linha ocorreu, descreva o problema e sugira uma correção com base no código, tokens, AST e a saída do console.\n"
        "Responda de forma clara, objetiva e amigável.\n\n"
        "Materiais de referência recuperados:"
    )
    for item in similares:
        if item["tipo"] == "jsonl":
            contexto += (
                f"\n### Exemplo Similar ###\n"
                f"Código: {item.get('codigo', '')}\n"
                f"Tokens: {item.get('tokens', '')}\n"
                f"AST: {item.get('ast', '')}\n"
                f"Saída/Erro: {item.get('interpretador', '')}\n---\n"
            )
        elif item["tipo"] == "doc":
            contexto += f"\n### Documentação Relevante ###\n{item['texto']}\n---\n"

    user = (
        "\n--- DADOS DO USUÁRIO ---\n"
        f"Código do usuário:\n{codigo_usuario}\n"
        f"Tokens do usuário:\n{tokens_usuario}\n"
        f"AST do usuário:\n{ast_usuario}\n"
        f"Output do console:\n{console_output}\n\n"
        "--- FEEDBACK PEDAGÓGICO ---\n"
        "Resposta:"
    )

    try:
        feedback = chamar_ollama(contexto, user, max_tokens=400, temperature=0.2, top_p=0.9, model=model)
        return PlainTextResponse(feedback)
    except RuntimeError as e:
        return PlainTextResponse(str(e), status_code=503)


@app.post("/construir")
async def construir(payload: dict = Body(...)):
    model = payload.get("model")
    if not payload.get("acao"):
        return PlainTextResponse("Erro: A chave 'acao' é obrigatória no JSON.", status_code=400)

    texto_busca = json.dumps(payload, ensure_ascii=False)
    similares = indice_construtor.buscar(texto_busca)

    system = (
        "Você é um expert na linguagem de programação \"Égua\" e sua única tarefa é traduzir um objeto JSON para o código Égua correspondente.\n"
        "### REGRAS GERAIS ###\n"
        "1.  **Normalização de Nomes:** Nomes de variáveis devem ser normalizados: sem acentos, cedilha, e com espaços substituídos por underscores (_). Não coloque underscores no início ou no fim do nome das variáveis.\n"
        "2.  **Strings:** Valores de texto devem sempre estar entre aspas duplas.\n"
        "3.  **Saída Limpa:** Sua resposta deve ser APENAS o código Égua, sem explicações ou formatação extra.\n"
        "4.  **Números por extenso:** Transforme-os em valores numéricos.\n"
        "5.  **Baseie-se Fortemente nos Exemplos:** Use os exemplos recuperados abaixo como sua principal fonte de inspiração para a estrutura e sintaxe do código.\n\n"
        "---\n"
        "### CONTEXTO E EXEMPLOS RELEVANTES (Recuperados para te ajudar) ###"
    )
    for item in similares:
        if item["tipo"] == "jsonl":
            system += f"\n# Exemplo Similar:\n# JSON de Entrada:\n# {json.dumps(item.get('json_input'))}\n# Código Égua de Saída:\n{item.get('codigo_gerado')}\n"
        elif item["tipo"] == "doc":
            system += f"\n# Documentação Relevante:\n# {item['texto']}\n"
    system += "\n---\n"

    user = (
        "Agora, traduza o seguinte JSON para código Égua:\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )

    try:
        resposta = chamar_ollama(system, user, max_tokens=300, temperature=0.1, top_p=0.9, model=model)
        codigo_limpo = resposta.strip().replace("`", "").replace("égua", "").strip()
        return PlainTextResponse(codigo_limpo)
    except RuntimeError as e:
        return PlainTextResponse(str(e), status_code=503)


@app.get("/modelos")
async def modelos():
    try:
        resultado = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        nomes = []
        linhas = resultado.stdout.strip().splitlines()
        for linha in linhas[1:]:
            partes = linha.split()
            if partes:
                nomes.append(partes[0])
        return JSONResponse({"modelos": nomes, "padrao": MODELO_PADRAO})
    except FileNotFoundError:
        return JSONResponse({"modelos": [], "padrao": MODELO_PADRAO, "erro": "Ollama não encontrado no PATH."})
    except Exception as e:
        print(f"Erro ao listar modelos do Ollama: {e}")
        return JSONResponse({"modelos": [], "padrao": MODELO_PADRAO, "erro": str(e)})


# --- Números por extenso (100% local, sem Google Translate) ---

UNIDADES = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
}

DEZENAS = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90,
}

CENTENAS = {
    "cem": 100, "cento": 100, "duzentos": 200, "trezentos": 300, "quatrocentos": 400,
    "quinhentos": 500, "seiscentos": 600, "setecentos": 700, "oitocentos": 800, "novecentos": 900,
}

MULTIPLICADORES = {"mil": 1000, "milhão": 1_000_000, "milhões": 1_000_000, "bilhão": 1_000_000_000, "bilhões": 1_000_000_000}

NUMERO_PALAVRA = {**UNIDADES, **DEZENAS, **CENTENAS, **MULTIPLICADORES}


def converter_extenso_para_digito(texto: str) -> int | None:
    """Converte 'vinte e três' -> 23. Retorna None se o texto não for um número por extenso."""
    palavras = [p for p in re.split(r"[\s,]+", texto.strip().lower()) if p]
    if not palavras:
        return None

    valores = []
    for p in palavras:
        if p in ("e", "de", "da", "do"):
            continue
        if p not in NUMERO_PALAVRA:
            return None
        valores.append(NUMERO_PALAVRA[p])

    total = 0
    atual = 0
    for v in valores:
        if v >= 1000:
            atual = max(atual, 1)
            total += atual * v
            atual = 0
        elif v == 100:
            atual = max(atual, 1) * 100
        else:
            atual += v
    total += atual
    return total


@app.post("/converter-extenso")
async def converter_extenso(payload: dict = Body(...)):
    texto_pt = payload.get("texto", "")
    if not texto_pt:
        return JSONResponse({"error": "Texto não fornecido"}, status_code=400)

    numero = converter_extenso_para_digito(texto_pt)
    if numero is None:
        return JSONResponse({"translated_en": texto_pt})
    return JSONResponse({"translated_en": str(numero)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
