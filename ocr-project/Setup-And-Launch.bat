@echo off
setlocal enabledelayedexpansion
title INVA-AUDIT Desktop App Setup ^& Launcher
color 0b

echo ======================================================================
echo             INVA-AUDIT -- Standalone Desktop Application
echo           Physical Inventory Verification ^& Zonal OCR System
echo ======================================================================
echo.

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

:: ----------------------------------------------------------------------
:: STEP 1: Verify Python Environment
:: ----------------------------------------------------------------------
echo [1/4] Checking Python runtime...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo       Found: %%i

:: ----------------------------------------------------------------------
:: STEP 2: Verify & Install Python OCR Dependencies
:: ----------------------------------------------------------------------
echo [2/4] Checking Python OCR packages (RapidOCR, OpenCV, Flask)...
python -c "import flask, flask_cors, cv2, numpy, rapidocr_onnxruntime" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Installing required OCR libraries (one-time setup, please wait)...
    python -m pip install --quiet flask flask-cors opencv-python-headless numpy rapidocr_onnxruntime
    if %errorlevel% neq 0 (
        echo [WARN] Pip install had warnings, retrying with user flag...
        python -m pip install --user flask flask-cors opencv-python-headless numpy rapidocr_onnxruntime
    )
    echo       OCR libraries installed successfully!
) else (
    echo       All Python OCR packages are verified and ready.
)

:: ----------------------------------------------------------------------
:: STEP 3: Verify Node.js Environment
:: ----------------------------------------------------------------------
echo [3/4] Checking Node.js runtime...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please install Node.js (LTS) from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo       Found Node: %%i

if not exist "%APP_DIR%server\node_modules" (
    echo       Installing server modules (one-time setup, please wait)...
    cd /d "%APP_DIR%server"
    call npm install --silent --no-audit --no-fund
    cd /d "%APP_DIR%"
    echo       Server modules ready!
) else (
    echo       Server modules verified.
)

:: ----------------------------------------------------------------------
:: STEP 4: Create Windows Desktop Shortcut (if not exists)
:: ----------------------------------------------------------------------
echo [4/4] Creating Windows Desktop Shortcut...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut(\"$d\INVA-AUDIT.lnk\"); $s.TargetPath = '%APP_DIR%Launch-INVA-AUDIT.vbs'; $s.WorkingDirectory = '%APP_DIR%'; $s.Description = 'INVA-AUDIT Desktop App'; $s.Save();" >nul 2>&1
echo       Desktop Shortcut ready on your screen!

echo.
echo ======================================================================
echo            Setup complete! Launching INVA-AUDIT Desktop App...
echo ======================================================================
echo.

:: Launch the silent desktop application
start "" "%APP_DIR%Launch-INVA-AUDIT.vbs"
timeout /t 2 /nobreak >nul
exit
