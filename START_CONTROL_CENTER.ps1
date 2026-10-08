$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "============================================================"
Write-Host " POWERPLANT ENGINEERING CONTROL CENTER"
Write-Host "============================================================"
Write-Host ""

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python tidak ditemukan di PATH." -ForegroundColor Red
    Write-Host "Install Python terlebih dahulu, lalu coba lagi."
    Read-Host "Press Enter to close"
    exit 1
}

try {
    python -c "import streamlit" 2>$null
} catch {
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Streamlit belum terinstall. Menjalankan instalasi dependency..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Instalasi dependency gagal." -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
}

Write-Host ""
Write-Host "Starting dashboard..." -ForegroundColor Green
Write-Host "Browser akan membuka http://localhost:8501"
Write-Host "Untuk menghentikan dashboard tekan Ctrl+C."
Write-Host ""
python -m streamlit run app.py
