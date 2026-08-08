# Learning System - AI 使用指南

> 最后更新：2026-08-07

## 项目概述

基于 MCP 2026-07-28 协议的 AI 学习系统，通过知识图谱、会话分析和智能推荐帮助用户准备技术面试和学习新技能。

**核心特点：**
- 🌐 完整的前后端架构：React 前端 + FastAPI 后端 + WebSocket 实时通信
- 🧠 知识图谱存储：PostgreSQL + 向量化语义搜索
- 🔧 26+ 个 MCP 工具（含原子化项目分析工具）
- 📊 实时缓存管理和任务系统
- 🔄 三层降级策略：LocalKG → MCP Memory → Fallback

---

## 快速启动

### 方式一：一键启动（推荐）

```bash
cd E:\Desktop\learning-system
start-all.bat
```

这会启动：
- MCP HTTP Server (端口 8080)
- WebSocket Server (端口 8000)  
- React 前端 (端口 3000)

### 方式二：分步启动

**1. 启动 MCP HTTP Server**
```bash
cd mcp-server
python http_server.py
```

**2. 启动 WebSocket Server**
```bash
cd client\backend
python websocket_server.py
```

**3. 启动前端**
```bash
cd client\frontend
npm run dev
```

### 访问地址
- 前端界面：http://localhost:3000
- HTTP API：http://localhost:8080
- WebSocket：ws://localhost:8000/ws

---

## 核心工具列表（26 个）

### 知识管理工具
1. **search_knowledge** - 语义搜索知识图谱
2. **get_knowledge_graph** - 获取完整知识图谱
3. **save_knowledge** - 保存知识点到图谱
4. **delete_knowledge** - 删除知识点（需确认）
5. **ui_knowledge_graph** - 生成知识图谱可视化 UI
6. **knowledge/create_relation** - 创建知识节点关系

### 会话分析工具
7. **analyze_session** - 分析会话并提取知识点

### 项目分析工具（原子化）
8. **track_project** - 便捷入口（内部调用原子工具）
9. **project/detect_framework** - 检测项目框架
10. **project/scan_structure** - 扫描项目结构
11. **project/analyze_dependencies** - 分析依赖关系
12. **project/extract_patterns** - 提取代码模式
13. **project_analyze_status** - 项目分析状态
14. **delete_project** - 删除项目（需确认）

### 技术探索工具
15. **explore_technology** - 探索技术主题
16. **resource/query_docs** - 查询文档（Context7 MCP）
17. **resource/web_search** - 网络搜索（Exa MCP）

### 长任务工具（Tasks Extension）
18. **analyze_project_deep** - 深度项目分析（5-10分钟）
19. **vectorize_knowledge_graph** - 图谱向量化（3-5分钟）
20. **research_technology_deep** - 深度技术调研（8-12分钟）
21. **tasks/get** - 查询任务状态
22. **tasks/list** - 列出所有任务
23. **tasks/cancel** - 取消运行中的任务

### 缓存管理工具
24. **invalidate_cache** - 失效指定缓存
25. **cache_stats** - 获取缓存统计
26. **rebuild_index** - 重建搜索索引（需确认）

---

## API 调用示例

### 1. 列出所有工具

```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### 2. 搜索知识

```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":2,
    "method":"tools/call",
    "params":{
      "name":"search_knowledge",
      "arguments":{"query":"FastAPI"}
    }
  }'
```

### 3. 保存知识点

```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"save_knowledge",
      "arguments":{
        "knowledge_points":[
          {
            "title":"FastAPI 路由",
            "content":"使用装饰器定义路由"
          }
        ],
        "session_id":"session_001"
      }
    }
  }'
```

### 4. 启动长任务

```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":4,
    "method":"tools/call",
    "params":{
      "name":"analyze_project_deep",
      "arguments":{"project_path":"E:/Desktop/my-project"}
    }
  }'
```

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│                   http://localhost:3000                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ WebSocket
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              WebSocket Server (FastAPI)                     │
│                   ws://localhost:8000                       │
│  - 实时通信                                                  │
│  - Skill 执行引擎                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP JSON-RPC
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              MCP HTTP Server (FastAPI)                      │
│                 http://localhost:8080                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  HTTPTransport (协议层)                              │   │
│  │  - JSON-RPC 2.0 处理                                 │   │
│  │  - _meta 字段支持                                    │   │
│  │  - MRTR/Tasks 扩展                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MCPServer (核心)                                    │   │
│  │  - 26+ 工具注册                                      │   │
│  │  - 缓存装饰器                                        │   │
│  │  - 任务管理                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Agents (智能代理)                                   │   │
│  │  - SessionAnalyzer                                  │   │
│  │  - MemoryManager                                    │   │
│  │  - LearningCoach                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据存储层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │   Redis      │  │   Local KG   │      │
│  │ 知识图谱     │  │   缓存       │  │   向量存储   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 数据流向

**前端发问流程：**
```
1. 用户输入 → React App
2. WebSocket 发送 → WebSocket Server
3. HTTP 转发 → MCP HTTP Server
4. 工具执行 → search_knowledge
5. 三层查询 → LocalKG → MCP → Fallback
6. 缓存处理 → 添加 _meta 字段
7. 响应返回 → WebSocket → 前端展示
```

---

## MCP 2026 协议特性

### 1. 无状态核心 (Stateless Core)
- 每个请求独立，无 session ID
- 服务器不维护客户端状态
- 通过 JWT 传递状态（MRTR 场景）

### 2. MRTR (Multi-Round Trip Request)
用于需要用户二次确认的危险操作。

**流程：**
```
1. 客户端调用 delete_knowledge
2. 服务器返回 _meta.io.modelcontextprotocol/inputRequired
3. 客户端展示确认对话框
4. 用户确认后，携带 requestState (JWT) 再次调用
5. 服务器验证 JWT 并执行删除
```

**示例响应：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {},
  "_meta": {
    "io.modelcontextprotocol/inputRequired": {
      "message": "确认删除 3 个知识点？",
      "fields": [
        {"name": "confirm", "type": "boolean", "label": "确认删除"}
      ],
      "requestState": "eyJhbGc..."
    }
  }
}
```

### 3. Tasks Extension (长任务)
用于处理耗时 5-10 分钟的异步任务。

**工作流程：**
```
1. 调用 analyze_project_deep
2. 立即返回 taskHandle
3. 客户端轮询 tasks/get 查询状态
4. 任务完成后获取结果
```

**任务状态：**
- `pending` - 等待执行
- `running` - 执行中
- `completed` - 已完成
- `failed` - 失败
- `cancelled` - 已取消

### 4. MCP Apps (UI 模板)
服务器可返回 HTML 模板，由客户端渲染。

**示例：**
```json
{
  "_meta": {
    "io.modelcontextprotocol/uiTemplate": {
      "templateId": "knowledge-graph-viz",
      "templatePath": "/templates/graph.html",
      "data": {"nodes": [...], "edges": [...]}
    }
  }
}
```

### 5. 缓存元数据 (_meta)
每个响应可携带缓存指令。

**字段说明：**
- `ttlMs` - 缓存时长（毫秒）
- `cacheScope` - 缓存范围
  - `public` - 所有用户共享
  - `user` - 单个用户
  - `session` - 单次会话

**示例：**
```json
{
  "_meta": {
    "ttlMs": 3600000,
    "cacheScope": "user"
  }
}
```

---

## 项目文件结构

```
learning-system/
├── mcp-server/                 # MCP 服务端
│   ├── http_server.py         # HTTP 服务器入口
│   ├── server.py              # MCP Server 核心（工具注册）
│   ├── config.py              # 配置管理
│   ├── .env                   # 环境变量（需配置）
│   ├── requirements.txt       # Python 依赖
│   │
│   ├── src/
│   │   ├── protocol/          # MCP 协议层
│   │   │   ├── mcp_protocol.py      # MCPServer 类
│   │   │   ├── http_transport.py    # HTTP 传输层
│   │   │   ├── result_types.py      # 结果类型定义
│   │   │   └── transport.py         # Stdio 传输层
│   │   │
│   │   ├── agents/            # 智能代理
│   │   │   ├── session_analyzer.py  # 会话分析
│   │   │   ├── memory_manager.py    # 知识图谱管理
│   │   │   └── learning_coach.py    # 学习教练
│   │   │
│   │   ├── storage/           # 存储层
│   │   │   ├── postgres_knowledge_graph.py  # PostgreSQL 存储
│   │   │   ├── local_knowledge_graph.py     # 本地向量存储
│   │   │   └── mcp_memory_adapter.py        # MCP Memory 适配器
│   │   │
│   │   ├── cache/             # 缓存系统
│   │   │   ├── cache_manager.py      # 缓存管理器
│   │   │   └── cache_decorator.py    # 缓存装饰器
│   │   │
│   │   ├── tasks/             # 任务系统
│   │   │   └── task_manager.py
│   │   │
│   │   ├── tools/             # 工具实现
│   │   │   ├── ui_knowledge_graph.py
│   │   │   ├── file_explorer.py
│   │   │   └── pattern_matcher.py
│   │   │
│   │   ├── security/          # 安全组件
│   │   │   ├── jwt_handler.py
│   │   │   └── nonce_store.py
│   │   │
│   │   ├── triggers/          # 触发器
│   │   │   └── idle_detector.py
│   │   │
│   │   └── bus/               # 事件总线
│   │       └── agent_bus.py
│   │
│   ├── skills/                # Skill 定义
│   ├── templates/             # UI 模板
│   └── data/                  # 数据目录
│       ├── knowledge/         # 知识图谱数据
│       ├── sessions/          # 会话记录
│       └── projects/          # 项目分析结果
│
├── client/                    # 客户端
│   ├── backend/               # WebSocket 服务器
│   │   ├── websocket_server.py      # WebSocket 入口
│   │   ├── mcp_http_client.py       # MCP HTTP 客户端
│   │   ├── skill_manager.py         # Skill 管理
│   │   ├── skill_executor.py        # Skill 执行引擎
│   │   └── requirements.txt
│   │
│   └── frontend/              # React 前端
│       ├── src/
│       │   ├── App.tsx              # 主应用
│       │   ├── services/
│       │   │   ├── websocket.ts     # WebSocket 客户端
│       │   │   └── mcpClient.ts     # MCP 客户端
│       │   ├── components/          # React 组件
│       │   └── types/               # TypeScript 类型
│       ├── package.json
│       └── vite.config.ts
│
├── docs/                      # 文档
│   ├── AI-USAGE-GUIDE.md            # 本文档
│   ├── ARCHITECTURE_CORRECTION.md   # 架构说明
│   ├── system-completion-plan.md    # 开发计划
│   └── phase*-completion-report.md  # 阶段报告
│
├── start-all.bat              # 一键启动脚本
└── README.md                  # 项目说明
```

---

## 配置说明

### 环境变量配置

编辑 `mcp-server/.env` 文件：

```bash
# DeepSeek API (可选，用于 AI 会话分析)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 数据目录
DATA_DIR=./data

# 服务端口
HTTP_PORT=8080

# PostgreSQL (可选，用于知识图谱存储)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=learning_system
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
POSTGRES_ENABLED=true

# Redis (可选，用于分布式缓存)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_ENABLED=false
```

### 配置项说明

| 配置项 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEEPSEEK_API_KEY` | 否 | - | DeepSeek API key，不配置则使用 regex fallback |
| `DATA_DIR` | 否 | `./data` | 数据存储目录 |
| `HTTP_PORT` | 否 | `8080` | HTTP Server 端口 |
| `POSTGRES_ENABLED` | 否 | `true` | 是否启用 PostgreSQL |
| `REDIS_ENABLED` | 否 | `false` | 是否启用 Redis 缓存 |

### 存储降级策略

系统会自动根据配置进行降级：

```
PostgreSQL (推荐) 
  ↓ 如果未配置或连接失败
LocalKG (本地向量存储)
  ↓ 如果初始化失败  
Fallback (内存临时存储)
```

---

## 常见问题

**端口占用：**
```bash
netstat -ano | findstr :8080
taskkill /F /PID <PID>
```

**添加工具：**
```python
@server.tool("my_tool")
async def my_tool(param: str) -> MCPResult:
    return MCPResult(data={"result": "ok"})
```
