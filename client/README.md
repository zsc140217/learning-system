# Learning System - Client

完整的 MCP 客户端实现，包含 Python 后端和 React 前端。

## 项目结构

```
client/
├── backend/                 # Python 后端 (Phase 2)
│   ├── main.py             # 主程序
│   ├── state.py            # 状态管理器
│   ├── mcp_client.py       # MCP 客户端
│   ├── skill_manager.py    # Skill 管理器
│   ├── task_manager.py     # 任务管理器
│   ├── mrtr_handler.py     # MRTR 处理器
│   └── config.py           # 配置管理
├── frontend/                # React 前端 (Phase 3)
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── services/       # 服务层
│   │   ├── store/          # 状态管理
│   │   └── types/          # TypeScript 类型
│   ├── package.json
│   └── README.md
└── README.md               # 本文件
```

## 快速启动

### 方式 1: 使用启动脚本 (推荐)

#### 后端
```bash
cd backend
python main.py
```

#### 前端
```bash
cd frontend
start.bat           # Windows
# 或
npm run dev         # 跨平台
```

### 方式 2: 手动启动

#### 1. 启动 MCP Server
```bash
cd ../../mcp-server
python server.py
```

#### 2. 启动后端客户端
```bash
cd ../client/backend
python main.py
```

#### 3. 启动前端
```bash
cd ../frontend
npm install
npm run dev
```

访问 http://localhost:3000

## 核心功能

### 后端 (Phase 2)

- **StateManager** - 无状态协议的会话状态管理
- **MCPClient** - stdio 协议通信
- **SkillManager** - Skill 文档加载和管理
- **TaskManager** - 长任务后台轮询
- **MRTRHandler** - 二次确认处理

### 前端 (Phase 3)

- **WebSocket 服务** - 实时双向通信，自动重连
- **MCP 客户端** - JSON-RPC 协议，特性检测
- **UI 渲染引擎** - JSON/HTML 混合渲染
- **状态管理** - Zustand 全局状态
- **标准组件库** - Header, StatsGrid, KnowledgeList, Chart

## MCP 2026 特性支持

| 特性 | 后端 | 前端 | 说明 |
|------|------|------|------|
| 无状态协议 | ✅ | ✅ | 客户端管理所有状态 |
| MRTR | ✅ | ✅ | 二次确认对话框 |
| Tasks | ✅ | ✅ | 长任务轮询和进度条 |
| MCP Apps | ✅ | ✅ | UI 模板渲染 |

## 技术栈

### 后端
- Python 3.10+
- asyncio (异步编程)
- subprocess (进程管理)

### 前端
- React 18
- TypeScript
- Vite
- Zustand (状态管理)
- Tailwind CSS (样式)
- Recharts (图表)

## 开发进度

- [x] Phase 1: MCP Server 原子化 (2天)
- [x] Phase 2: 客户端基础框架 (3天)
- [x] Phase 3: React 前端开发 (3天)
- [ ] Phase 4: Skills 编写 (1天)
- [ ] Phase 5: 端到端测试 (1天)

## 文档

- [后端交接文档](../docs/phase2-3-handover.md)
- [前端完成报告](../docs/phase3-frontend-completion.md)
- [MCP 特性映射](../docs/mcp-features-mapping.md)
- [架构思路](../docs/架构思路.md)

## 环境要求

- Python 3.10+
- Node.js 18+
- Windows 10+ (推荐使用 Git Bash)

## 常见问题

### Q: WebSocket 连接失败？
A: 确保后端已启动在 8000 端口

### Q: 前端无法启动？
A: 运行 `npm install` 安装依赖

### Q: 如何调试？
A: 
- 后端: 查看控制台日志
- 前端: 打开浏览器 DevTools

## 下一步

1. 完成 Phase 4: 编写 Skills (interview-prep, tech-deep-dive, project-review)
2. 完成 Phase 5: 端到端测试
3. 部署到生产环境

## License

MIT
