@echo off
REM MCP HTTP Server Startup Script
REM Usage: start_http_server.bat

echo ============================================
echo MCP HTTP Server - Starting...
echo Protocol: MCP 2026-07-28 (Stateless)
echo ============================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\" (
    echo [ERROR] Virtual environment not found
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check dependencies
python -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    echo [ERROR] Missing dependencies: fastapi, uvicorn
    echo Installing required packages...
    pip install fastapi uvicorn httpx
)

REM Start HTTP server
echo [START] Launching HTTP server on port 8080...
echo [CTRL+C] Press Ctrl+C to stop
echo.

python http_server.py

pause
