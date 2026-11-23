@echo off
setlocal
cd /d "%~dp0"

set "PY=..\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Python venv not found: %PY%
  echo Create backend\venv and install requirements.txt first.
  exit /b 1
)

echo ===== Chat end-to-end test =====
"%PY%" test_chat.py
if errorlevel 1 exit /b 1

echo.
echo ===== Presence test =====
"%PY%" test_presence.py
if errorlevel 1 exit /b 1

echo.
echo All tests passed.
endlocal
