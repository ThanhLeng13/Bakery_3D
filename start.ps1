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

# ---- FRONTEND PORT RESOLUTION ----
$frontendPort = 3000
$portFound = $false
while (-not $portFound) {
    $portInUse = netstat -ano | findstr ":$frontendPort " | Select-String "LISTENING"
    if ($portInUse) {
        $pid = ($portInUse -split '\s+')[-1]
        $pidInt = $null
        if ([int]::TryParse($pid, [ref]$pidInt)) {
            $proc = Get-Process -Id $pidInt -ErrorAction SilentlyContinue
            $procName = if ($proc) { $proc.ProcessName } else { "Unknown" }
            if ($procName -eq "node" -or $procName -eq "next-router-worker") {
                $procObj = Get-CimInstance Win32_Process -Filter "ProcessId = $pidInt" -ErrorAction SilentlyContinue
                $cmdLine = if ($procObj) { $procObj.CommandLine } else { "" }
                $execPath = if ($procObj) { $procObj.ExecutablePath } else { "" }
                
                $isOurProcess = $false
                if (($cmdLine -and ($cmdLine -like "*Bakery_3D*" -or $cmdLine -like "*next*")) -or 
                    ($execPath -and ($execPath -like "*Bakery_3D*" -or $execPath -like "*next*"))) {
                    $isOurProcess = $true
                }
                
                if ($isOurProcess) {
                    Write-Host "[*] Phat hien frontend dang chay o cong $frontendPort. Dang dung tien trinh cu (PID $pidInt)..." -ForegroundColor Yellow
                    Stop-Process -Id $pidInt -Force -ErrorAction SilentlyContinue
                    Start-Sleep -Seconds 1
                    $portFound = $true
                } else {
                    Write-Host "[!] Cong $frontendPort dang duoc dung boi tien trinh Node/Next khac khong thuoc du an nay (PID: $pidInt, Command: $cmdLine)." -ForegroundColor Yellow
                    Write-Host "    Chuyen sang cong tiep theo..." -ForegroundColor Yellow
                    $frontendPort++
                }
            } else {
                Write-Host "[!] Cong $frontendPort dang bi chiem boi ung dung khac (PID: $pidInt, ten: $procName)." -ForegroundColor Yellow
                $frontendPort++
            }
        } else {
            $frontendPort++
        }
    } else {
        $portFound = $true
    }
}

# ---- BACKEND ----
Write-Host "[1/2] Khoi dong BACKEND (FastAPI - cong 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-NoExit",
    "-Command",
    "cd '$backendDir'; .\venv\Scripts\Activate.ps1; `$env:FRONTEND_PORT = $frontendPort; Write-Host '[BACKEND] Dang cai thu vien...' -ForegroundColor Cyan; pip install -r requirements.txt -q; if (`$LASTEXITCODE -ne 0) { Write-Host '[BACKEND] Cai dat thu vien THAT BAI!' -ForegroundColor Red; Read-Host 'Nhan Enter de dong'; exit 1 }; Write-Host '[BACKEND] Dang chay server...' -ForegroundColor Green; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 3

# ---- FRONTEND ----
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

