@echo off
title SmartLearn Backend (8001)
cd /d "%~dp0..\backend"
echo [Backend] http://127.0.0.1:8001
echo [Backend] API docs: http://127.0.0.1:8001/docs
venv\Scripts\python.exe -m uvicorn main:app --port 8001
pause
