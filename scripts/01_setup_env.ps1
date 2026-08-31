<#
.SYNOPSIS
    Cai dat moi truong AI local cho du an (PyTorch CUDA + diffusers).

.DESCRIPTION
    MAC DINH: khong dong vao bat ky duong dan nao cua may ban.
    pip va HuggingFace dung thu muc cache mac dinh cua he dieu hanh:
        pip  -> %LOCALAPPDATA%\pip\Cache
        HF   -> %USERPROFILE%\.cache\huggingface
    Tong cong can khoang 12 GB trong tren o he thong (thuong la C:).

    CHI khi truyen -ModelRoot thi script moi chuyen cache sang o khac.
    Dung tuy chon nay neu o C sap day.

.PARAMETER ModelRoot
    Thu muc chua cache pip + HuggingFace, vi du "D:\AI_Models".
    Bo trong = giu nguyen mac dinh he thong (khuyen nghi cho da so nguoi dung).

.PARAMETER Persist
    Chi co tac dung khi da truyen -ModelRoot.
    Ghi HF_HOME / PIP_CACHE_DIR vinh vien vao bien moi truong User,
    tuc la MOI du an Python sau nay tren may cung dung thu muc do.
    Khong co co nay thi chi ap dung trong phien PowerShell hien tai.

.EXAMPLE
    .\scripts\01_setup_env.ps1
    Cai binh thuong, cache nam o vi tri mac dinh cua Windows.

.EXAMPLE
    .\scripts\01_setup_env.ps1 -ModelRoot "E:\AI_Models" -Persist
    Chuyen cache sang o E va nho vinh vien.
#>
param(
    [string]$ModelRoot = "",
    [switch]$Persist,

    [ValidateSet("auto", "cu118", "cu126", "cu128", "cpu")]
    [string]$CudaChannel = "auto",

    [string]$TorchVersion = "2.13.0",

    [switch]$Lock
)

$ErrorActionPreference = "Stop"

function Get-FreeGB($path) {
    $qualifier = Split-Path -Qualifier $path       # vi du "C:"
    $drive = Get-PSDrive $qualifier.TrimEnd(":") -ErrorAction SilentlyContinue
    if ($drive) { return [math]::Round($drive.Free / 1GB, 1) }
    return $null
}

Write-Host "=== SETUP MOI TRUONG AI LOCAL ===`n" -ForegroundColor Cyan


# quyet dinh noi dat cache

if ([string]::IsNullOrWhiteSpace($ModelRoot)) {
    # --- Che do mac dinh: KHONG thay doi gi ---
    $hfPath  = if ($env:HF_HOME) { $env:HF_HOME } else { Join-Path $env:USERPROFILE ".cache\huggingface" }
    $pipPath = if ($env:PIP_CACHE_DIR) { $env:PIP_CACHE_DIR } else { Join-Path $env:LOCALAPPDATA "pip\Cache" }

    Write-Host "[i] Che do mac dinh - khong thay doi duong dan nao tren may ban." -ForegroundColor Gray
    Write-Host "    HuggingFace cache : $hfPath"
    Write-Host "    pip cache         : $pipPath"
    Write-Host "    (Muon doi cho: chay lai voi -ModelRoot 'E:\AI_Models')`n" -ForegroundColor Gray
}
else {
    # --- Che do chuyen huong: nguoi dung chu dong yeu cau ---
    $hfPath  = Join-Path $ModelRoot "huggingface"
    $pipPath = Join-Path $ModelRoot "pip-cache"
    $tmpPath = Join-Path $ModelRoot "tmp"
    foreach ($p in @($hfPath, $pipPath, $tmpPath)) {
        if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
    }

    $env:HF_HOME = $hfPath
    $env:PIP_CACHE_DIR = $pipPath
    # TMP chi doi trong phien nay: pip giai nen wheel torch can ~5GB tam thoi.
    # Khong ghi vinh vien vi rat nhieu phan mem khac cung dung bien TMP.
    $env:TMP = $tmpPath
    $env:TEMP = $tmpPath

    Write-Host "[OK] Cache chuyen sang: $ModelRoot" -ForegroundColor Green
    Write-Host "     HF_HOME       = $hfPath"
    Write-Host "     PIP_CACHE_DIR = $pipPath"
    Write-Host "     TMP/TEMP      = $tmpPath  (chi trong phien nay)"

    if ($Persist) {
        [Environment]::SetEnvironmentVariable("HF_HOME", $hfPath, "User")
        [Environment]::SetEnvironmentVariable("PIP_CACHE_DIR", $pipPath, "User")
        Write-Host "[!] Da ghi VINH VIEN vao bien moi truong User." -ForegroundColor Yellow
        Write-Host "    Moi du an Python sau nay tren may cung se dung thu muc nay." -ForegroundColor Yellow
        Write-Host "    Muon go bo: [Environment]::SetEnvironmentVariable('HF_HOME', `$null, 'User')" -ForegroundColor DarkGray
    }
    else {
        Write-Host "[i] Chi ap dung trong phien PowerShell nay (them -Persist de nho vinh vien)." -ForegroundColor Gray
    }
    Write-Host ""
}


# canh bao dung luong

$freeHF = Get-FreeGB $hfPath
$freePip = Get-FreeGB $pipPath
Write-Host "[i] Dung luong trong: cache HF $freeHF GB | cache pip $freePip GB"
Write-Host "    Can khoang 12 GB (torch ~3GB + wheel tam ~5GB + model ~3.5GB)."
if (($freeHF -ne $null -and $freeHF -lt 12) -or ($freePip -ne $null -and $freePip -lt 12)) {
    Write-Host "[!] KHONG DU CHO. Hay don dep o dia, hoac chay lai voi -ModelRoot tro sang o khac." -ForegroundColor Red
    $answer = Read-Host "    Van muon tiep tuc? (y/N)"
    if ($answer -ne "y") { Write-Host "Da dung." -ForegroundColor Yellow; exit 1 }
}
Write-Host ""


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

if ($Lock) {
    $req = Join-Path $PSScriptRoot "..\requirements-lock.txt"
    Write-Host "`n[..] Cai tu requirements-lock.txt (ban chinh xac da kiem chung)..." -ForegroundColor Yellow
}
else {
    $req = Join-Path $PSScriptRoot "..\requirements.txt"
    Write-Host "`n[..] Cai tu requirements.txt (khoang phien ban linh hoat)..." -ForegroundColor Yellow
}
python -m pip install -r $req


# Buoc 5: tao .env neu chua co

$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $PSScriptRoot "..\.env.example") $envFile
    Write-Host "[OK] Da tao .env tu .env.example" -ForegroundColor Green
}

Write-Host "`n=== XONG. Tiep theo: python scripts/02_check_gpu.py ===" -ForegroundColor Cyan
