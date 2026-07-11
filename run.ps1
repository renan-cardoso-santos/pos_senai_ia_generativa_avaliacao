# run.ps1 — sobe o RecrutaMe de forma reprodutível (Windows / PowerShell).
#
# Resolve as três causas comuns de falha ao demonstrar:
#   1. dependência faltando no .venv (ex.: cryptography usado pela LGPD);
#   2. ImportError por bytecode .pyc obsoleto (cache de outra versão do Python);
#   3. usuário demo / CV de exemplo ausentes.
#
# Uso:
#   .\run.ps1               # sobe o app (porta 8501)
#   .\run.ps1 -Seed         # roda o seed antes (garante demo + CV de exemplo)
#   .\run.ps1 -Port 8600    # porta alternativa

param(
    [switch]$Seed,
    [int]$Port = 8501
)

$raiz = $PSScriptRoot
$py = Join-Path $raiz ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Ambiente virtual nao encontrado em .venv." -ForegroundColor Red
    Write-Host "Crie com:  python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# 1) Sincroniza o ambiente com o pyproject.toml/uv.lock (instala o que faltar).
Write-Host "-> Sincronizando dependencias (uv sync)..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv sync
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   (aviso) 'uv sync' falhou; seguindo (deps podem ja existir)." -ForegroundColor Yellow
    }
} else {
    Write-Host "   (aviso) 'uv' nao encontrado no PATH; pulei a sincronizacao de dependencias." -ForegroundColor Yellow
}

# 2) Limpa bytecode obsoleto (evita ImportError por .pyc de outra versao do Python).
Write-Host "-> Limpando __pycache__ do projeto..." -ForegroundColor Cyan
Get-ChildItem -Path $raiz -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\\.venv\\" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 3) Seed opcional — usuario demo + CV padronizado de exemplo (idempotente).
if ($Seed) {
    Write-Host "-> Rodando seed (dados de demonstracao)..." -ForegroundColor Cyan
    & $py -m app.seed
}

# 4) Sobe o app.
Write-Host "-> Iniciando RecrutaMe em http://localhost:$Port" -ForegroundColor Green
Write-Host "   Login demo ja pre-preenchido: demo@recrutame.dev / demo1234" -ForegroundColor DarkGray
& $py -m streamlit run (Join-Path $raiz "app\main.py") --server.port $Port
