@echo off
echo ============================================================
echo Learning System Frontend - Starting...
echo ============================================================
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo [1/2] Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
) else (
    echo [1/2] Dependencies already installed
    echo.
)

echo [2/2] Starting development server...
echo.
echo Frontend will be available at: http://localhost:3000
echo Press Ctrl+C to stop
echo.

call npm run dev

pause
