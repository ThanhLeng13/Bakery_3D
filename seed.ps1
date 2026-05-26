# ============================================================
# BAKERY 3D - SEED DU LIEU BANH NGOT
# Chay: .\seed.ps1
# ============================================================

$Host.UI.RawUI.WindowTitle = "Bakery 3D - Seed Data"

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "   BAKERY 3D - SEED DU LIEU            " -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""
Write-Host " Script nay se import 18 loai banh ngot" -ForegroundColor White
Write-Host " vao Supabase cua ban." -ForegroundColor White
Write-Host ""

$rootDir = $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$venvActivate = Join-Path $backendDir "venv\Scripts\Activate.ps1"

# Kiem tra venv
if (-not (Test-Path $venvActivate)) {
    Write-Host "[!] Chua co venv. Dang tao..." -ForegroundColor Yellow
    Set-Location $backendDir
    python -m venv venv
}

# Kiem tra .env
$backendEnv = Join-Path $backendDir ".env"
if (-not (Test-Path $backendEnv)) {
    Write-Host "[!] Chua co backend\.env - vui long tao file nay truoc!" -ForegroundColor Red
    Read-Host "Nhan Enter de thoat"
    exit 1
}

Write-Host "[*] Dang kich hoat moi truong ao va chay seed..." -ForegroundColor Cyan
Set-Location $backendDir

& "$venvActivate"
pip install -r requirements.txt -q
Write-Host ""
Write-Host "[*] Dang chay seed_sweet_cakes.py..." -ForegroundColor Yellow
python app/seed_sweet_cakes.py

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Seed du lieu THANH CONG!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " Co loi khi seed du lieu!" -ForegroundColor Red
    Write-Host " Kiem tra lai .env va ket noi Supabase." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

Write-Host ""
Read-Host "Nhan Enter de dong"
