@echo off
title INVA-AUDIT Desktop Launcher
color 0b
echo ========================================================
echo    INVA-AUDIT -- Desktop Application Launcher
echo    Physical Inventory Verification System
echo ========================================================
echo.

:: 1. Check & Start Python OCR service on port 5001
echo [1/3] Checking Python OCR service...
netstat -ano | findstr ":5001" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo       Starting RapidOCR Engine in background...
    start /b "" python "%~dp0image-service\app.py"
    timeout /t 2 /nobreak >nul
) else (
    echo       Python OCR engine is already active.
)

:: 2. Check & Start Node backend on port 5000
echo [2/3] Checking Local Application Server...
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo       Starting Local Server in background...
    start /b "" node "%~dp0server\server.js"
    timeout /t 2 /nobreak >nul
) else (
    echo       Local Server is already active.
)

:: 3. Launch Native Desktop Window
echo [3/3] Opening INVA-AUDIT Desktop Window...
echo.

:: Try Microsoft Edge App Mode (Built-in on all Windows laptops)
start "" "msedge.exe" --app="http://localhost:5000" --window-size=1440,900 --user-data-dir="%LOCALAPPDATA%\INVA-AUDIT-Profile"
if %errorlevel% equ 0 goto done

:: Fallback to Google Chrome App Mode
start "" "chrome.exe" --app="http://localhost:5000" --window-size=1440,900 --user-data-dir="%LOCALAPPDATA%\INVA-AUDIT-Profile"
if %errorlevel% equ 0 goto done

:: Generic default browser fallback
start "" "http://localhost:5000"

:done
echo INVA-AUDIT Desktop Window is now open!
timeout /t 3 >nul
exit
