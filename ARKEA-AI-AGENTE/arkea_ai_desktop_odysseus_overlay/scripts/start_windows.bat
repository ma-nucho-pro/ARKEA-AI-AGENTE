@echo off
cd /d "%~dp0\.."
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
start http://127.0.0.1:7210
python start_arkea.py
pause
