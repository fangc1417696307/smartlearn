@echo off
title SmartLearn Redis (6380)
cd /d "%~dp0..\backend\tools\redis"

redis-cli.exe -p 6380 ping >nul 2>&1
if %errorlevel%==0 (
  echo [Redis] Port 6380 is already running.
  timeout /t 3 >nul
  exit /b
)

echo [Redis] Starting 127.0.0.1:6380 ...
echo [Redis] Close this window to stop Redis.
redis-server.exe --port 6380 --bind 127.0.0.1 --save "" --appendonly no
pause
