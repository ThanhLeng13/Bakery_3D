# ============================================================
# BAKERY 3D - SCRIPT TAT HE THONG
# Chay: .\stop.ps1
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Red
Write-Host "   BAKERY 3D - TAT HE THONG            " -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

Write-Host "[*] Dang tat cac tien trinh backend (uvicorn)..." -ForegroundColor Yellow

# Get-Process trong PS 5.1 khong co .CommandLine — dung Get-CimInstance thay the
$uvicornProcs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like "*uvicorn*" }

if ($uvicornProcs) {
    $uvicornProcs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "[OK] Da tat tien trinh uvicorn." -ForegroundColor Green
}

# Backup: kill theo cong 8000
$port8000 = netstat -ano | findstr ":8000" | Select-String "LISTENING"
if ($port8000) {
    $pid8000 = ($port8000 -split '\s+')[-1]
    Stop-Process -Id $pid8000 -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Da tat backend (cong 8000)." -ForegroundColor Green
} else {
    Write-Host "[OK] Backend khong chay hoac da tat." -ForegroundColor Green
}

Write-Host "[*] Dang tat cac tien trinh frontend (node/next)..." -ForegroundColor Yellow
$frontendStopped = $false
foreach ($port in @(3000, 3001, 3002)) {
    $portCheck = netstat -ano | findstr ":$port " | Select-String "LISTENING"
    if ($portCheck) {
        $pidCheck = ($portCheck -split '\s+')[-1]
        $procCheck = Get-Process -Id $pidCheck -ErrorAction SilentlyContinue
        $procName = if ($procCheck) { $procCheck.ProcessName } else { "Unknown" }
        if ($procName -eq "node" -or $procName -eq "next-router-worker") {
            Stop-Process -Id $pidCheck -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Da tat frontend (cong $port)." -ForegroundColor Green
            $frontendStopped = $true
        }
    }
}
if (-not $frontendStopped) {
    Write-Host "[OK] Frontend khong chay hoac da tat." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " He thong da tat hoan toan." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Seconds 2
