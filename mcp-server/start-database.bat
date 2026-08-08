@echo off
REM 数据库启动和验证脚本 - Windows版本
REM 用途：一键启动PostgreSQL和Redis，并验证连接

echo ========================================
echo  Learning System - 数据库启动脚本
echo ========================================
echo.

REM 检查Docker是否运行
echo [1/5] 检查 Docker 状态...
docker version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未运行，请先启动Docker Desktop
    pause
    exit /b 1
)
echo ✅ Docker 已运行

REM 进入项目目录
cd /d "%~dp0"

REM 启动数据库服务
echo.
echo [2/5] 启动数据库服务...
docker compose up -d
if errorlevel 1 (
    echo ❌ Docker Compose 启动失败
    pause
    exit /b 1
)
echo ✅ 数据库服务已启动

REM 等待数据库就绪
echo.
echo [3/5] 等待数据库就绪...
timeout /t 10 /nobreak >nul
echo ✅ 数据库已就绪

REM 显示服务状态
echo.
echo [4/5] 数据库服务状态:
docker compose ps

REM 运行集成测试
echo.
echo [5/5] 运行集成测试...
python tests\test_database_integration.py
if errorlevel 1 (
    echo.
    echo ⚠️ 测试失败，请检查配置
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 数据库集成配置成功！
echo ========================================
echo.
echo 数据库连接信息:
echo   PostgreSQL: localhost:5432
echo   Redis:      localhost:6379
echo.
pause
