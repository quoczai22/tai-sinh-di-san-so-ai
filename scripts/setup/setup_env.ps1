<#
.SYNOPSIS
    Cai dat moi truong cho du an bang uv (theo pyproject.toml va uv.lock).

.DESCRIPTION
    Moi thu vien (ke ca PyTorch ban CUDA cu126) da duoc ghim trong pyproject.toml va uv.lock,
    nen chi can "uv sync". Khong dung pip va khong tao moi truong ao khac: uv tao .venv o goc repo.
    Script nay: kiem tra uv, chay uv sync, tao .env tu .env.example neu chua co.

.EXAMPLE
    .\scripts\setup\setup_env.ps1
#>
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host "=== SETUP MOI TRUONG ===`n" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "Khong tim thay uv. Cai uv truoc: https://docs.astral.sh/uv/getting-started/installation/"
}
Write-Host "[OK] $(uv --version)" -ForegroundColor Green

Write-Host "`n[..] uv sync (tai khoang 3GB lan dau, gom PyTorch CUDA)..." -ForegroundColor Yellow
uv sync

$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $root ".env.example") $envFile
    Write-Host "[OK] Da tao .env tu .env.example" -ForegroundColor Green
}

Write-Host "`n=== XONG. Tiep theo: uv run python scripts/setup/check_gpu.py ===" -ForegroundColor Cyan
