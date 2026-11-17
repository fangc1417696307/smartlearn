@echo off
title SmartLearn Launcher
echo ============================================
echo   SmartLearn one-click start
echo   Redis(6380) + Kafka(9092) + Backend(8001) + Frontend(5173)
echo ============================================
echo.

start "SmartLearn Redis" cmd /k "%~dp0scripts\start-redis.bat"
timeout /t 2 >nul
start "SmartLearn Kafka" cmd /k "%~dp0scripts\start-kafka.bat"
timeout /t 3 >nul
start "SmartLearn Backend" cmd /k "%~dp0scripts\start-backend.bat"
timeout /t 3 >nul
start "SmartLearn Frontend" cmd /k "%~dp0scripts\start-frontend.bat"
timeout /t 5 >nul
start "" http://127.0.0.1:5173

echo All services started. Close the service windows to stop them.
timeout /t 5 >nul
