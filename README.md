# Learning System - AI-Powered Learning Assistant

**AI驱动的学习成长系统** - 基于MCP 2026-07-28协议的Multi-Agent知识管理平台

![System Architecture](imgs/system-architecture.png)

## 项目概述

这是一个面向用户的学习应用，专为**技术学习**和**面试准备**设计。通过完整实现**MCP 2026-07-28协议**（MRTR、Tasks、Apps、Cache），结合**多智能体架构**和**知识图谱**，提供智能化、上下文感知的学习辅助。

### 核心价值

- **知识图谱可视化** - D3.js交互式图谱，探索概念间的关系
- **多智能体协作** - 6个专职Agent通过事件总线协同工作
- **MCP协议完整实现** - MRTR二次确认、长任务管理、UI组件返回、三层缓存
- **技能驱动工作流** - LLM基于Markdown技能文档动态编排原子工具
- **语义搜索** - PostgreSQL + pgvector实现向量检索
- **实时通信** - WebSocket双向聊天，延迟<100ms

## 为什么选择MCP？

MCP（Model Context Protocol）解决了AI应用的三大核心问题：

### 1. 上下文隔离
传统方式分析50个文件会污染主对话上下文10MB+，MCP通过Sub-Agent模式实现上下文隔离：
```
主Agent（干净上下文）
  -> 启动Sub-Agent（分析50个文件）
  -> 返回JSON结果（10KB）
  -> Sub-Agent上下文销毁
```

### 2. AI-First架构
**核心理念：服务端只提供原子能力，不包含业务逻辑**

```python
# 错误方式：硬编码工作流
@server.tool("track_project")
def track_project(path):
    framework = detect_framework()  # 步骤1
    structure = scan_structure()    # 步骤2
    # 工作流固定在代码中

# 正确方式：原子化工具 + Skill文档
@server.tool("project/detect_framework")  # 只做框架检测
@server.tool("project/scan_structure")    # 只做结构扫描

# 工作流由Skill markdown定义，LLM动态编排
```

**优势：**
- 工作流与实现分离（修改Skill文档即可调整流程）
- 可复用ECC生态的Skills和MCP Servers
- LLM根据用户需求灵活组合工具

### 3. MCP 2026四大特性

- **MRTR（多轮往返请求）** - 危险操作二次确认（JWT + Nonce防重放）
- **Tasks（长任务管理）** - 5-10分钟异步任务，支持进度追踪和取消
- **Apps（UI组件返回）** - 服务端返回可视化组件（知识图谱、分析报告）
- **Cache（三层缓存）** - public/user/session三级缓存，命中率60%+

## 技术架构

### 多智能体系统

6个专职Agent通过事件驱动总线协作：

| Agent | 职责 | 触发条件 |
|-------|------|---------|
| **SessionAnalyzer** | 从对话中提取知识点 | 会话结束、空闲60秒 |
| **MemoryManager** | 持久化到PostgreSQL知识图谱 | 知识保存事件 |
| **LearningCoach** | 生成间隔重复复习计划 | 会话结束、每日检查 |
| **ProjectAgent** | 追踪项目经验用于面试 | 项目分析请求 |
| **InterviewAgent** | 生成STAR格式面试材料 | 面试准备请求 |
| **ProjectAnalyzer** | 深度项目分析（Sub-Agent模式） | 工具调用 |

### 知识图谱

基于PostgreSQL + pgvector实现：
- **实体（Entities）** - 概念、技术、项目，带向量embeddings
- **关系（Relations）** - 语义关系（uses、implements、depends-on）
- **多图谱支持** - 前端、后端、面试准备独立图谱
- **语义搜索** - pgvector余弦相似度 + DeepSeek embeddings

### 技术栈

**前端**
- React 18.2 + TypeScript 5.2
- Vite 5.0（构建工具）
- Tailwind CSS 3.3（样式）
- Zustand 4.4（状态管理）
- D3.js 7.8（知识图谱可视化）
- Recharts 2.10（统计图表）

**后端**
- Python 3.x
- FastMCP 3.4.5（MCP协议实现）
- FastAPI 0.104（HTTP/WebSocket服务）
- asyncpg 0.29（PostgreSQL驱动）
- Redis 5.0（缓存层）
- DeepSeek API（LLM聊天 + embeddings）

**数据库**
- PostgreSQL with pgvector扩展
- Redis三层缓存

## 项目结构

```
learning-system/
├── client/
│   ├── backend/              # Python WebSocket服务器
│   │   ├── websocket_server.py   # WebSocket入口
│   │   ├── mcp_http_client.py    # MCP HTTP客户端
│   │   ├── skill_executor.py     # Skill执行引擎
│   │   ├── state.py              # 会话状态管理
│   │   └── task_manager.py       # 长任务管理
│   └── frontend/             # React + TypeScript UI
│       └── src/
│           ├── components/   # ChatInterface、KnowledgeGraphView等
│           ├── services/     # API客户端
│           └── stores/       # Zustand状态
├── mcp-server/              # MCP服务器实现
│   ├── server.py            # 主服务器（32个工具）
│   ├── http_server.py       # HTTP传输层（端口8080）
│   ├── config.py            # 配置
│   ├── src/
│   │   ├── agents/          # 6个专职Agent
│   │   ├── protocol/        # MCP协议层（MRTR、Tasks、Apps）
│   │   ├── storage/         # PostgreSQL + Memory MCP适配器
│   │   ├── tools/           # MCP工具实现
│   │   ├── cache/           # Redis缓存装饰器
│   │   └── llm/             # DeepSeek LLM集成
│   ├── migrations/          # 数据库Schema
│   └── skills/              # Skill定义（.md）
├── docs/                    # 文档
│   ├── mcp-features-mapping.md          # MCP 2026特性映射
│   ├── ARCHITECTURE_CORRECTION.md       # 架构决策
│   ├── learning-system-optimization-plan.md  # ECC启发设计
│   └── system-completion-plan.md        # 实现路线图
└── imgs/                    # 截图
```

## 快速开始

### 前置要求

- Python 3.9+
- Node.js 18+
- PostgreSQL 14+ with pgvector扩展
- Redis 5+

### 安装

1. **克隆仓库**
```bash
git clone <repository-url>
cd learning-system
```

2. **后端设置**
```bash
cd mcp-server
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env，配置PostgreSQL、Redis、DeepSeek API密钥

# 运行数据库迁移
psql -U postgres -d learning_system -f migrations/001_add_knowledge_graphs.sql
```

3. **前端设置**
```bash
cd client/frontend
npm install

# 配置环境变量
cp .env.example .env
# 编辑.env，配置WebSocket服务器URL
```

4. **启动服务**

终端1 - MCP服务器：
```bash
cd mcp-server
python http_server.py
# 运行在 http://localhost:8080
```

终端2 - WebSocket后端：
```bash
cd client/backend
python websocket_server.py
# 运行在 ws://localhost:8765
```

终端3 - 前端：
```bash
cd client/frontend
npm run dev
# 运行在 http://localhost:5173
```

### 快速启动脚本

```bash
# 使用提供的批处理脚本（Windows）
cd client
start.bat
```

## 使用方式

### 聊天界面

交互式提问和学习：
```
你："MCP 2026的核心特性是什么？"
AI："MCP 2026有四大核心特性：MRTR用于多轮确认..."
```

每次会话后，知识点自动提取并保存到图谱。

### 知识图谱可视化

- **查看** - 点击"显示知识图谱"可视化关系
- **交互** - 拖动节点、缩放/平移、点击查看详情
- **搜索** - 双击节点触发语义搜索

### 项目追踪

追踪项目用于面试准备：
```
你："分析E:/Desktop/learning-system项目"
AI：[使用Sub-Agent运行深度分析，保存到知识图谱]
```

系统提取：
- 技术栈（FastAPI、PostgreSQL、React）
- 框架模式
- 面试技术亮点

### 面试准备

生成STAR格式材料：
```
你："为learning-system项目准备面试材料"
AI：[生成项目介绍、技术亮点、常见问题]
```

## MCP工具（32个可用）

### 知识管理
- `save_knowledge` - 保存提取的知识点
- `search_knowledge` - 使用embeddings语义搜索
- `get_knowledge_graph` - 通过节点名检索图谱
- `ui_knowledge_graph` - 返回可视化UI组件
- `delete_knowledge` - 删除节点（需MRTR确认）

### 项目分析
- `track_project` - 追踪项目用于面试
- `analyze_project_deep` - 深度分析（长任务，5-10分钟）
- `delete_project` - 从图谱移除项目

### 学习
- `analyze_session` - 从对话提取知识
- `explore_technology` - 深入研究技术主题
- `research_technology_deep` - 全面研究（长任务）

### 文件操作
- `read_file`、`write_file`、`list_directory`、`search_files`、`get_file_info`

### 系统
- `get_cache_stats`、`invalidate_cache` - 缓存管理
- `tasks/get`、`tasks/list`、`tasks/cancel` - 长任务控制

## Skills系统

Skills以markdown格式定义工作流，LLM读取Skill并动态编排工具调用。

可用Skills：
- `codebase-onboarding.md` - 分析新代码库
- `interview-prep.md` - 生成面试材料
- `tech-deep-dive.md` - 6阶段学习路径
- `summarize-knowledge.md` - 提取关键概念
- `summarize.md` - 通用总结

Skills存储在`mcp-server/skills/`，运行时加载。

## 从ECC学到的设计理念

1. **AI-First架构** - 服务端提供原子工具，工作流用markdown定义
2. **Sub-Agent模式** - 在独立Agent中隔离上下文密集操作
3. **事件驱动多Agent** - 解耦的Agent通过事件总线通信
4. **Skill系统** - LLM编排的可复用工作流定义
5. **MCP协议** - AI-工具通信的标准化接口

## 面试谈资要点

讨论此项目时的技术亮点：

**技术特色：**
- 实现完整MCP 2026协议（MRTR、Tasks、Apps、Cache）
- 事件驱动的多智能体架构
- 知识图谱 + 语义搜索（PostgreSQL + pgvector）
- Sub-Agent模式实现上下文隔离
- 三层缓存策略（命中率60%+）

**为什么用MCP？**
"MCP解决了AI应用的上下文污染问题。传统方式将用户对话和文件分析混在一起，导致上下文不可读。MCP通过Sub-Agent隔离分析，返回干净的JSON结果。"

**为什么用多Agent？**
"每个Agent单一职责（SessionAnalyzer提取知识、MemoryManager持久化、LearningCoach生成复习计划）。它们通过事件通信，添加新Agent无需修改现有Agent。"

**为什么用知识图谱？**
"支持基于关系的学习。准备面试时，我可以查询'learning-system使用了哪些技术？'，得到FastAPI、PostgreSQL、MCP及其关系，而不是扁平列表。"

## 开发路线图

### 已完成（INT-1到INT-4）
- [x] PostgreSQL知识图谱集成
- [x] 32个工具的MCP服务器
- [x] 多Agent事件总线
- [x] WebSocket实时通信
- [x] D3.js图谱可视化
- [x] Skill执行引擎

### 进行中
- [ ] 知识图谱视觉增强（配色方案、节点大小）
- [ ] 统一设计令牌的设计系统
- [ ] 500+节点性能优化（WebGL目标）

### 计划中
- [ ] 高级图谱交互（右键菜单、多选）
- [ ] 侧边栏详情面板
- [ ] 完整interview-prep和tech-deep-dive工作流
- [ ] 前端动画系统
- [ ] 性能监控仪表板
- [ ] 跨页面刷新的会话持久化

## 配置

### MCP服务器（`mcp-server/config.py`）
```python
POSTGRES_HOST = "localhost"
POSTGRES_DB = "learning_system"
REDIS_HOST = "localhost"
DEEPSEEK_API_KEY = "your-api-key"
HTTP_SERVER_PORT = 8080
```

### 前端（`client/frontend/.env`）
```
VITE_WEBSOCKET_URL=ws://localhost:8765
```

## 许可证

MIT License - 详见LICENSE文件

## 致谢

- 设计模式灵感来自ECC（Embodied Coding Coach）生态系统
- MCP协议规范来自Anthropic
- 知识图谱概念来自Memory MCP

---

**构建技术**: FastMCP, FastAPI, React, PostgreSQL, D3.js, DeepSeek API  
**开发状态**: 🟢 生产就绪（核心功能完成）  
**面试重点**: MCP协议实现、多Agent架构、知识图谱语义搜索
