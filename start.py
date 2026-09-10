#!/usr/bin/env python3
# start.py — sobe tudo localmente (sem APIs) com um único comando:
# Ollama (se necessário) -> servidor unificado (Whisper + RAG + Ollama) -> frontend PHP.
# Uso: python3 start.py
# Versão multiplataforma do antigo start.ps1 (Windows/PowerShell).

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
OLLAMA_URL = "http://localhost:11434"
PORTA_SERVIDOR = 3000
PORTA_FRONTEND = 8080
MODELO_PADRAO = "llama3.2"
TIMEOUT_OLLAMA = 30
TIMEOUT_SERVIDOR = 180
LOG_SERVIDOR = RAIZ / "servers" / "local_assistant.log"


def _habilitar_ansi_windows():
    if os.name == "nt":
        os.system("")  # habilita códigos ANSI no console do Windows 10+


_habilitar_ansi_windows()
_SEM_COR = not sys.stdout.isatty()
VERDE = "" if _SEM_COR else "\033[32m"
CIANO = "" if _SEM_COR else "\033[36m"
AMARELO = "" if _SEM_COR else "\033[33m"
VERMELHO = "" if _SEM_COR else "\033[31m"
RESET = "" if _SEM_COR else "\033[0m"


def info(msg):
    print(f"{CIANO}{msg}{RESET}")


def ok(msg):
    print(f"{VERDE}{msg}{RESET}")


def aviso(msg):
    print(f"{AMARELO}{msg}{RESET}", file=sys.stderr)


def erro(msg):
    print(f"{VERMELHO}{msg}{RESET}", file=sys.stderr)


def atualizar_path_windows():
    """Relê o PATH do registro para achar ffmpeg/ollama recém-instalados (como no start.ps1)."""
    if os.name != "nt":
        return
    import winreg

    caminhos = []
    chaves = [
        (winreg.HKEY_CURRENT_USER, "Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]
    for raiz, subchave in chaves:
        try:
            with winreg.OpenKey(raiz, subchave) as chave:
                valor, _ = winreg.QueryValueEx(chave, "Path")
                if valor:
                    caminhos.append(os.path.expandvars(valor))
        except OSError:
            pass
    if caminhos:
        os.environ["Path"] = ";".join(caminhos + [os.environ.get("Path", "")])


def porta_aberta(porta):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def ollama_responde():
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=2):
            return True
    except (urllib.error.URLError, OSError):
        return False


def modelos_ollama():
    try:
        resultado = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if resultado.returncode != 0:
        return None
    linhas = resultado.stdout.strip().splitlines()
    return [linha.split()[0] for linha in linhas[1:] if linha.split()]


def iniciar_em_segundo_plano(comando, cwd=None, stdout=None, stderr=None):
    kwargs = {
        "cwd": cwd,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL if stdout is None else stdout,
        "stderr": subprocess.DEVNULL if stderr is None else stderr,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(comando, **kwargs)


def ultimas_linhas(caminho, n=20):
    try:
        linhas = caminho.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(linhas[-n:])


def main():
    atualizar_path_windows()

    # 1. Ollama
    if not ollama_responde():
        if shutil.which("ollama") is None:
            erro("Ollama não encontrado no PATH. Instale em https://ollama.com/download e rode de novo.")
            return 1
        info("Iniciando Ollama...")
        iniciar_em_segundo_plano(["ollama", "serve"])
        for _ in range(TIMEOUT_OLLAMA):
            if ollama_responde():
                break
            time.sleep(1)
        if not ollama_responde():
            aviso("Ollama não respondeu. Verifique se ele está instalado.")
    else:
        ok("Ollama já está rodando.")

    # 2. Modelos (baixa um padrão no primeiro uso)
    modelos = modelos_ollama()
    if not modelos:
        aviso(f"Nenhum modelo instalado. Baixando {MODELO_PADRAO} (primeiro uso, ~2 GB)...")
        try:
            subprocess.run(["ollama", "pull", MODELO_PADRAO])
        except FileNotFoundError:
            aviso("Comando 'ollama' indisponível; baixe um modelo manualmente com 'ollama pull <modelo>'.")
    else:
        ok("Modelos Ollama disponíveis:")
        for nome in modelos[:10]:
            print(f"  - {nome}")

    # 3. Servidor unificado (porta 3000)
    if porta_aberta(PORTA_SERVIDOR):
        ok("Servidor unificado já está rodando na porta 3000.")
    else:
        if shutil.which("uv") is None:
            erro("'uv' não encontrado no PATH. Instale em https://docs.astral.sh/uv/ e rode de novo.")
            return 1
        info("Verificando dependências locais (torch/faiss/whisper)...")
        checagem = subprocess.run(
            ["uv", "run", "--no-sync", "python", "-c", "import torch, faiss, faster_whisper, sentence_transformers"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
        )
        if checagem.returncode != 0:
            erro("Dependências locais ausentes. Rode antes:")
            print("  uv sync --extra local-models --python 3.12")
            return 1
        info("Iniciando servidor unificado (Whisper + RAG + Ollama)...")
        with open(LOG_SERVIDOR, "ab") as log:
            processo = iniciar_em_segundo_plano(
                ["uv", "run", "--no-sync", "python", "servers/local_assistant.py"],
                cwd=RAIZ,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        for _ in range(TIMEOUT_SERVIDOR):
            if porta_aberta(PORTA_SERVIDOR):
                break
            if processo.poll() is not None:
                erro("O servidor unificado encerrou logo após iniciar. Últimas linhas do log:")
                print(ultimas_linhas(LOG_SERVIDOR))
                return 1
            time.sleep(1)
        if not porta_aberta(PORTA_SERVIDOR):
            erro("Servidor unificado não subiu em 3 minutos (primeira execução baixa o Whisper).")
            erro(f"Tente rodar manualmente: uv run --no-sync python servers/local_assistant.py (log: {LOG_SERVIDOR})")
            return 1
        ok("Servidor unificado no ar (porta 3000).")

    # 4. Frontend
    if shutil.which("php") is None:
        erro("PHP não encontrado no PATH. Instale PHP para servir o frontend.")
        return 1
    info(f"Abrindo http://localhost:{PORTA_FRONTEND} ...")
    webbrowser.open(f"http://localhost:{PORTA_FRONTEND}")
    try:
        subprocess.run(["php", "-S", f"localhost:{PORTA_FRONTEND}"], cwd=RAIZ)
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
