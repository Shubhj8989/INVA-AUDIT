@echo off
setlocal enabledelayedexpansion
title INVA-AUDIT Desktop App Setup ^& Launcher
color 0b

echo ======================================================================
echo             INVA-AUDIT -- Standalone Desktop Application
echo           Physical Inventory Verification and Zonal OCR System
echo ======================================================================
echo.

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

:: ----------------------------------------------------------------------
:: STEP 1: Detect Python Command
:: ----------------------------------------------------------------------
echo [1/4] Detecting Python runtime...
set "PY_CMD="

python --version >nul 2>&1
if %errorlevel% equ 0 set "PY_CMD=python"

if "!PY_CMD!"=="" (
    py --version >nul 2>&1
    if %errorlevel% equ 0 set "PY_CMD=py"
)

if "!PY_CMD!"=="" (
    if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
)

if "!PY_CMD!"=="" (
    for /d %%p in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
        if exist "%%p\python.exe" set "PY_CMD=%%p\python.exe"
    )
)

if "!PY_CMD!"=="" (
    echo [ERROR] Python was not found.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check Add Python to PATH during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('"!PY_CMD!" --version 2^>^&1') do echo       Found: %%i

:: ----------------------------------------------------------------------
:: STEP 2: Verify and Install Python OCR Dependencies
:: ----------------------------------------------------------------------
echo [2/4] Checking Python OCR packages...
"!PY_CMD!" -c "import flask, flask_cors, cv2, numpy, rapidocr_onnxruntime" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Installing required OCR libraries, please wait...
    "!PY_CMD!" -m pip install --quiet flask flask-cors opencv-python-headless numpy rapidocr_onnxruntime
    if %errorlevel% neq 0 (
        "!PY_CMD!" -m pip install --user flask flask-cors opencv-python-headless numpy rapidocr_onnxruntime
    )
    echo       OCR libraries installed successfully!
) else (
    echo       All Python OCR packages are verified and ready.
)

:: ----------------------------------------------------------------------
:: STEP 3: Detect Node.js and Install Server Dependencies
:: ----------------------------------------------------------------------
echo [3/4] Checking Node.js runtime...
set "NODE_CMD="
node --version >nul 2>&1
if %errorlevel% equ 0 set "NODE_CMD=node"

if "!NODE_CMD!"=="" (
    if exist "%APPDATA%\Antigravity\bin\agy-node.cmd" set "NODE_CMD=%APPDATA%\Antigravity\bin\agy-node.cmd"
)

if "!NODE_CMD!"=="" (
    echo [ERROR] Node.js was not found.
    echo Please install Node.js from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('"!NODE_CMD!" --version 2^>^&1') do echo       Found Node: %%i

if not exist "%APP_DIR%server\node_modules" (
    echo       Installing server modules, please wait...
    cd /d "%APP_DIR%server"
    call npm install --silent --no-audit --no-fund
    cd /d "%APP_DIR%"
    echo       Server modules ready!
) else (
    echo       Server modules verified.
)

:: ----------------------------------------------------------------------
:: STEP 4: Create Windows Desktop Shortcut
:: ----------------------------------------------------------------------
echo [4/4] Creating Windows Desktop Shortcut...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut(\"$d\INVA-AUDIT.lnk\"); $s.TargetPath = '%APP_DIR%Launch-INVA-AUDIT.vbs'; $s.WorkingDirectory = '%APP_DIR%'; $s.Description = 'INVA-AUDIT Desktop App'; $s.Save();" >nul 2>&1
echo       Desktop Shortcut ready on your screen!

echo.
echo ======================================================================
echo            Setup complete! Launching INVA-AUDIT Desktop App...
echo ======================================================================
echo.

start "" "%APP_DIR%Launch-INVA-AUDIT.vbs"
ping -n 3 127.0.0.1 >nul
exit
