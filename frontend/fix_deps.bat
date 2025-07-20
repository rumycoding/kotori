@echo off
echo ============================================
echo   Kotori Frontend - Dependency Fix Script
echo ============================================
echo.

echo [INFO] Checking current react-scripts installation...
npm list react-scripts 2>nul
if errorlevel 1 (
    echo [INFO] react-scripts not found or broken
) else (
    echo [INFO] react-scripts found, checking version...
    npm list react-scripts | findstr "0.0.0" >nul
    if not errorlevel 1 (
        echo [WARNING] react-scripts has invalid version 0.0.0, will reinstall
        echo [INFO] Uninstalling broken react-scripts...
        npm uninstall react-scripts
    )
)

echo.
echo [INFO] Cleaning up existing dependencies...
if exist "node_modules" (
    echo [INFO] Removing node_modules directory...
    rmdir /s /q node_modules
)

if exist "package-lock.json" (
    echo [INFO] Removing package-lock.json...
    del package-lock.json
)

echo.
echo [INFO] Clearing npm cache...
npm cache clean --force

echo.
echo [INFO] Installing react-scripts first...
npm install react-scripts@5.0.1 --save --legacy-peer-deps
if errorlevel 1 (
    echo [ERROR] Failed to install react-scripts@5.0.1
    echo [INFO] Trying with --force flag...
    npm install react-scripts@5.0.1 --save --force
    if errorlevel 1 (
        echo [ERROR] Still failed to install react-scripts
        goto :error
    )
)

echo.
echo [INFO] Installing remaining dependencies...
npm install --legacy-peer-deps
if errorlevel 1 (
    echo [ERROR] Failed to install other dependencies
    goto :error
)

echo.
echo [INFO] Verifying react-scripts installation...
npm list react-scripts
if errorlevel 1 (
    echo [WARNING] react-scripts verification failed
    goto :error
)

echo.
echo [SUCCESS] Dependencies installed successfully!
echo.
echo You can now run:
echo   npm start
echo   npx react-scripts start
echo   or
echo   npm run dev
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] Installation failed. Manual steps to try:
echo.
echo 1. Delete node_modules and package-lock.json
echo 2. Run: npm cache clean --force
echo 3. Run: npm install react-scripts@5.0.1 --force
echo 4. Run: npm install --legacy-peer-deps
echo.
echo Alternative: Try using yarn instead of npm:
echo   yarn install
echo   yarn start
echo.
pause
exit /b 1