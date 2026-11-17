@echo off
title SmartLearn Kafka (9092)
set "JAVA_HOME=D:\develop\JDK"
if not exist "%JAVA_HOME%\bin\java.exe" (
  for /f "delims=" %%j in ('where java 2^>nul') do (
    for %%i in ("%%j") do set "JAVA_HOME=%%~dpi.."
  )
)
set "KAFKA_HEAP_OPTS=-Xmx512M -Xms256M"
cd /d "%~dp0..\backend\tools\kafka\kafka_2.13-4.4.0"

if not exist "..\data\meta.properties" (
  echo [Kafka] First run: formatting KRaft storage...
  for /f "delims=" %%i in ('bin\windows\kafka-storage.bat random-uuid') do set "CID=%%i"
  bin\windows\kafka-storage.bat format --standalone -t "%CID%" -c config\server.properties
)

echo [Kafka] broker: 127.0.0.1:9092
echo [Kafka] Close this window to stop Kafka.
bin\windows\kafka-server-start.bat config\server.properties
pause
