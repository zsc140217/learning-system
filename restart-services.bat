@echo off
echo ====================================
echo 重启 Learning System 服务
echo ====================================

echo.
echo [1/3] 停止旧服务...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq MCP*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq WebSocket*" 2>nul

echo.
echo [2/3] 启动 MCP Server (端口 8080)...
start "MCP Server" cmd /k "cd mcp-server && python server.py"

timeout /t 3 /nobreak >nul

echo.
echo [3/3] 启动 WebSocket Server (端口 8000)...
start "WebSocket Server" cmd /k "cd client\backend && python websocket_server.py"

echo.
echo ====================================
echo 服务已启动！
echo ====================================
echo.
echo 前端地址: http://localhost:3000
echo MCP Server: http://localhost:8080
echo WebSocket: ws://localhost:8000/ws
echo.
echo 测试步骤:
echo 1. 打开浏览器访问 http://localhost:3000
echo 2. 确认右上角显示绿色 "Connected"
echo 3. 点击 "Knowledge Graph" 按钮
echo 4. 应该能看到知识图谱可视化
echo.
pause
