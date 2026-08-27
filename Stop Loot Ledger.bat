@echo off
title Stop Loot Ledger
echo Stopping Loot Ledger...
set FOUND=
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    set FOUND=1
)
if defined FOUND (echo Stopped.) else (echo It was not running.)
timeout /t 2 >nul
