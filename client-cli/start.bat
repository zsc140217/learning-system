@echo off
echo ========================================
echo MCP 2026 CLI Client
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\Lib\site-packages\rich\" (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Start CLI
echo.
echo Starting CLI client...
echo.
python cli.py

pause
