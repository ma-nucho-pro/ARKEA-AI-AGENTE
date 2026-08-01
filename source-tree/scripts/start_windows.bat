@echo off
cd /d "%~dp0\.."
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
set "ARKEA_DEV_NO_AUTH=1"
start "ARKEA backend de desarrollo" /B python start_arkea.py
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:7210
pause
