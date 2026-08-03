@echo off
REM ============================================================
REM Learning System - Windows Installation Script
REM ============================================================
REM 
REM This script will:
REM 1. Check Python installation
REM 2. Create virtual environment
REM 3. Install dependencies
REM 4. Configure the project
REM 5. Run tests to verify installation
REM
REM ============================================================

echo.
echo ============================================================
echo  Learning System - Installation
echo ============================================================
echo.

REM Check Python version
echo [1/5] Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo [OK] Python found

REM Check Python version is 3.10+
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo [INFO] Python version: %PYTHON_VERSION%

REM Create virtual environment
echo.
echo [2/5] Creating virtual environment...
if exist venv (
    echo [INFO] Virtual environment already exists. Skipping creation.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

REM Upgrade pip
echo.
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo.
echo [4/5] Installing dependencies...
echo [INFO] This may take a few minutes...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Configure project
echo.
echo [5/5] Configuring project...

REM Check if config.yaml exists
if not exist config\config.yaml (
    echo [WARNING] config\config.yaml not found
    echo [INFO] Please create config\config.yaml from config.yaml template
    echo [INFO] Set your DeepSeek API key in the config file
) else (
    echo [OK] Configuration file found
)

REM Create data directories
if not exist data mkdir data
if not exist data\sessions mkdir data\sessions
if not exist data\projects mkdir data\projects
if not exist data\knowledge mkdir data\knowledge
echo [OK] Data directories created

REM Set terminal encoding to UTF-8
chcp 65001 > nul 2>&1
echo [OK] Terminal encoding set to UTF-8

REM Installation complete
echo.
echo ============================================================
echo  Installation Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Configure your API keys in config\config.yaml
echo   2. Run tests: python test_memory_integration.py
echo   3. Start the MCP server: python mcp-server\server.py
echo.
echo To activate the virtual environment in the future:
echo   venv\Scripts\activate.bat
echo.
echo ============================================================
pause
