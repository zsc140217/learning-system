# Learning System 项目学习计划 - 面试导向

本学习计划专为面试准备设计，帮助你深入理解项目实现细节，能够清晰回答面试官的技术问题。

---

## 学习目标

通过本计划，你将能够：
1. **清晰解释**每个技术选型的原因（为什么用MCP、为什么用多Agent、为什么用知识图谱）
2. **详细描述**系统的数据流和交互流程
3. **深入理解**WebSocket、MCP协议、PostgreSQL知识图谱的实现
4. **准备好回答**常见面试问题和技术挑战
5. **展示**项目的技术亮点和复杂度

---

## 第一阶段：整体架构理解（核心概念）

### 任务1：理解系统三层架构

#### 学习内容
阅读文件：
- `docs/ARCHITECTURE_CORRECTION.md` - 架构设计决策
- `docs/mcp-features-mapping.md` - MCP协议特性
- `README.md` - 整体架构部分

#### 核心知识点

**1. 三层架构**
```
用户浏览器（前端React）
    ↕ WebSocket
WebSocket服务器（client/backend/websocket_server.py）
    ↕ HTTP
MCP服务器（mcp-server/server.py）
    ↕ asyncpg
PostgreSQL + Redis
```

**2. 为什么这样设计？**
- **前端 → WebSocket服务器**：实时双向通信，延迟<100ms
- **WebSocket → MCP服务器**：MCP协议标准化，解耦前端和AI逻辑
- **MCP → 数据库**：持久化知识图谱，支持语义搜索

**3. 数据流示例**
```
用户输入："MCP是什么？"
  ↓ WebSocket发送
WebSocket服务器接收 → 调用mcp.call_tool("chat", {message: "..."})
  ↓ HTTP请求
MCP服务器 → 调用DeepSeek LLM → 查询知识图谱 → 返回结果
  ↓ HTTP响应
WebSocket服务器 → WebSocket推送
  ↓
前端显示AI回复
```

#### 面试问题准备

**Q1: 为什么不直接前端调用MCP服务器？**
A: WebSocket服务器作为中间层有三个作用：
1. **状态管理**：维护会话状态、对话历史（MCP协议是无状态的）
2. **连接复用**：管理MCP客户端连接池，避免频繁建立HTTP连接
3. **实时推送**：支持长任务进度推送、知识提取确认等双向通信

**Q2: 为什么用WebSocket而不是HTTP轮询？**
A: 
1. 实时性更好（延迟<100ms vs 轮询间隔通常500ms+）
2. 减少网络开销（持久连接 vs 每次请求都要握手）
3. 支持服务端主动推送（长任务进度、MRTR确认请求）

**Q3: 系统的瓶颈在哪里？**
A: 
1. **LLM调用**：DeepSeek API响应时间2-5秒（最大瓶颈）
2. **PostgreSQL向量搜索**：500+节点时查询>200ms（计划用WebGL优化）
3. **WebSocket并发**：单进程最多支持1000个并发连接（可用Nginx负载均衡）

---

### 任务2：理解MCP协议的作用

#### 学习内容
阅读文件：
- `mcp-server/src/protocol/http_transport.py` - HTTP传输层
- `client/backend/mcp_http_client.py` - MCP客户端
- `docs/mcp-features-mapping.md` - MCP 2026特性

#### 核心知识点

**1. MCP协议是什么？**
Model Context Protocol - AI应用的标准化协议（类似HTTP之于Web）

**结构：**
```python
# 请求格式
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "save_knowledge",
        "arguments": {"knowledge_points": [...]}
    },
    "id": 1
}

# 响应格式
{
    "jsonrpc": "2.0",
    "result": {
        "content": [...],
        "isError": false
    },
    "id": 1
}
```

**2. MCP解决了什么问题？**

**问题1：上下文污染**
```
传统方式：
用户："分析这个项目"
AI读取50个文件（10MB） → 全部加载到对话上下文
用户看不到自己的消息，全是文件内容

MCP方式：
用户："分析这个项目"
AI调用MCP工具 → Sub-Agent独立分析50个文件
Sub-Agent返回JSON（10KB）→ 主对话上下文保持干净
```

**问题2：工作流硬编码**
```
错误：在server.py里写死流程
@server.tool("track_project")
def track_project(path):
    step1 = detect_framework()
    step2 = scan_structure()
    step3 = analyze_deps()
    # 修改流程要改代码

正确：原子化工具 + Skill文档
@server.tool("detect_framework")  # 原子能力
@server.tool("scan_structure")    # 原子能力

# 工作流在skills/track-project.md定义
# LLM读取Skill，自主决定调用顺序
```

**3. MCP 2026四大特性实现**

#### MRTR（多轮往返请求）
```python
# 第一轮：返回确认请求
return {
    "content": [...],
    "meta": {
        "io.modelcontextprotocol/inputRequired": {
            "requestState": jwt_token,  # 状态令牌
            "fields": [{"name": "confirm", "type": "boolean"}]
        }
    }
}

# 第二轮：验证JWT后执行
payload = verify_jwt(request_state)
if payload["nonce"] not in used_nonces:
    delete_knowledge()
```

**应用场景：**删除知识节点、删除项目、重建索引

#### Tasks（长任务管理）
```python
# 提交任务
task_id = task_manager.create_task(
    "深度项目分析",
    lambda: analyze_project_deep(path),
    eta_seconds=600
)

# 返回任务句柄
return {
    "content": [{
        "type": "resource",
        "resource": {
            "uri": f"task://{task_id}",
            "mimeType": "application/vnd.mcp.task"
        }
    }]
}

# 客户端轮询
while True:
    status = await mcp.call("tasks/get", {"task_id": task_id})
    if status["status"] == "completed":
        break
```

**应用场景：**深度项目分析（5-10分钟）、知识图谱向量化、深度技术调研

#### Apps（UI组件返回）
```python
# 返回可视化HTML
return {
    "content": [{
        "type": "resource",
        "resource": {
            "uri": "app://knowledge-graph-vis",
            "mimeType": "text/html",
            "text": vis_js_html
        }
    }]
}
```

**应用场景：**知识图谱可视化、项目分析报告

#### Cache（三层缓存）
```python
@cacheable(ttl_seconds=86400, scope="user")
@cacheable(ttl_seconds=3600, scope="public")
@cacheable(ttl_seconds=300, scope="session")
```

#### 面试问题准备

**Q1: MCP协议和HTTP有什么区别？**
A: 
- HTTP是通用协议，MCP是AI专用协议
- MCP内置了MRTR确认、长任务、UI返回、缓存等AI应用常见需求
- MCP支持工具调用的标准化描述（类似OpenAPI但专为LLM设计）

**Q2: 为什么不直接用HTTP实现这些功能？**
A: 可以用HTTP实现，但MCP提供了标准化：
1. **互操作性**：任何支持MCP的客户端都能调用你的服务器
2. **生态复用**：可以复用ECC生态的Skills和MCP Servers
3. **协议演进**：MCP协议持续更新，自动获得新特性

---

### 任务3：理解WebSocket通信机制

#### 学习内容
阅读文件：
- `client/backend/websocket_server.py` - WebSocket服务器
- `client/frontend/src/services/websocket.ts` - 前端WebSocket客户端

#### 核心知识点

**1. WebSocket消息格式**

前端 → 后端（请求）：
```typescript
{
    type: "chat",
    message: "MCP是什么？",
    sessionId: "sess-xxx"
}
```

后端 → 前端（响应）：
```typescript
{
    type: "message",
    role: "assistant",
    content: "MCP是...",
    timestamp: 1723123456789
}
```

**2. WebSocket连接生命周期**
```python
# 1. 建立连接
async def handle_connection(websocket):
    client_id = str(uuid.uuid4())
    clients[client_id] = websocket
    
# 2. 接收消息
async for message in websocket:
    data = json.loads(message)
    await handle_message(websocket, data)
    
# 3. 断开连接
finally:
    del clients[client_id]
```

**3. 为什么需要状态管理？**

MCP服务器是无状态的，但用户需要有状态的对话。WebSocket服务器负责：
- **会话管理**：维护session_id和对话历史
- **上下文传递**：每次调用MCP时传递session_id
- **连接池**：复用MCP HTTP连接

#### 面试问题准备

**Q1: WebSocket断开后如何恢复会话？**
A: 
1. 前端保存sessionId到localStorage
2. 重连时发送sessionId
3. 后端从Redis加载会话状态
4. 继续之前的对话

**Q2: 如何处理并发请求？**
A: 
1. 每个WebSocket连接独立处理（asyncio并发）
2. MCP客户端连接池（最多10个并发HTTP连接）
3. 任务队列处理长任务（避免阻塞）

---

## 第二阶段：核心组件深入（实现细节）

### 任务4：PostgreSQL知识图谱实现

#### 学习内容
阅读文件：
- `mcp-server/src/storage/postgres_knowledge_graph.py` - 知识图谱实现
- `mcp-server/migrations/001_add_knowledge_graphs.sql` - 数据库Schema
- `mcp-server/src/storage/mcp_memory_adapter.py` - Memory MCP适配器

#### 核心知识点

**1. 数据库Schema**
```sql
-- 知识图谱元数据
CREATE TABLE graphs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 实体节点
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    graph_id INTEGER REFERENCES graphs(id),
    name VARCHAR(255),
    entity_type VARCHAR(100),
    observations JSONB,           -- 知识点内容
    embedding vector(1536),       -- 向量embeddings
    created_at TIMESTAMP
);

-- 关系边
CREATE TABLE relations (
    id SERIAL PRIMARY KEY,
    graph_id INTEGER REFERENCES graphs(id),
    from_entity INTEGER REFERENCES entities(id),
    to_entity INTEGER REFERENCES entities(id),
    relation_type VARCHAR(100),
    created_at TIMESTAMP
);
```

**2. 为什么用PostgreSQL而不是Neo4j？**

面试高频问题！准备回答：

**A: 三个原因**
1. **向量搜索**：pgvector扩展支持embedding向量，Neo4j需要额外集成
2. **部署简单**：单一数据库，不需要维护两套系统
3. **成本考虑**：PostgreSQL免费，Neo4j企业版需付费

**权衡：**
- 图遍历性能：Neo4j更好（专业图数据库）
- 但本项目图谱规模小（<1000节点），PostgreSQL递归查询足够

**3. 向量搜索实现**
```python
# 生成embedding
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode("FastAPI")  # 返回1536维向量

# 余弦相似度搜索
query = """
SELECT e.*, e.embedding <=> $1::vector AS distance
FROM entities e
WHERE e.graph_id = $2
ORDER BY distance ASC
LIMIT 5
"""
results = await conn.fetch(query, embedding, graph_id)
```

**<=>操作符**：pgvector的余弦距离（0=完全相同，2=完全不同）

**4. 知识保存流程**
```
用户对话结束
  ↓
SessionAnalyzer提取知识点
  ↓
发布knowledge_extracted事件
  ↓
MemoryManager处理
  ↓
1. 生成embedding（DeepSeek API）
2. 去重检查（向量相似度>0.9视为重复）
3. INSERT到entities表
4. 自动建立关系（基于共现和语义相似度）
  ↓
保存到PostgreSQL
```

**5. 多图谱管理**
```python
# 场景：用户有多个学习领域
graphs = [
    {"id": 1, "name": "默认图谱"},
    {"id": 2, "name": "前端技术"},
    {"id": 3, "name": "后端技术"}
]

# 知识点关联图谱
await save_knowledge({
    "name": "React Hooks",
    "graph_id": 2  # 保存到前端技术图谱
})

# 跨图谱搜索
results = await search_across_graphs(
    query="React",
    graph_ids=[2, 3]  # 同时搜索前端和后端
)
```

#### 面试问题准备

**Q1: 如何保证embedding质量？**
A: 
1. 使用DeepSeek官方embedding模型（1536维）
2. 知识点预处理：提取关键词、去除停用词
3. 批量生成embedding（减少API调用）
4. 定期向量重建（模型更新后）

**Q2: 1000个节点时搜索性能如何？**
A: 
- **当前**：~200ms（未优化）
- **瓶颈**：PostgreSQL计算1000个向量距离
- **优化方案**：
  1. HNSW索引（pgvector支持）：降到50ms
  2. 分片图谱（按主题）：每个图谱<200节点
  3. Redis缓存热门查询

**Q3: 如何处理知识冲突？**
A: 
场景：同一概念有不同解释
解决：
1. 保存时间戳，保留最新版本
2. 支持多个observations（不同视角）
3. 关系标记置信度（0.0-1.0）

---

### 任务5：多Agent事件驱动架构

#### 学习内容
阅读文件：
- `mcp-server/src/agents/` - 6个Agent实现
- `mcp-server/server.py` - 事件总线初始化

#### 核心知识点

**1. 6个Agent的职责**

```python
# 1. SessionAnalyzer - 会话分析
@bus.subscribe("session.completed")
async def on_session_completed(event):
    # 提取知识点
    knowledge = await extract_knowledge(event["transcript"])
    await bus.publish("knowledge_extracted", knowledge)

# 2. MemoryManager - 知识管理
@bus.subscribe("knowledge_save_requested")
async def on_knowledge_save(event):
    # 保存到PostgreSQL
    await postgres.save_entities(event["knowledge_points"])

# 3. LearningCoach - 学习教练
@bus.subscribe("session.completed")
async def on_session_completed(event):
    # 生成复习计划（间隔重复算法）
    plan = generate_review_plan(event["topics"])
    await bus.publish("review_plan_generated", plan)

# 4. ProjectAgent - 项目管理
@bus.subscribe("project_track_requested")
async def on_project_track(event):
    # 提取技术栈、框架模式
    analysis = await analyze_project(event["path"])
    await postgres.save_project(analysis)

# 5. InterviewAgent - 面试助手
@bus.subscribe("interview_prep_requested")
async def on_interview_prep(event):
    # 生成STAR格式材料
    materials = await generate_interview_materials(event["project_id"])
    return materials

# 6. ProjectAnalyzer - 项目分析器（工具类）
# 不订阅事件，按需调用
analyzer = ProjectAnalyzer(project_path)
result = await analyzer.analyze(deep=True)
```

**2. 事件总线实现**
```python
class EventBus:
    def __init__(self):
        self.subscribers = {}  # {event_type: [handler1, handler2]}
    
    def subscribe(self, event_type):
        def decorator(handler):
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)
            return handler
        return decorator
    
    async def publish(self, event_type, data):
        if event_type in self.subscribers:
            # 并发执行所有订阅者
            tasks = [
                handler({"type": event_type, "data": data})
                for handler in self.subscribers[event_type]
            ]
            await asyncio.gather(*tasks)
```

**3. 为什么用事件驱动而不是直接调用？**

**直接调用的问题：**
```python
# 耦合度高
def on_session_end(transcript):
    knowledge = extract_knowledge(transcript)
    memory_manager.save(knowledge)  # 直接调用
    learning_coach.generate_plan(knowledge)  # 直接调用
    # 添加新功能要修改这里
```

**事件驱动的优势：**
```python
# 解耦
def on_session_end(transcript):
    bus.publish("session.completed", transcript)
    # 其他Agent自动响应，互不影响

# 添加新Agent无需修改现有代码
@bus.subscribe("session.completed")
async def new_agent_handler(event):
    # 新功能
```

**4. Sub-Agent模式（ProjectAnalyzer）**

**为什么ProjectAnalyzer不用事件总线？**

因为它需要**上下文隔离**：
```
问题：分析项目需要读50个文件（10MB）
如果在主Agent上下文：污染对话历史

解决：Sub-Agent模式
主Agent调用 → 启动独立DeepSeek进程
  ↓
Sub-Agent读取50个文件（独立上下文10MB）
  ↓
返回JSON结果（10KB）
  ↓
主Agent接收结果（上下文保持干净）
```

**实现：**
```python
class ProjectAnalyzer:
    def __init__(self, project_path):
        self.deepseek = DeepSeekClient()
        self.file_explorer = FileExplorer(project_path)
    
    async def analyze(self):
        # 1. 加载Skill文档
        skill = load_skill("project-deep-analyzer.md")
        
        # 2. 注册工具
        self.deepseek.register_tool("glob_files", self.file_explorer.glob)
        self.deepseek.register_tool("read_file", self.file_explorer.read)
        
        # 3. Sub-Agent自主执行（可能调用20次工具）
        result = await self.deepseek.chat_with_tools(
            prompt=f"{skill}\n\n分析: {self.project_path}",
            max_iterations=20
        )
        
        # 4. 返回结构化JSON
        return parse_analysis_result(result)
```

#### 面试问题准备

**Q1: 为什么不用消息队列（RabbitMQ、Kafka）？**
A: 
1. **规模小**：单机应用，不需要分布式消息队列
2. **实时性要求高**：内存事件总线延迟<1ms，消息队列>10ms
3. **简单性**：避免引入额外组件

**未来扩展**：如果需要分布式部署，可以将事件总线替换为Redis Pub/Sub

**Q2: Agent之间如何避免循环依赖？**
A: 
1. **单向事件流**：SessionAnalyzer → MemoryManager（不反向）
2. **事件命名规范**：`past_tense.completed`（已完成）而非`present_tense.trigger`（触发）
3. **禁止Agent之间直接调用**：只能通过事件通信

**Q3: 如何调试事件流？**
A: 
```python
# 事件日志中间件
@bus.subscribe("*")  # 订阅所有事件
async def event_logger(event):
    logger.info(f"Event: {event['type']}, Data: {event['data']}")
```

---

### 任务6：Skill系统工作原理

#### 学习内容
阅读文件：
- `mcp-server/skills/` - 5个Skill定义
- `client/backend/skill_manager.py` - Skill加载器
- `client/backend/skill_executor.py` - Skill执行引擎

#### 核心知识点

**1. Skill文档格式**

示例：`skills/interview-prep.md`
```markdown
# Interview Prep Skill

## 目标
为指定项目生成面试材料

## 输入
- project_id: 项目标识

## 工作流
### 第1步：查询项目信息
调用工具：get_knowledge_graph
参数：{"node_name": project_id}

### 第2步：提取技术栈
从返回结果中提取：
- 使用的框架
- 核心技术
- 架构模式

### 第3步：生成STAR材料
调用工具：generate_star_format
参数：{"project_info": ...}

## 输出
返回JSON：
{
    "project_intro": "...",
    "tech_highlights": [...],
    "common_questions": [...]
}
```

**2. Skill执行流程**
```
用户请求："为learning-system准备面试材料"
  ↓
SkillManager匹配Skill（interview-prep.md）
  ↓
SkillExecutor解析Skill文档
  ↓
LLM读取Skill → 理解工作流 → 自主决策
  ↓
调用工具1：get_knowledge_graph(node_name="learning-system")
  ↓
调用工具2：generate_star_format(project_info=...)
  ↓
返回结构化结果
```

**3. 为什么Skill用Markdown而不是代码？**

**优势：**
1. **灵活性**：LLM可以根据实际情况调整步骤顺序
2. **可维护性**：非技术人员也能编辑Skill
3. **可复用**：ECC生态有281个Skill可直接使用

**示例对比：**
```python
# 硬编码方式：步骤固定
def interview_prep(project_id):
    info = get_knowledge_graph(project_id)  # 必须先执行
    star = generate_star(info)              # 然后执行
    return star

# Skill方式：LLM自主决策
# 如果知识图谱里没有项目信息，LLM可以先调用track_project
# 如果用户只要技术栈，可以跳过STAR生成
```

**4. Skill的5个阶段模式**

典型Skill结构（参考ECC）：
```
阶段1：理解需求（Understand）
阶段2：收集信息（Gather）
阶段3：分析处理（Analyze）
阶段4：生成结果（Generate）
阶段5：验证优化（Verify）
```

#### 面试问题准备

**Q1: Skill和工具（Tool）有什么区别？**
A: 
- **Tool**：原子能力（read_file、save_knowledge）
- **Skill**：工作流（如何组合多个Tool完成任务）

类比：
- Tool = 函数
- Skill = 算法流程图

**Q2: 如何保证LLM按Skill执行？**
A: 
1. **明确的步骤编号**：第1步、第2步（引导顺序）
2. **工具名称和参数说明**：减少LLM猜测
3. **示例输出**：让LLM知道预期结果格式
4. **验证机制**：检查LLM是否调用了必需的工具

**Q3: Skill可以嵌套吗？**
A: 
可以！示例：
```markdown
### 第3步：深度技术调研
调用Skill：tech-deep-dive
参数：{"technology": "FastAPI"}
```

---

## 第三阶段：前端实现（用户界面）

### 任务7：React前端架构

#### 学习内容
阅读文件：
- `client/frontend/src/App.tsx` - 应用入口
- `client/frontend/src/store/appStore.ts` - Zustand状态管理
- `client/frontend/src/services/websocket.ts` - WebSocket客户端

#### 核心知识点

**1. 前端技术栈选择理由**

| 技术 | 作用 | 为什么选它？ |
|------|------|-------------|
| React 18.2 | UI框架 | 虚拟DOM性能好、生态丰富 |
| TypeScript | 类型系统 | 编译时发现错误、提升代码质量 |
| Zustand | 状态管理 | 轻量级（比Redux简单）、性能好 |
| Tailwind CSS | 样式 | 原子化CSS、开发速度快 |
| D3.js | 图谱可视化 | 数据驱动、灵活性高 |
| Vite | 构建工具 | 启动快（HMR<50ms）、ES模块原生支持 |

**2. Zustand状态管理**
```typescript
interface AppState {
    // 会话状态
    sessionId: string
    messages: Message[]
    
    // WebSocket连接
    ws: WebSocket | null
    isConnected: boolean
    
    // UI状态
    showKnowledgeGraph: boolean
    currentTask: Task | null
    
    // Actions
    sendMessage: (content: string) => void
    connectWebSocket: () => void
}

const useAppStore = create<AppState>((set, get) => ({
    sessionId: generateSessionId(),
    messages: [],
    ws: null,
    isConnected: false,
    
    sendMessage: (content) => {
        const { ws, sessionId } = get()
        ws?.send(JSON.stringify({
            type: 'chat',
            message: content,
            sessionId
        }))
    }
}))
```

**为什么用Zustand而不是Redux？**
- Redux：需要actions、reducers、middleware（代码量3倍）
- Zustand：直接在store里定义actions（代码简洁）

**3. WebSocket客户端实现**
```typescript
class WebSocketClient {
    connect() {
        this.ws = new WebSocket('ws://localhost:8765')
        
        this.ws.onopen = () => {
            console.log('Connected')
            useAppStore.setState({ isConnected: true })
        }
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            this.handleMessage(data)
        }
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error)
            this.reconnect()
        }
    }
    
    reconnect() {
        setTimeout(() => this.connect(), 3000)
    }
}
```

**4. 组件结构**
```
App.tsx (根组件)
├── Header (顶部导航)
├── ChatInterface (聊天界面)
│   ├── MessageList (消息列表)
│   └── InputBox (输入框)
├── KnowledgeGraphView (知识图谱)
│   ├── D3ForceGraph (D3可视化)
│   └── NodeDetails (节点详情)
├── TaskProgress (任务进度)
└── ConfirmDialog (确认弹窗)
```

#### 面试问题准备

**Q1: 为什么不用Vue或Angular？**
A: 
- React生态最成熟（D3.js集成方案多）
- TypeScript支持最好
- 个人最熟悉（开发效率高）

**Q2: 如何优化首屏加载速度？**
A: 
1. **代码分割**：路由懒加载（React.lazy）
2. **图片优化**：WebP格式、懒加载
3. **Tree Shaking**：移除未使用的代码
4. **CDN**：静态资源使用CDN

当前首屏加载：~1.5秒（未优化）
优化后目标：<800ms

**Q3: 如何处理WebSocket断线重连？**
A: 
```typescript
reconnect() {
    this.retryCount++
    const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000)
    setTimeout(() => this.connect(), delay)
}
```
指数退避策略：1s → 2s → 4s → 8s → 最多30s

---

### 任务8：D3.js知识图谱可视化

#### 学习内容
阅读文件：
- `client/frontend/src/components/KnowledgeGraph/KnowledgeGraphView.tsx` - D3图谱组件

#### 核心知识点

**1. D3.js力导向图原理**
```typescript
// 创建力模拟
const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
        .id(d => d.id)
        .distance(100))                    // 边长度
    .force("charge", d3.forceManyBody()
        .strength(-300))                   // 节点斥力
    .force("center", d3.forceCenter(
        width / 2, height / 2))            // 居中
    .force("collision", d3.forceCollide()
        .radius(30))                       // 防重叠

// 每次tick更新位置
simulation.on("tick", () => {
    nodes.forEach(node => {
        node.x = Math.max(30, Math.min(width - 30, node.x))
        node.y = Math.max(30, Math.min(height - 30, node.y))
    })
    updateVisualization()
})
```

**2. 交互功能实现**

**拖动节点：**
```typescript
function handleDrag(event, d) {
    d.fx = event.x  // 固定x坐标
    d.fy = event.y  // 固定y坐标
    simulation.alpha(0.3).restart()  // 重新开始模拟
}

function handleDragEnd(event, d) {
    d.fx = null  // 释放固定
    d.fy = null
}
```

**缩放平移：**
```typescript
const zoom = d3.zoom()
    .scaleExtent([0.1, 10])  // 缩放范围
    .on("zoom", (event) => {
        g.attr("transform", event.transform)
    })

svg.call(zoom)
```

**点击节点查看详情：**
```typescript
nodeElements.on("click", (event, d) => {
    setSelectedNode(d)
    // 高亮相关节点
    highlightConnectedNodes(d.id)
})
```

**双击节点触发搜索：**
```typescript
nodeElements.on("dblclick", (event, d) => {
    // 防止缩放
    event.stopPropagation()
    // 触发语义搜索
    searchRelatedKnowledge(d.name)
})
```

**3. 性能优化**

**问题：500个节点时卡顿**
```typescript
// 优化1：降低模拟精度
simulation.alphaDecay(0.05)  // 加快收敛

// 优化2：限制渲染帧率
let lastRender = 0
simulation.on("tick", () => {
    const now = Date.now()
    if (now - lastRender < 16) return  // 60fps
    lastRender = now
    updateVisualization()
})

// 优化3：Canvas渲染（替代SVG）
// 计划：500+节点时切换到WebGL
```

**4. 节点样式设计**
```typescript
// 节点大小：根据连接数
const nodeRadius = d => Math.sqrt(d.connections) * 5 + 10

// 节点颜色：根据类型
const nodeColor = d => {
    if (d.type === 'project') return '#3b82f6'      // 蓝色
    if (d.type === 'technology') return '#10b981'   // 绿色
    if (d.type === 'concept') return '#f59e0b'      // 橙色
    return '#6b7280'                                // 灰色
}

// 边粗细：根据关系强度
const linkWidth = d => d.strength * 2
```

#### 面试问题准备

**Q1: 为什么用D3.js而不是ECharts或vis.js？**
A: 
- **D3.js**：灵活性最高，可以完全自定义
- **ECharts**：配置式，自定义受限
- **vis.js**：功能全面但性能较差

选择D3.js因为需要高度定制化的交互

**Q2: 如何优化大规模图谱（1000+节点）？**
A: 
1. **按需加载**：只显示2层关系，点击展开更多
2. **聚合显示**：相似节点聚合成簇
3. **WebGL渲染**：Canvas无法处理1000+节点
4. **虚拟化**：只渲染可见区域的节点

**Q3: 图谱布局算法有哪些？**
A: 
- **力导向**（当前使用）：自动布局，适合中小规模
- **层次布局**：树状结构，适合知识体系
- **圆形布局**：环形排列，适合关系对称的图
- **网格布局**：规则排列，适合分类展示

---

## 第四阶段：技术深入（核心难点）

### 任务9：异步编程和并发控制

#### 学习内容
阅读文件：
- `mcp-server/server.py` - 异步工具注册
- `client/backend/websocket_server.py` - asyncio并发

#### 核心知识点

**1. Python asyncio基础**
```python
# 同步代码（阻塞）
def fetch_data():
    time.sleep(2)  # 阻塞2秒
    return "data"

result = fetch_data()  # 总共2秒

# 异步代码（非阻塞）
async def fetch_data_async():
    await asyncio.sleep(2)  # 协程切换
    return "data"

result = await fetch_data_async()  # 其他协程可以执行
```

**2. 并发调用多个工具**
```python
# 错误：串行执行（慢）
result1 = await call_tool("tool1")
result2 = await call_tool("tool2")
result3 = await call_tool("tool3")
# 总时间：t1 + t2 + t3

# 正确：并发执行（快）
results = await asyncio.gather(
    call_tool("tool1"),
    call_tool("tool2"),
    call_tool("tool3")
)
# 总时间：max(t1, t2, t3)
```

**3. 连接池管理**
```python
class MCPClientPool:
    def __init__(self, max_size=10):
        self.pool = asyncio.Queue(maxsize=max_size)
        for _ in range(max_size):
            client = MCPHttpClient("http://localhost:8080")
            self.pool.put_nowait(client)
    
    async def acquire(self):
        return await self.pool.get()
    
    async def release(self, client):
        await self.pool.put(client)
    
    async def call_tool(self, name, args):
        client = await self.acquire()
        try:
            result = await client.call_tool(name, args)
            return result
        finally:
            await self.release(client)
```

**为什么需要连接池？**
- 避免频繁建立HTTP连接（握手开销）
- 限制并发数（防止打爆MCP服务器）

**4. 超时处理**
```python
async def call_tool_with_timeout(name, args, timeout=30):
    try:
        result = await asyncio.wait_for(
            mcp.call_tool(name, args),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Tool {name} timeout after {timeout}s")
        return {"error": "timeout"}
```

#### 面试问题准备

**Q1: asyncio和多线程有什么区别？**
A: 
- **asyncio**：单线程、协程切换、适合I/O密集型
- **多线程**：多线程、抢占式、适合CPU密集型

本项目用asyncio因为：
1. 大量网络I/O（HTTP、WebSocket、PostgreSQL）
2. GIL限制了多线程性能
3. 协程切换开销小

**Q2: 如何调试异步代码？**
A: 
```python
# 1. 打印协程栈
import asyncio
tasks = asyncio.all_tasks()
for task in tasks:
    print(task.get_stack())

# 2. 检测阻塞调用
loop = asyncio.get_event_loop()
loop.set_debug(True)  # 警告阻塞>100ms的调用

# 3. 使用async-timeout
async with asyncio.timeout(5):
    await slow_operation()
```

**Q3: 如何处理并发写入PostgreSQL？**
A: 
```python
# 使用连接池
pool = await asyncpg.create_pool(
    dsn="postgresql://...",
    min_size=5,
    max_size=20
)

# 并发写入（连接池自动管理）
await asyncio.gather(
    pool.execute("INSERT ..."),
    pool.execute("INSERT ..."),
    pool.execute("INSERT ...")
)
```

---

### 任务10：缓存策略和性能优化

#### 学习内容
阅读文件：
- `mcp-server/src/cache/cache_decorator.py` - 缓存装饰器
- `mcp-server/src/cache/cache_manager.py` - Redis缓存管理

#### 核心知识点

**1. 三层缓存架构**
```
请求 → L1: 内存缓存（LRU，容量1000条）
  ↓ miss
     → L2: Redis缓存（TTL可配置）
       ↓ miss
          → L3: PostgreSQL数据库
```

**2. 缓存装饰器实现**
```python
def cacheable(ttl_seconds=3600, scope="public"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存key
            cache_key = f"{scope}:{func.__name__}:{hash_args(args, kwargs)}"
            
            # 尝试从缓存获取
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 保存到缓存
            await redis.setex(cache_key, ttl_seconds, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# 使用示例
@cacheable(ttl_seconds=86400, scope="user")
async def get_project_analysis(project_id):
    return await postgres.query(...)
```

**3. 缓存失效策略**
```python
# 主动失效
@server.tool("save_knowledge")
async def save_knowledge(knowledge_points):
    await postgres.save(knowledge_points)
    # 清除相关缓存
    await cache.invalidate_pattern("search_knowledge:*")

# 被动失效（TTL过期）
# public级：1小时（技术文档不常变）
# user级：1天（用户项目分析结果）
# session级：5分钟（会话临时数据）
```

**4. 缓存命中率监控**
```python
class CacheStats:
    def __init__(self):
        self.hits = 0
        self.misses = 0
    
    @property
    def hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0

# 工具暴露统计
@server.tool("get_cache_stats")
async def get_cache_stats():
    return {
        "hit_rate": cache.stats.hit_rate,
        "total_keys": await redis.dbsize()
    }
```

**当前缓存命中率：60%+**

#### 面试问题准备

**Q1: 如何避免缓存雪崩？**
A: 
- **问题**：大量缓存同时过期，瞬间打爆数据库
- **解决**：
  1. TTL随机化：86400 + random(0, 3600)
  2. 热点数据永不过期（手动更新）
  3. 请求限流（令牌桶算法）

**Q2: 如何处理缓存穿透？**
A: 
- **问题**：查询不存在的数据，每次都打数据库
- **解决**：
  ```python
  # 缓存空结果
  if result is None:
      await redis.setex(cache_key, 60, "null")
  ```

**Q3: Redis和Memcached选哪个？**
A: 选Redis因为：
1. 支持更多数据结构（Hash、Set、Sorted Set）
2. 持久化支持（RDB、AOF）
3. 发布订阅（可用于事件总线扩展）

---

## 第五阶段：面试准备（实战演练）

### 任务11：技术亮点提炼

#### 核心卖点（面试必讲）

**1. MCP协议完整实现**
```
面试官："你这个项目用了什么协议？"

你的回答：
"我完整实现了MCP 2026协议的四大特性：
1. MRTR多轮确认：删除知识节点时用JWT+Nonce防重放攻击
2. Tasks长任务：深度项目分析5-10分钟，支持进度追踪和取消
3. Apps UI返回：知识图谱可视化直接从服务端返回HTML组件
4. Cache三层缓存：public/user/session三级，命中率60%+

这解决了传统AI应用的上下文污染问题，通过Sub-Agent模式
将10MB的文件分析隔离到独立上下文，返回10KB的JSON结果。"
```

**2. 多Agent事件驱动架构**
```
面试官："你的多Agent是怎么实现的？"

你的回答：
"我设计了6个专职Agent通过事件总线协作：
- SessionAnalyzer提取知识点
- MemoryManager持久化到PostgreSQL
- LearningCoach生成复习计划
- ProjectAgent追踪项目经验
- InterviewAgent生成面试材料
- ProjectAnalyzer深度分析（Sub-Agent模式）

优势是解耦，添加新Agent不需要修改现有代码。
而且通过异步事件并发处理，SessionAnalyzer和LearningCoach
可以同时响应session.completed事件，提升性能。"
```

**3. 知识图谱语义搜索**
```
面试官："为什么用PostgreSQL而不是Neo4j？"

你的回答：
"三个原因：
1. pgvector扩展支持1536维向量，DeepSeek embeddings可以直接存储
2. 部署简单，单一数据库，不需要维护两套系统
3. 成本考虑，PostgreSQL免费，Neo4j企业版需要付费

权衡是图遍历性能不如Neo4j，但我们的图谱规模<1000节点，
PostgreSQL递归查询足够。而且通过HNSW索引优化，
向量搜索从200ms降到50ms。"
```

**4. AI-First架构设计**
```
面试官："什么是AI-First架构？"

你的回答：
"核心理念是服务端只提供原子化工具，不包含业务逻辑。
工作流由Skill markdown文档定义，LLM读取后自主编排。

比如项目分析：
- 错误方式：在代码里写死 detect_framework() → scan_structure()
- 正确方式：提供原子工具，Skill文档描述流程，LLM动态决策

好处是工作流与实现分离，修改Skill文档就能调整流程，
而且可以复用ECC生态的Skills和MCP Servers。"
```

---

### 任务12：常见面试问题速查表

#### 架构设计类

**Q1: 为什么分成三层（前端、WebSocket、MCP）？**
A: 
- **前端**：用户界面，React + D3.js
- **WebSocket服务器**：状态管理（MCP无状态需要中间层）、连接复用、实时推送
- **MCP服务器**：AI逻辑、工具编排、数据持久化

**Q2: 系统的性能瓶颈在哪？如何优化？**
A: 
1. **LLM调用**（2-5秒）- 最大瓶颈
   - 优化：缓存常见查询、批量请求
2. **PostgreSQL向量搜索**（200ms）
   - 优化：HNSW索引、图谱分片
3. **WebSocket并发**（1000连接限制）
   - 优化：Nginx负载均衡、水平扩展

**Q3: 如果用户量暴增10倍怎么办？**
A: 
1. **MCP服务器**：水平扩展（无状态，易扩展）
2. **PostgreSQL**：读写分离、分库分表
3. **Redis**：集群模式
4. **WebSocket**：Nginx负载均衡

---

#### 技术选型类

**Q1: 为什么用FastAPI而不是Flask？**
A: 
- 原生异步支持（Flask需要额外配置）
- 自动生成OpenAPI文档
- Pydantic数据验证（类型安全）
- 性能更好（uvicorn ASGI）

**Q2: 为什么用Zustand而不是Redux？**
A: 
- 代码量少（1/3的代码实现同样功能）
- 学习成本低（不需要理解actions、reducers、middleware）
- 性能好（组件级别的精确更新）

**Q3: 为什么用D3.js而不是ECharts？**
A: 
- 灵活性高（完全自定义交互）
- 适合知识图谱（力导向布局算法）
- ECharts配置式，难以实现复杂交互

---

#### 实现细节类

**Q1: WebSocket断线重连怎么做的？**
A: 
```typescript
reconnect() {
    this.retryCount++
    const delay = Math.min(
        1000 * Math.pow(2, this.retryCount), 
        30000
    )
    setTimeout(() => this.connect(), delay)
}
```
指数退避：1s → 2s → 4s → 8s → 最多30s

**Q2: 如何保证JWT安全？**
A: 
1. 短过期时间（5分钟）
2. Nonce防重放（每个token只能用一次）
3. HTTPS传输
4. 敏感操作（删除）才用JWT

**Q3: 向量搜索的原理是什么？**
A: 
1. 文本 → embedding（DeepSeek API）→ 1536维向量
2. 存储到PostgreSQL（pgvector）
3. 查询时计算余弦相似度：`embedding <=> query_vector`
4. 返回距离最小的Top 5

---

#### 挑战和解决类

**Q1: 遇到的最大技术挑战是什么？**
A: 
**挑战**：MCP协议是无状态的，但用户需要有状态的对话

**解决**：
1. WebSocket服务器维护会话状态（session_id、历史消息）
2. 每次调用MCP时显式传递session_id
3. Redis缓存会话数据（TTL=300秒）
4. 三层标签系统隔离数据（project/session/user）

**Q2: 如何调试事件驱动的多Agent？**
A: 
1. 事件日志中间件（订阅所有事件）
2. 调用链追踪（traceId贯穿整个流程）
3. 单元测试每个Agent的handler
4. 集成测试完整事件流

**Q3: D3.js性能问题怎么解决的？**
A: 
1. 降低模拟精度（alphaDecay=0.05）
2. 限制渲染帧率（60fps，16ms一帧）
3. Canvas替代SVG（500+节点）
4. 按需加载（只显示2层关系）

---

### 任务13：STAR面试话术准备

#### STAR格式：Situation → Task → Action → Result

**示例1：MCP协议实现**

**Situation（情境）**
"在学习AI应用开发时，我发现传统方式有个严重问题：
AI分析项目时需要读取大量文件，这些内容会污染用户的对话上下文，
用户看不到自己发的消息，全是文件内容。"

**Task（任务）**
"我的目标是实现一个学习助手，既能深度分析项目，
又能保持对话上下文的干净。"

**Action（行动）**
"我采用了MCP 2026协议的Sub-Agent模式：
1. 研究了MCP协议规范和ECC生态的实现方式
2. 设计了三层架构：前端、WebSocket服务器、MCP服务器
3. 实现了MRTR、Tasks、Apps、Cache四大特性
4. 用ProjectAnalyzer作为Sub-Agent，在独立上下文中分析项目"

**Result（结果）**
"最终实现了上下文隔离：
- 分析50个文件（10MB）只返回10KB的JSON结果
- 主对话上下文保持干净，用户体验大幅提升
- 而且通过缓存优化，相同项目的分析从5分钟降到<1秒"

---

**示例2：多Agent架构设计**

**Situation**
"项目初期，我把所有逻辑都写在一个server.py文件里，
导致代码耦合严重，添加新功能要改很多地方。"

**Task**
"需要重构成可扩展的架构，新增功能时不影响现有代码。"

**Action**
"我设计了事件驱动的多Agent架构：
1. 将功能按职责拆分成6个专职Agent
2. 实现了事件总线，Agent之间通过事件通信
3. 每个Agent只订阅自己关心的事件
4. 确保单向事件流，避免循环依赖"

**Result**
"现在添加新功能非常简单：
- 新增一个Agent，订阅相关事件，不需要修改现有代码
- 而且并发性能提升，SessionAnalyzer和LearningCoach
  可以同时响应同一个事件，总耗时从串行的5秒降到并行的3秒"

---

**示例3：知识图谱优化**

**Situation**
"知识图谱最初用的是JSON文件存储，当节点超过200个时，
搜索一次需要2秒，用户体验很差。"

**Task**
"需要优化搜索性能，目标是<200ms。"

**Action**
"我做了三方面优化：
1. 迁移到PostgreSQL + pgvector，用向量相似度搜索
2. 添加HNSW索引，加速向量查询
3. 实现三层缓存（内存LRU + Redis + PostgreSQL）
4. 前端只加载2层关系，点击展开更多"

**Result**
"搜索性能从2000ms优化到50ms（40倍提升）：
- 向量索引贡献：2000ms → 200ms
- Redis缓存贡献：200ms → 50ms（60%命中率）
- 用户体验显著改善，搜索响应几乎是即时的"

---

### 任务14：面试实战模拟问答

#### 开场介绍（30秒电梯演讲）

"这是一个AI驱动的学习助手，帮助我准备技术面试。
核心特色有三点：

第一，完整实现了MCP 2026协议，通过Sub-Agent模式解决了
AI应用的上下文污染问题。

第二，事件驱动的多Agent架构，6个专职Agent协作，
可扩展性强。

第三，基于PostgreSQL + pgvector的知识图谱，支持语义搜索，
可以从对话中自动提取知识点并建立关系。

技术栈是Python FastAPI后端，React + D3.js前端，
WebSocket实时通信，目前已实现32个MCP工具和5个Skill工作流。"

---

#### 深挖问题应对

**面试官："你说的上下文污染具体是什么问题？"**

"传统AI应用，当用户说'分析这个项目'时，AI会直接读取
所有文件内容到对话上下文。比如一个项目有50个文件，
每个200KB，总共10MB的内容全部加载到上下文。

这导致两个问题：
1. 用户看不到自己的消息，全是文件内容
2. 超过上下文窗口限制，对话会中断

我用MCP的Sub-Agent模式解决：启动一个独立的Agent，
在单独的上下文中分析文件，然后只返回提取的JSON结果，
大约10KB。这样主对话上下文保持干净。"

---

**面试官："为什么要自己实现MCP协议，而不是直接用现成的库？"**

"其实我用了FastMCP库作为基础，但MCP 2026的四大特性
（MRTR、Tasks、Apps、Cache）FastMCP只提供了基础支持，
需要自己实现业务逻辑。

比如MRTR的JWT验证、Nonce防重放，这些安全机制需要自己设计。
Tasks的进度追踪、取消机制也需要自己实现。
Apps的UI组件渲染需要和前端配合。

所以'实现MCP协议'指的是完整实现这四大特性，
而不是从零写JSON-RPC协议。"

---

**面试官："你的项目有多少用户？性能怎么样？"**

"这是个人学习项目，目前只有我自己使用，
但我在设计时考虑了可扩展性：

性能指标：
- WebSocket延迟：<100ms
- 知识图谱搜索：<50ms（有缓存）
- LLM响应：2-5秒（DeepSeek API）
- 单机并发：支持1000个WebSocket连接

可扩展性：
- MCP服务器无状态，可以水平扩展
- PostgreSQL支持读写分离
- Redis支持集群模式
- WebSocket通过Nginx负载均衡

如果用户量暴增，可以快速扩展到分布式架构。"

---

#### 项目不足和改进（展示思考深度）

**面试官："你觉得这个项目有什么不足？"**

"有几个方面可以改进：

1. **测试覆盖率不够**
   目前只有少量单元测试，缺乏集成测试和E2E测试。
   计划补充到80%覆盖率。

2. **监控和日志**
   没有完善的监控系统，只有基本的日志。
   计划集成Prometheus + Grafana。

3. **安全性**
   目前没有用户认证，任何人都能连接WebSocket。
   计划添加JWT认证和RBAC权限控制。

4. **前端性能**
   500+节点的知识图谱会卡顿，需要优化到WebGL渲染。

5. **错误恢复**
   LLM调用失败时没有重试机制，用户体验不好。
   计划添加指数退避重试。

这些是我下一步的优化方向。"

---

## 学习计划总结

### 学习路径建议

**第1周：理解整体**
- 任务1-3：架构理解、MCP协议、WebSocket通信
- 目标：能画出系统架构图，讲清楚数据流

**第2周：核心组件**
- 任务4-6：知识图谱、多Agent、Skill系统
- 目标：理解每个组件的实现原理和交互方式

**第3周：技术深入**
- 任务7-10：前端实现、D3.js、异步编程、缓存优化
- 目标：掌握技术细节，能回答深挖问题

**第4周：面试准备**
- 任务11-14：技术亮点、问题速查、STAR话术、模拟问答
- 目标：流畅表达项目价值，准备好所有常见问题

---

### 检验标准

**你应该能够回答以下问题：**

1. ✓ 为什么用MCP协议？解决了什么问题？
2. ✓ 三层架构的每一层作用是什么？
3. ✓ MCP 2026四大特性如何实现？
4. ✓ 多Agent如何协作？为什么用事件驱动？
5. ✓ 知识图谱为什么用PostgreSQL而不是Neo4j？
6. ✓ 向量搜索的原理是什么？
7. ✓ WebSocket断线重连机制？
8. ✓ D3.js力导向图的性能优化？
9. ✓ 异步编程的并发控制？
10. ✓ 三层缓存策略？

**你应该能够演示：**

1. ✓ 画出系统架构图（3分钟）
2. ✓ 讲解完整的用户请求流程（5分钟）
3. ✓ 展示知识图谱可视化效果
4. ✓ 用STAR格式讲述技术挑战

---

### 推荐学习资源

**MCP协议**
- MCP官方文档：https://modelcontextprotocol.io
- FastMCP库：https://github.com/jlowin/fastmcp

**异步编程**
- Python asyncio官方文档
- 《Fluent Python》第21章（协程和异步）

**知识图谱**
- pgvector文档：https://github.com/pgvector/pgvector
- 《图算法》- O'Reilly

**D3.js**
- D3.js官方文档：https://d3js.org
- Observable示例：https://observablehq.com/@d3

**系统设计**
- 《Designing Data-Intensive Applications》
- 《System Design Interview》

---

## 最后的建议

### 面试中的展示技巧

1. **先讲价值，再讲技术**
   - 错误："我用了PostgreSQL、Redis、FastAPI..."
   - 正确："这个项目解决了AI应用的上下文污染问题，技术上..."

2. **用具体数字说话**
   - 错误："性能优化后快了很多"
   - 正确："从2000ms优化到50ms，提升了40倍"

3. **主动展示思考深度**
   - 不要等面试官问"有什么不足"
   - 主动说："当时我还考虑过用Neo4j，但最终选PostgreSQL是因为..."

4. **准备好代码演示**
   - 提前准备好关键代码片段
   - 能快速定位到核心实现
   - 可以现场修改和调试

5. **诚实面对不足**
   - 不懂就说不懂，不要胡编
   - 说明如果给时间会如何学习
   - 展示学习能力比装懂更重要

---

**祝你面试顺利！🎉**
