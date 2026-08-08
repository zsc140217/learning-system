@echo off
REM ============================================================
REM Learning System - 一键启动所有服务
REM ============================================================
echo.
echo ============================================================
echo Learning System - Full Stack Startup
echo ============================================================
echo.
echo Services:
echo   [1] MCP HTTP Server  - Port 8080
echo   [2] Client Backend   - CLI Mode
echo   [3] Frontend (Vite)  - Port 3000
echo.
echo ============================================================
echo.

REM 检查是否安装了必要的工具
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 16+
    pause
    exit /b 1
)

REM 检查 .env 文件
if not exist "mcp-server\.env" (
    echo [WARNING] mcp-server\.env not found
    echo Please copy .env.example to .env and configure:
    echo   - DEEPSEEK_API_KEY
    echo.
    set /p continue="Continue anyway? (y/n): "
    if /i not "%continue%"=="y" exit /b 1
    echo.
)

REM 启动 MCP HTTP Server
echo [1/3] Starting MCP HTTP Server...
echo ============================================================
cd mcp-server

REM 检查虚拟环境
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM 激活虚拟环境并安装依赖
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

REM 在新窗口启动 MCP Server
start "MCP Server (Port 8080)" cmd /k "cd /d "%cd%" && venv\Scripts\activate.bat && python http_server.py"

echo [OK] MCP Server started in new window
echo.
cd ..

REM 等待服务启动
timeout /t 3 /nobreak >nul

REM 启动 Frontend
echo [2/3] Starting Frontend (Vite)...
echo ============================================================
cd client\frontend

REM 检查 node_modules
if not exist "node_modules\" (
    echo Installing frontend dependencies...
    call npm install
)

REM 在新窗口启动前端
start "Frontend (Port 3000)" cmd /k "cd /d "%cd%" && npm run dev"

echo [OK] Frontend started in new window
echo.
cd ..\..

REM 等待前端启动
timeout /t 3 /nobreak >nul

REM 启动 Client Backend (CLI)
echo [3/3] Starting Client Backend (CLI Mode)...
echo ============================================================
cd client

REM 检查虚拟环境
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM 激活虚拟环境并安装依赖
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

cd backend

echo.
echo ============================================================
echo All Services Started!
echo ============================================================
echo.
echo   MCP Server:  http://localhost:8080
echo   Frontend:    http://localhost:3000
echo   Backend:     CLI Interactive Mode (current window)
echo.
echo ============================================================
echo.
echo Press Ctrl+C in each window to stop services
echo.

REM 在当前窗口运行 CLI
python main.py
