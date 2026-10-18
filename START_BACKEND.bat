@echo off
chcp 65001 > nul
cd /d %~dp0backend
if not exist .venv (
  echo [안내] 먼저 START_CORE.bat을 실행해 Core 환경을 준비합니다.
  pause
  exit /b 1
)
call .venv\Scripts\activate
uvicorn main:app --reload
pause
