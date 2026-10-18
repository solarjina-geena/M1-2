@echo off
chcp 65001 > nul
cd /d %~dp0backend
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-core.txt
uvicorn main:app --reload
pause
