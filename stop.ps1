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
$port3000 = netstat -ano | findstr ":3000" | Select-String "LISTENING"
if ($port3000) {
    $pid3000 = ($port3000 -split '\s+')[-1]
    Stop-Process -Id $pid3000 -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Da tat frontend (cong 3000)." -ForegroundColor Green
} else {
    Write-Host "[OK] Frontend khong chay hoac da tat." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " He thong da tat hoan toan." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Seconds 2
