@echo off
echo =====================================================
echo   ShopCoins - Flask App
echo =====================================================
cd /d "%~dp0"

if not exist "dino\Scripts\python.exe" (
    echo Creez mediu virtual...
    python -m venv dino
)

echo Instalez dependente...
dino\Scripts\pip install -r requirements.txt --quiet

echo.
echo Pornesc serverul Flask la http://localhost:5000
echo.
echo Apasa Ctrl+C pentru a opri serverul.
echo =====================================================

set FLASK_APP=run.py
set FLASK_DEBUG=1
dino\Scripts\python run.py
pause
