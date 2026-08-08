---
name: run-learning-system
description: Launch and verify the Learning System web application with backend MCP server and frontend React UI
---

# Run Learning System

Learning System 是一个基于 FastAPI + React + PostgreSQL 的智能学习系统，使用 MCP 协议进行通信。

本文档记录了在 Windows 系统上启动前后端服务的完整步骤。

## Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL (运行在 localhost:5432)
- Redis (运行在 localhost:6379)

## Architecture

```
learning-system/
├── mcp-server/          # FastAPI 后端 (端口 8000)
│   ├── server.py        # MCP 服务器主入口
│   └── requirements.txt
└── client/
    └── frontend/        # React 前端 (端口 3000)
        ├── src/
        ├── package.json
        └── postcss.config.js  # 必需！Tailwind CSS 编译配置
```

## Critical Setup - PostCSS Config

**前端样式依赖 PostCSS 配置才能正常显示。** 如果 `client/frontend/postcss.config.js` 不存在，创建它：

```bash
cd client/frontend
cat > postcss.config.js << 'EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF
```

## Build & Run

### 1. 启动后端 (MCP Server)

```bash
cd mcp-server
python server.py
```

后端将启动在 **http://localhost:8000**，提供：
- HTTP 端点: `/`
- WebSocket 端点: `/ws`
- MCP 工具: `chat`, `save_knowledge`, `ui_knowledge_graph` 等

验证：
```bash
curl http://localhost:8000/
```

应该返回 MCP 服务器信息。

### 2. 启动前端 (React UI)

**新终端窗口：**

```bash
cd client/frontend

# 首次运行需要安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将自动选择可用端口（通常是 3000，如果被占用会自动递增到 3001, 3002...）。

输出示例：
```
VITE v5.4.21  ready in 556 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

### 3. 访问应用

打开浏览器访问前端显示的 URL（例如 http://localhost:3000），你应该看到：

- **背景**: 淡蓝紫色渐变 + 微妙的点状图案
- **顶部栏**: 玻璃态半透明效果，带 "LS" Logo 和状态指示器
- **欢迎页**: 大的渐变 Logo + 3 个功能卡片（多轮对话、知识总结、知识图谱）
- **底部工具栏**: 4 个彩色渐变按钮（绿色、蓝色、橙色、紫色）
- **连接状态**: 右上角显示绿色"已连接"

**如果看到纯白背景 + 小按钮 + 无样式**：
1. 检查 `postcss.config.js` 是否存在
2. 重启前端服务器（Ctrl+C 然后重新 `npm run dev`）
3. 浏览器强制刷新（Ctrl+Shift+R）

## Verification Flow

测试完整流程：

```bash
# 1. 在浏览器中输入消息
"什么是 FastAPI？"

# 2. 点击"总结知识点"按钮
# 应该弹出知识点确认对话框

# 3. 点击"知识图谱"按钮
# 应该显示图谱可视化弹窗
```

## Troubleshooting

### 前端样式不显示（白板、黑白色）

**原因**: 缺少 `postcss.config.js`，导致 Tailwind CSS 未被编译。

**修复**:
```bash
cd client/frontend
cat > postcss.config.js << 'EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

# 杀掉旧的 Node 进程
taskkill //F //IM node.exe

# 重启
npm run dev
```

### 端口被占用

前端会自动递增端口（3000 → 3001 → 3002...），查看终端输出确认实际端口。

### WebSocket 连接失败

检查：
1. 后端是否在 8000 端口运行：`netstat -ano | findstr ":8000"`
2. 前端 Vite 配置代理是否正确（`vite.config.ts` 中的 `/ws` 代理）

### TypeScript 编译错误

**症状**: `error TS2339: Property 'inline' does not exist`

**原因**: ReactMarkdown 类型定义问题

**修复**: 已在 `ChatInterface.tsx` 中使用 `any` 类型和手动判断替代

### 后端启动失败

检查：
- PostgreSQL 是否运行
- Redis 是否运行
- `.env` 文件配置是否正确

## Gotchas

1. **PostCSS 配置是必需的**：Vite 不会自动创建它，没有它 Tailwind 完全不工作
2. **端口自动递增**：如果 3000 被占用，前端会自动尝试 3001, 3002... 不要硬编码端口
3. **强制刷新很重要**：浏览器缓存很顽固，CSS 更新后必须 Ctrl+Shift+R
4. **多个 Node 进程**：Windows 上 `npm run dev` 可能留下僵尸进程，使用 `taskkill //F //IM node.exe` 清理
5. **会话历史在内存中**：重启后端会丢失对话历史（未来可用 Redis 持久化）

## Quick Commands

```bash
# 完整启动（两个终端）
# 终端 1:
cd mcp-server && python server.py

# 终端 2:
cd client/frontend && npm run dev

# 清理并重启前端
taskkill //F //IM node.exe
cd client/frontend && npm run dev

# 检查服务状态
netstat -ano | findstr ":8000"  # 后端
netstat -ano | findstr ":3000"  # 前端（或 3001, 3002...）
```

## Agent Path

未来的 AI Agent 应该：
1. 先检查 `postcss.config.js` 是否存在，不存在则创建
2. 启动后端到后台
3. 启动前端到后台
4. 等待 3-5 秒让服务启动
5. 使用 `curl http://localhost:3000` 验证前端可访问
6. 如需截图，使用 `chromium-cli` 访问实际端口

## Notes

- 前端使用 Vite 热更新，修改代码会自动刷新
- 后端需要手动重启才能生效代码更改
- UI 设计使用玻璃态 (glassmorphism) + 渐变色方案
- 消息气泡使用 ReactMarkdown 渲染，支持代码高亮
