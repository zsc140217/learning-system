@echo off
REM Windows 启动脚本

echo Starting Learning System Client...
echo.

REM 检查虚拟环境
if not exist "venv\" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
echo [2/3] Installing dependencies...
pip install -q -r requirements.txt

REM 启动客户端
echo [3/3] Starting client...
echo.
cd backend
python main.py
