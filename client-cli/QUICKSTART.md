# 快速开始指南

## 第一步：安装依赖

### Windows 自动安装
```bash
start.bat
```

### 手动安装
```bash
pip install -r requirements.txt
```

## 第二步：配置并启动服务器

### 1. 生成 JWT 密钥
```bash
cd ../mcp-server
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. 更新配置文件
将生成的密钥填入 `../claude_desktop_config.json` 的 `JWT_SECRET` 字段

### 3. 启动服务器
```bash
python server.py
```

服务器将在 `http://localhost:8080` 启动

## 第三步：启动 CLI 客户端

在新的终端窗口：

```bash
cd client-cli
python cli.py
```

## 测试示例

### 1. 测试基础功能
```
You> /tools
```

应该看到可用工具列表

### 2. 测试会话分析
```
You> analyze "今天学习了 MCP 协议的 MRTR 特性"
```

### 3. 测试 MRTR 确认对话框
（需要服务器实现对应的危险操作工具）

### 4. 测试 Tasks 进度追踪
（需要服务器实现长时间任务）

## 常见问题

### Q: 连接失败？
A: 确保服务器已启动并监听在 8080 端口

### Q: 找不到模块？
A: 运行 `pip install -r requirements.txt` 安装依赖

### Q: 服务器启动失败？
A: 检查 `JWT_SECRET` 是否已配置

## 下一步

- 阅读 `README.md` 了解更多命令
- 查看 `mcp-server/server.py` 了解服务器实现
- 自定义工具和命令
