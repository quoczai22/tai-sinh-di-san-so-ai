<#
.SYNOPSIS
    Cai dat moi truong AI local cho du an (PyTorch CUDA + diffusers).

.DESCRIPTION
    Script chi lam mot viec ma pip khong tu lam duoc: chon dung kenh CUDA
    va cai torch tu index rieng cua PyTorch.

    Ly do phai co: "pip install torch" tren Windows keo ve ban CPU-only.
    Cai xong khong bao loi gi ca, den luc chay moi phat hien
    torch.cuda.is_available() = False. Phai dung --index-url tro toi
    download.pytorch.org/whl/<kenh> moi lay duoc ban CUDA.

    Script KHONG dong vao duong dan nao tren may ban. pip va HuggingFace
    dung thu muc cache mac dinh cua he dieu hanh:
        pip -> %LOCALAPPDATA%\pip\Cache
        HF  -> %USERPROFILE%\.cache\huggingface

.PARAMETER CudaChannel
    Kenh wheel PyTorch. Mac dinh "auto" = doc nvidia-smi roi tu chon.
    Ghi de bang: cu118 | cu126 | cu128 | cpu

.PARAMETER TorchVersion
    Phien ban torch can pin. Truyen chuoi rong de lay ban moi nhat cua kenh.

.EXAMPLE
    .\scripts\01_setup_env.ps1
    Cai binh thuong, tu phat hien GPU.

.EXAMPLE
    .\scripts\01_setup_env.ps1 -CudaChannel cu128
    Ep dung kenh cu128 (RTX 50xx / Blackwell).
#>
param(
    [ValidateSet("auto", "cu118", "cu126", "cu128", "cpu")]
    [string]$CudaChannel = "auto",

    [string]$TorchVersion = "2.13.0"
)

$ErrorActionPreference = "Stop"

Write-Host "=== SETUP MOI TRUONG AI LOCAL ===`n" -ForegroundColor Cyan


# Buoc 1: kich hoat venv

$venv = Join-Path $PSScriptRoot "..\venv\Scripts\Activate.ps1"
if (-not (Test-Path $venv)) {
    throw "Khong tim thay venv. Chay truoc: python -m venv venv"
}
& $venv
Write-Host "[OK] venv da kich hoat: $(python --version)" -ForegroundColor Green


# Buoc 2: nang cap pip

python -m pip install --upgrade pip setuptools wheel


# Buoc 3: PyTorch
# KHONG dung "pip install torch" thuong - se keo ve ban CPU-only.
# Phai lay tu index CUDA rieng cua PyTorch.

if ($CudaChannel -eq "auto") {
    if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
        $CudaChannel = "cpu"
        Write-Host "[!] Khong thay nvidia-smi -> khong co GPU NVIDIA. Dung ban CPU." -ForegroundColor Yellow
        Write-Host "    SD1.5 tren CPU cham hon 20-50 lan, chi du de kiem tra code chay." -ForegroundColor Yellow
    }
    else {
        # "CUDA Version: X.Y" trong nvidia-smi = ban CAO NHAT driver ho tro
        $out = (& nvidia-smi 2>$null | Out-String)
        $ver = if ($out -match "CUDA Version:\s*(\d+)\.(\d+)") { [double]"$($Matches[1]).$($Matches[2])" } else { 0 }
        $gpu = if ($out -match "(RTX\s*\d{4}|GTX\s*\d{3,4})") { $Matches[1] } else { "?" }

        # RTX 50xx (Blackwell, sm_120) KHONG chay duoc wheel cu126 -> bat buoc cu128
        if     ($gpu -match "RTX\s*5\d{3}") { $CudaChannel = "cu128" }
        elseif ($ver -ge 12.6)              { $CudaChannel = "cu126" }
        elseif ($ver -ge 11.8)              { $CudaChannel = "cu118" }
        else {
            Write-Host "[!] Driver qua cu (CUDA $ver). Nen cap nhat driver NVIDIA truoc." -ForegroundColor Red
            $CudaChannel = "cu118"
        }
        Write-Host "[i] GPU $gpu | driver ho tro CUDA $ver -> chon kenh $CudaChannel" -ForegroundColor Gray
    }
}

$indexUrl = "https://download.pytorch.org/whl/$CudaChannel"

if ([string]::IsNullOrWhiteSpace($TorchVersion)) {
    Write-Host "`n[..] Cai PyTorch ban MOI NHAT tu kenh $CudaChannel..." -ForegroundColor Yellow
    Write-Host "    Khong pin phien ban - moi truong co the khac dong doi." -ForegroundColor DarkYellow
    python -m pip install torch torchvision --index-url $indexUrl
}
else {
    Write-Host "`n[..] Cai PyTorch $TorchVersion tu kenh $CudaChannel (~2.5GB)..." -ForegroundColor Yellow
    python -m pip install "torch==$TorchVersion" --index-url $indexUrl
    if ($LASTEXITCODE -eq 0) {
        # Khong pin torchvision: de pip tu chon ban khop voi torch da cai
        python -m pip install torchvision --index-url $indexUrl
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[!] Cai PyTorch that bai. Nguyen nhan thuong gap:" -ForegroundColor Red
    Write-Host "    - Kenh $CudaChannel khong co torch $TorchVersion." -ForegroundColor Red
    Write-Host "      Xem ban co san: https://download.pytorch.org/whl/$CudaChannel/torch/" -ForegroundColor Red
    Write-Host "    Cach xu ly:" -ForegroundColor Red
    Write-Host "      .\scripts\01_setup_env.ps1 -TorchVersion ''       # lay ban moi nhat" -ForegroundColor Red
    Write-Host "      .\scripts\01_setup_env.ps1 -CudaChannel cu128     # doi kenh CUDA" -ForegroundColor Red
    exit 1
}


# Buoc 4: diffusers stack

$req = Join-Path $PSScriptRoot "..\requirements.txt"
Write-Host "`n[..] Cai diffusers stack tu requirements.txt..." -ForegroundColor Yellow
python -m pip install -r $req


# Buoc 5: tao .env neu chua co

$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $PSScriptRoot "..\.env.example") $envFile
    Write-Host "[OK] Da tao .env tu .env.example" -ForegroundColor Green
}

Write-Host "`n=== XONG. Tiep theo: python scripts/02_check_gpu.py ===" -ForegroundColor Cyan
