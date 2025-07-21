@echo off
title Kotori Bot - Language Learning UI

echo.
echo ================================================================
echo                  Kotori Bot - Language Learning UI
echo ================================================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo.
    echo Please copy .env.example to .env and configure your settings:
    echo   1. Copy .env.example to .env
    echo   2. Edit .env with your Azure OpenAI credentials
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

echo [INFO] Environment file found
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo.
    pause
    exit /b 1
)

echo [INFO] Python is available
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 16+ from https://nodejs.org
    echo.
    pause
    exit /b 1
)

echo [INFO] Node.js is available
echo.

REM Start backend
echo [INFO] Starting Kotori Bot Backend...
echo.
cd backend
start "Kotori Backend" cmd /k "DEBUG_MODE=true python run_backend.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Go back to root and start frontend
cd ..
echo [INFO] Starting Kotori Bot Frontend...
echo.
cd frontend

REM Check if node_modules exists, if not install dependencies
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    echo [INFO] Using --legacy-peer-deps to resolve dependency conflicts...
    npm install --legacy-peer-deps
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies
        echo [INFO] Please try manually: npm install --legacy-peer-deps
        pause
        exit /b 1
    )
)

REM Start frontend with more robust command
echo [INFO] Starting frontend development server...
start "Kotori Frontend" cmd /k "npm start"

echo.
echo ================================================================
echo                    Kotori Bot Started Successfully!
echo ================================================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo The application will open in your browser automatically.
echo.
echo IMPORTANT:
echo - Make sure Anki is running with AnkiConnect addon
echo - Both terminal windows should remain open
echo - Press Ctrl+C in either window to stop the services
echo.
echo ================================================================
echo.
pause