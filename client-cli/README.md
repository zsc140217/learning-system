# MCP 2026 CLI Client

交互式终端客户端，支持 MCP 2026-07-28 协议的所有特性。

## 特性

- MRTR（多轮往返请求）- JWT 签名的确认对话框
- Tasks 扩展 - 实时进度追踪
- MCP Apps - UI 模板渲染（CLI 简化版）
- Rich 终端 UI - 美观的表格、进度条、面板

## 安装

```bash
cd client-cli
pip install -r requirements.txt
```

## 使用

### 1. 启动 MCP 服务器

```bash
cd ../mcp-server
python server.py
```

### 2. 启动 CLI 客户端

```bash
python cli.py
```

或指定服务器地址：

```bash
python cli.py --server http://localhost:8080
```

调试模式：

```bash
python cli.py --debug
```

## 命令示例

### 查看帮助
```
You> /help
```

### 列出可用工具
```
You> /tools
```

### 分析会话
```
You> analyze "今天学习了 FastAPI 的依赖注入"
```

### 搜索知识
```
You> search "MCP协议"
```

## 项目结构

```
client-cli/
├── cli.py              # 主入口
├── mcp_client.py       # MCP 协议客户端
├── ui_renderer.py      # UI 渲染组件
├── requirements.txt    # 依赖列表
└── README.md          # 本文档
```

## 技术栈

- **prompt-toolkit** - 交互式命令行
- **rich** - 美观的终端输出
- **httpx** - 异步 HTTP 客户端
- **click** - CLI 参数解析
- **loguru** - 日志记录
