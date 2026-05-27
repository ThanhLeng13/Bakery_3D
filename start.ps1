# ============================================================
# BAKERY 3D - SCRIPT KHOI DONG NHANH
# Double-click hoac chay: .\start.ps1
# ============================================================

$Host.UI.RawUI.WindowTitle = "Bakery 3D - Launcher"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   BAKERY 3D - KHOI DONG HE THONG      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

# Kiem tra venv backend
$venvActivate = Join-Path $backendDir "venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Host "[!] Chua co virtual environment. Dang tao..." -ForegroundColor Yellow
    Set-Location $backendDir
    python -m venv venv
    Write-Host "[OK] Da tao venv." -ForegroundColor Green
}

# Kiem tra .env backend
$backendEnv = Join-Path $backendDir ".env"
if (-not (Test-Path $backendEnv)) {
    Write-Host "[!] Chua co file backend\.env !" -ForegroundColor Red
    Write-Host "    Sao chep backend\.env.example thanh backend\.env va dien thong tin Supabase." -ForegroundColor Red
    Read-Host "Nhan Enter de thoat"
    exit 1
}

# Kiem tra .env.local frontend
$frontendEnv = Join-Path $frontendDir ".env.local"
if (-not (Test-Path $frontendEnv)) {
    Write-Host "[!] Chua co file frontend\.env.local !" -ForegroundColor Red
    Write-Host "    Sao chep frontend\.env.local.example thanh frontend\.env.local va dien thong tin." -ForegroundColor Red
    Read-Host "Nhan Enter de thoat"
    exit 1
}

# ---- BACKEND ----
Write-Host "[1/2] Khoi dong BACKEND (FastAPI - cong 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-NoExit",
    "-Command",
    "cd '$backendDir'; .\venv\Scripts\Activate.ps1; Write-Host '[BACKEND] Dang cai thu vien...' -ForegroundColor Cyan; pip install -r requirements.txt -q; if (`$LASTEXITCODE -ne 0) { Write-Host '[BACKEND] Cai dat thu vien THAT BAI!' -ForegroundColor Red; Read-Host 'Nhan Enter de dong'; exit 1 }; Write-Host '[BACKEND] Dang chay server...' -ForegroundColor Green; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 3

# ---- FRONTEND ----
$frontendPort = 3000
$port3000InUse = netstat -ano | findstr ":3000 " | Select-String "LISTENING"
if ($port3000InUse) {
    $pid3000 = ($port3000InUse -split '\s+')[-1]
    $proc3000 = Get-Process -Id $pid3000 -ErrorAction SilentlyContinue
    $procName3000 = if ($proc3000) { $proc3000.ProcessName } else { "Unknown" }
    if ($procName3000 -eq "node" -or $procName3000 -eq "next-router-worker") {
        Write-Host "[*] Phat hien frontend dang chay o cong 3000. Dang dung tien trinh cu (PID $pid3000)..." -ForegroundColor Yellow
        Stop-Process -Id $pid3000 -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    } else {
        Write-Host "[!] Cong 3000 dang bi chiem boi ung dung khac (PID: $pid3000, ten: $procName3000)." -ForegroundColor Yellow
        Write-Host "    Chuyen frontend sang cong 3001..." -ForegroundColor Yellow
        $frontendPort = 3001
        
        # Kiem tra tiep xem cong 3001 co bi chiem khong
        $port3001InUse = netstat -ano | findstr ":3001 " | Select-String "LISTENING"
        if ($port3001InUse) {
            $pid3001 = ($port3001InUse -split '\s+')[-1]
            $proc3001 = Get-Process -Id $pid3001 -ErrorAction SilentlyContinue
            $procName3001 = if ($proc3001) { $proc3001.ProcessName } else { "Unknown" }
            if ($procName3001 -eq "node" -or $procName3001 -eq "next-router-worker") {
                Write-Host "[*] Phat hien frontend dang chay o cong 3001. Dang dung tien trinh cu (PID $pid3001)..." -ForegroundColor Yellow
                Stop-Process -Id $pid3001 -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
            } else {
                Write-Host "[!] Cong 3001 cung bi chiem boi ung dung khac (PID: $pid3001, ten: $procName3001)." -ForegroundColor Yellow
                Write-Host "    Chuyen frontend sang cong 3002..." -ForegroundColor Yellow
                $frontendPort = 3002
            }
        }
    }
}

Write-Host "[2/2] Khoi dong FRONTEND (Next.js - cong $frontendPort)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; Write-Host '[FRONTEND] Dang kiem tra packages...' -ForegroundColor Cyan; if (-not (Test-Path 'node_modules')) { npm install; if (`$LASTEXITCODE -ne 0) { Write-Host '[FRONTEND] npm install THAT BAI!' -ForegroundColor Red; Read-Host 'Nhan Enter de dong'; exit 1 } }; Write-Host '[FRONTEND] Dang chay server...' -ForegroundColor Green; npm run dev -- -p $frontendPort"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " He thong dang khoi dong..." -ForegroundColor Green
Write-Host ""
Write-Host " Backend API:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host " API Docs:     http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host " Frontend:     http://localhost:$frontendPort" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host " Doi khoang 10-15 giay roi mo trinh duyet." -ForegroundColor Yellow
Write-Host " De TAT het, dong 2 cua so terminal kia" -ForegroundColor Yellow
Write-Host " hoac chay: .\stop.ps1" -ForegroundColor Yellow
Write-Host ""

# Tu dong mo trinh duyet sau 12 giay
Write-Host " Trinh duyet se tu dong mo sau 12 giay..." -ForegroundColor Cyan
Start-Sleep -Seconds 12
Start-Process "http://localhost:$frontendPort"

Read-Host "Nhan Enter de dong cua so nay (cac server van chay)"

