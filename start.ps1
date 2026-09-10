# start.ps1 — sobe tudo localmente (sem APIs) com um único comando:
# Ollama (se necessário) -> servidor unificado (Whisper + RAG + Ollama) -> frontend PHP.
# Uso: .\start.ps1

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot

# Garante que ffmpeg/ollama recém-instalados sejam encontrados
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")

function Test-Ollama {
    try {
        Invoke-WebRequest -Uri "http://localhost:11434" -TimeoutSec 2 -UseBasicParsing | Out-Null
        return $true
    } catch {
        return $false
    }
}

# 1. Ollama
if (-not (Test-Ollama)) {
    Write-Host "Iniciando Ollama..." -ForegroundColor Cyan
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    $tentativas = 0
    while (-not (Test-Ollama) -and $tentativas -lt 30) {
        Start-Sleep -Seconds 1
        $tentativas++
    }
    if (-not (Test-Ollama)) {
        Write-Warning "Ollama não respondeu. Verifique se ele está instalado."
    }
} else {
    Write-Host "Ollama já está rodando." -ForegroundColor Green
}

# 2. Modelos (baixa um padrão no primeiro uso)
$saida = & ollama list 2>$null
if ($LASTEXITCODE -ne 0 -or @($saida | Select-Object -Skip 1).Count -eq 0) {
    Write-Host "Nenhum modelo instalado. Baixando llama3.2 (primeiro uso, ~2 GB)..." -ForegroundColor Yellow
    ollama pull llama3.2
} else {
    Write-Host "Modelos Ollama disponíveis:" -ForegroundColor Green
    $saida | Select-Object -First 10
}

# 3. Servidor unificado (porta 3000)
if (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Servidor unificado já está rodando na porta 3000." -ForegroundColor Green
} else {
    Write-Host "Iniciando servidor unificado (Whisper + RAG + Ollama)..." -ForegroundColor Cyan
    Start-Process -FilePath "uv" -ArgumentList "run", "python", "servers/local_assistant.py" -WorkingDirectory $raiz -WindowStyle Hidden
    $tentativas = 0
    while (-not (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue) -and $tentativas -lt 180) {
        Start-Sleep -Seconds 1
        $tentativas++
    }
    if (-not (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue)) {
        Write-Error "Servidor unificado não subiu em 3 minutos (primeira execução baixa o Whisper). Tente rodar manualmente: uv run python servers/local_assistant.py"
        exit 1
    }
    Write-Host "Servidor unificado no ar (porta 3000)." -ForegroundColor Green
}

# 4. Frontend
Write-Host "Abrindo http://localhost:8080 ..." -ForegroundColor Cyan
Start-Process "http://localhost:8080"
Set-Location $raiz
php -S localhost:8080