@echo off
chcp 65001 > nul
cd /d %~dp0backend
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements-firestore.txt
pause
