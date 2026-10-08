@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  POWERPLANT ENGINEERING CONTROL CENTER
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan di PATH.
    echo Install Python terlebih dahulu, lalu coba lagi.
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo Streamlit belum terinstall.
    echo Menjalankan instalasi dependency...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Instalasi dependency gagal.
        pause
        exit /b 1
    )
)

echo.
echo Starting dashboard...
echo Browser akan membuka http://localhost:8501
echo Untuk menghentikan dashboard tekan Ctrl+C pada window ini.
echo.
python -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo Dashboard berhenti karena error. Lihat pesan di atas.
)
pause
