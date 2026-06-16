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

# Chon che do chay cho Frontend
Write-Host "Lua chon che do khoi dong cho Frontend:" -ForegroundColor Cyan
Write-Host "  [1] Development Mode (Moi truong Phat trien, mac dinh)" -ForegroundColor White
Write-Host "      - Hot Module Replacement, nhanh reload, connect-src bao gom http://localhost:8000" -ForegroundColor Gray
Write-Host "  [2] Production Build  (Build toi uu, kiem tra truoc khi deploy)" -ForegroundColor White
Write-Host "      - Build & chay qua 'npm run start', dung NEXT_PUBLIC_API_URL cho backend" -ForegroundColor Gray
$choiceInput = Read-Host "Nhap lua chon cua ban [1 hoac 2, mac dinh la 1]"
$isProduction = $false
if ($choiceInput -eq "2") {
    $isProduction = $true
    Write-Host "[*] Da chon Production Build Mode." -ForegroundColor Cyan
} else {
    Write-Host "[*] Chay o che do Development Mode." -ForegroundColor Cyan
}

# ---- FRONTEND PORT RESOLUTION ----
$lastPortFile = Join-Path $rootDir ".last_port"
$frontendPort = 3000

# Thu dung lai port lan truoc neu con trong
if (Test-Path $lastPortFile) {
    $savedPort = Get-Content $lastPortFile -Raw
    $savedPortInt = $null
    # Guard: $savedPort co the la $null neu file trong (tranh loi .Trim() tren null)
    if ($savedPort -and [int]::TryParse($savedPort.Trim(), [ref]$savedPortInt)) {
        $frontendPort = $savedPortInt
        Write-Host "[*] Su dung lai cong da luu: $frontendPort" -ForegroundColor Cyan
    }
}

$portFound = $false
while (-not $portFound) {
    $portInUse = netstat -ano | findstr ":$frontendPort " | Select-String "LISTENING"
    if ($portInUse) {
        $listenerPid = ($portInUse -split '\s+')[-1]
        $listenerPidInt = $null
        if ([int]::TryParse($listenerPid, [ref]$listenerPidInt)) {
            $listenerProc = Get-Process -Id $listenerPidInt -ErrorAction SilentlyContinue
            $listenerProcName = if ($listenerProc) { $listenerProc.ProcessName } else { "Unknown" }
            if ($listenerProcName -eq "node" -or $listenerProcName -eq "next-router-worker") {
                $procObj = Get-CimInstance Win32_Process -Filter "ProcessId = $listenerPidInt" -ErrorAction SilentlyContinue
                $cmdLine = if ($procObj) { $procObj.CommandLine } else { "" }
                $execPath = if ($procObj) { $procObj.ExecutablePath } else { "" }

                $isOurProcess = $false
                if (($cmdLine -and ($cmdLine -like "*Bakery_3D*frontend*" -or $cmdLine -like "*Bakery_3D/frontend*")) -or
                    ($execPath -and ($execPath -like "*Bakery_3D*frontend*" -or $execPath -like "*Bakery_3D/frontend*"))) {
                    $isOurProcess = $true
                }

                if ($isOurProcess) {
                    Write-Host "[*] Phat hien frontend dang chay o cong $frontendPort. Dang dung tien trinh cu (PID $listenerPidInt)..." -ForegroundColor Yellow
                    Stop-Process -Id $listenerPidInt -Force -ErrorAction SilentlyContinue
                    Start-Sleep -Seconds 1
                    $portFound = $true
                } else {
                    Write-Host "[!] Cong $frontendPort dang duoc dung boi tien trinh Node/Next khac (PID: $listenerPidInt)." -ForegroundColor Yellow
                    Write-Host "    Chuyen sang cong tiep theo..." -ForegroundColor Yellow
                    $frontendPort++
                }
            } else {
                Write-Host "[!] Cong $frontendPort dang bi chiem boi ung dung khac (PID: $listenerPidInt, ten: $listenerProcName)." -ForegroundColor Yellow
                $frontendPort++
            }
        } else {
            $frontendPort++
        }
    } else {
        $portFound = $true
    }
}

# Luu port vua chon de lan sau su dung lai
Set-Content -Path $lastPortFile -Value "$frontendPort" -Encoding UTF8

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
if ($isProduction) {
    Write-Host "[2/2] Khoi dong FRONTEND (Next.js Production Build - cong $frontendPort)..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList @(
        "-ExecutionPolicy", "Bypass",
        "-NoExit",
        "-Command",
        "cd '$frontendDir'; `$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8000'; Write-Host '[FRONTEND] Dang build production...' -ForegroundColor Cyan; if (-not (Test-Path 'node_modules')) { npm install }; npm run build; if (`$LASTEXITCODE -ne 0) { Write-Host '[FRONTEND] Build THAT BAI!' -ForegroundColor Red; Read-Host 'Nhan Enter de dong'; exit 1 }; Write-Host '[FRONTEND] Dang chay server production...' -ForegroundColor Green; npm run start -- -p $frontendPort"
    )
} else {
    Write-Host "[2/2] Khoi dong FRONTEND (Next.js Development - cong $frontendPort)..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList @(
        "-ExecutionPolicy", "Bypass",
        "-NoExit",
        "-Command",
        "cd '$frontendDir'; Write-Host '[FRONTEND] Dang kiem tra packages...' -ForegroundColor Cyan; if (-not (Test-Path 'node_modules')) { npm install; if (`$LASTEXITCODE -ne 0) { Write-Host '[FRONTEND] npm install THAT BAI!' -ForegroundColor Red; Read-Host 'Nhan Enter de dong'; exit 1 } }; Write-Host '[FRONTEND] Dang chay server dev...' -ForegroundColor Green; npm run dev -- -p $frontendPort"
    )
}

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

# Tu dong mo trinh duyet khi frontend san sang (toi da doi 3 phut cho build production)
Write-Host " Dang doi frontend khoi dong (co the mat 1-2 phut neu la Production Build)..." -ForegroundColor Cyan
$maxRetries = 180
$retryCount = 0
$portIsUp = $false
while (-not $portIsUp -and $retryCount -lt $maxRetries) {
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $frontendPort)
        $tcpClient.Close()
        $portIsUp = $true
    } catch {
        Start-Sleep -Seconds 1
        $retryCount++
    }
}

if ($portIsUp) {
    Write-Host " [OK] Frontend da san sang. Dang mo trinh duyet..." -ForegroundColor Green
    Start-Process "http://localhost:$frontendPort"
} else {
    Write-Host " [!] Khong the ket noi toi frontend sau $maxRetries giay. Vui long kiem tra terminal cua frontend xem co loi khong." -ForegroundColor Red
    Start-Process "http://localhost:$frontendPort"
}

Read-Host "Nhan Enter de dong cua so nay (cac server van chay)"
