# Learning System 前端优化与知识管理实施计划

**日期**: 2026-08-07  
**版本**: v1.0  
**基于**: ECC 生态分析 + MCP 重构协议理解

---

## 📋 执行摘要

本计划基于 ECC (Evolving Claude Code) 生态的设计思路，结合重构后的 MCP 协议特性，为 learning-system 项目设计了一套完整的前端优化和知识管理方案。

**核心目标**：
1. 实现流畅的多轮对话体验（会话管理）
2. 建立知识总结确认机制（人机协作）
3. 优化知识图谱可视化（中文显示）
4. 封装可复用的学习工作流（Skill 系统）

**预计时间**: 10-14 小时  
**优先级**: 高（阶段 1-2）→ 中（阶段 3）→ 低（阶段 4）

---

## ⚠️ 前置条件检查（2026-08-07 更新）

### 已解决的架构缺口

**✅ 文件系统工具集成** (2026-08-07)
- **问题**: MCP Server 缺少文件系统访问工具，LLM 无法读取本地文件
- **解决**: 在 `server.py` 中添加 5 个工具
  - `read_file` - 读取文件内容
  - `list_directory` - 列出目录结构
  - `search_files` - 搜索文件（glob 模式）
  - `write_file` - 写入文件
  - `get_file_info` - 获取文件元信息
- **影响**: LLM 现在可以读取和分析项目代码，这是后续优化的基础
- **工具数量**: 27 → 32

### 基于 system-completion-plan.md 的已完成模块

**✅ 核心基础设施**:
- MCP Server (端口 8080) + DeepSeek LLM 集成
- WebSocket 通信 + 前端客户端（StateManager, MCPClient）
- 知识图谱存储（PostgreSQL + pgvector）
- D3.js 力导向图组件（基础版）
- Skill 执行引擎（支持 .md 格式）
- Redis 缓存系统

**⏸️ 待优化的功能**:
- 前端响应格式显示（当前显示原始 JSON）
- 会话管理（session_id 未持久化）
- 知识图谱中文显示和交互
- 知识总结确认流程（核心新增功能）

**本计划专注于**: 在已有基础上增强用户体验和知识管理能力

---

## 🧠 ECC 生态核心洞察

### 为什么要用 Agent？

**不用 Agent 的问题**：
- 直接调用 LLM 时，所有任务共享同一个上下文，容易相互干扰
- 无法并行处理独立任务（如同时进行安全检查和性能分析）
- 难以实现多视角分析（需要不同角色从不同角度审查）

**Agent 的价值**：
```
Agent = 独立的 AI 实例 + 专门的 System Prompt + 独立的上下文 + 专门的工具集
```

**核心优势**：
1. **上下文专注** - 每个 agent 只处理自己领域的问题（如 knowledge-organizer 只负责整理知识）
2. **并行执行** - 独立 agent 可以并行运行，提高效率（如同时收集资料 + 生成题目）
3. **多视角分析** - 创建不同角色的 sub-agents（基础知识评估者 + 应用能力评估者 + 面试官视角）
4. **可组合性** - agent 可以串行或并行组合形成复杂工作流

**在 learning-system 中的应用**：
- `knowledge-organizer` - 负责整理和结构化学习材料
- `quiz-generator` - 根据知识图谱生成面试题
- `progress-tracker` - 分析学习进度并提供建议
- `knowledge-verifier` - 验证知识的准确性和一致性

**设计类比**：
```
传统方式：一个全能助手处理所有事情（容易混乱）
Agent 方式：专业团队，每个成员负责自己的领域（清晰高效）
```

---

### 为什么要用 Skill？

**不用 Skill 的问题**：
- 每次执行相同任务都要重新描述流程（如"先搜索资料，再提取知识点，再构建图谱"）
- 流程写死在代码中，难以调整和优化
- 无法复用成功的工作流模式

**Skill 的价值**：
```
Skill = 触发条件 + 执行步骤 + 质量门控 + 确认点
```

**核心优势**：
1. **可发现性** - 用户可以列出所有可用 skills（如 `/list-skills`），看到每个 skill 的用途
2. **参数化** - 同一个 skill 可以接受不同参数（如 `/learn-topic Python` vs `/learn-topic React`）
3. **模式复用** - 相同的工作流可以应用到不同领域（如学习 Python 和学习 React 的流程类似）
4. **可组合** - skills 可以调用其他 skills（如 `/master-topic` 包含 research + planning + execution）
5. **可演化** - 从使用中学习新的模式，保存为新 skill

**在 learning-system 中的应用**：
- `/learn-topic <主题>` - 端到端学习流程（搜索资料 → 提取知识 → 构建图谱 → 生成题目）
- `/mock-interview <岗位>` - 模拟面试流程（分析目标 → 生成题目 → 记录答案 → 评估反馈）
- `/review-weak-points` - 复习薄弱知识点（分析图谱 → 识别薄弱点 → 生成练习 → 跟踪进度）
- `/summarize-conversation` - 总结对话并确认（提取知识 → 预览 → 用户确认 → 存储到图谱）

**设计类比**：
```
传统方式：每次都手动执行一系列命令（重复劳动）
Skill 方式：一键触发完整工作流（自动化 + 标准化）
```

---

### 为什么要用 MCP？

**不用 MCP 的问题**：
- 每次都要实现与外部服务的集成逻辑（如知识图谱操作、文件读写）
- 工具接口不统一，难以切换实现（如从 Redis 切换到 PostgreSQL）
- 难以发现和组合可用的工具

**MCP 的价值**：
```
MCP = 标准化的工具协议 + 参数 Schema + 响应格式 + 错误处理
```

**核心优势**：
1. **标准化接口** - 所有工具遵循统一的协议（name, parameters, response）
2. **可替换性** - 底层实现可以切换（如从 Claude Memory MCP 切换到自己的 PostgreSQL 实现）
3. **可发现性** - 客户端可以列出所有可用工具及其参数 schema
4. **类型安全** - 参数和响应都有 schema 定义，避免类型错误

**在 learning-system 中的应用**：
- 使用 MCP 的 `create_entities` / `add_observations` 管理知识图谱
- 使用 MCP 的 `search_nodes` / `open_nodes` 检索知识
- 使用自定义 MCP 工具封装 DeepSeek LLM 调用（`chat` 工具）
- 前端通过 WebSocket 调用 MCP 工具，无需直接访问数据库或 LLM API

**设计类比**：
```
传统方式：每个服务都有自己的 API 风格（学习成本高）
MCP 方式：统一的协议，所有工具都是"即插即用"（标准化）
```

**为什么重构 MCP 很重要**：
- 旧版 MCP 缺少标准的 Session 管理和知识图谱支持
- 新版 MCP 原生支持 multi-agent、knowledge graph、memory 等高级特性
- 这个项目是学习和实践新版 MCP 的绝佳机会

---

### 关键设计原则

从 ECC 生态中提炼的设计原则：

1. **分层架构**  
   Tools（原子操作）→ Agents（领域专长）→ Skills（端到端工作流）
   
2. **质量门控**  
   在关键节点设置检查点（如知识一致性检查、学习完成度评估）
   
3. **确认机制**  
   在关键决策点等待用户确认（WAIT for user CONFIRM）
   
4. **并行执行**  
   独立任务并行处理以提高效率
   
5. **状态持久化**  
   会话状态、学习进度可以保存和恢复
   
6. **知识演化**  
   从使用中学习和优化（如提取有效的学习模式）

---

## 📐 MCP 协议核心特性

### 重构后的改进

基于 `docs/mcp-features-mapping.md` 和源码分析：

#### 1. 标准化 Tool 定义

每个 MCP 工具必须包含：
```python
@server.call_tool()
async def tool_name(
    param1: str,
    param2: Optional[int] = None
) -> dict:
    """
    工具描述
    
    参数：
      param1: 参数1描述
      param2: 参数2描述（可选）
    
    返回：
      {
        "result": "返回数据",
        "metadata": {...}  # 可选的元数据
      }
    """
    pass
```

**关键点**：
- 使用 Python 类型注解定义参数（自动生成 JSON Schema）
- Docstring 作为工具描述（客户端可以查看）
- 返回统一的 dict 格式（`result` 字段 + 可选的 `metadata`）

#### 2. Session 管理

重构后的 MCP 原生支持 Session：
```python
# 服务端
sessions = {}  # session_id -> conversation history

async def chat(message: str, session_id: Optional[str] = None) -> dict:
    # 如果没有 session_id，创建新会话
    if not session_id:
        session_id = f"session_{int(time.time())}_{random_string()}"
        sessions[session_id] = []
    
    # 获取历史消息
    history = sessions.get(session_id, [])
    history.append({"role": "user", "content": message})
    
    # 调用 LLM
    response = await llm.chat(history)
    history.append({"role": "assistant", "content": response})
    
    # 保存历史
    sessions[session_id] = history
    
    return {
        "response": response,
        "session_id": session_id,
        "message_count": len(history)
    }
```

**客户端使用**：
```typescript
// 第一次调用
const response1 = await mcpClient.callTool('chat', {
  message: "什么是 FastAPI？"
});
const sessionId = response1.result.session_id;

// 后续调用携带 session_id
const response2 = await mcpClient.callTool('chat', {
  message: "它有什么优点？",  // LLM 知道"它"指 FastAPI
  session_id: sessionId
});
```

#### 3. 知识图谱支持

MCP 重构后原生支持知识图谱操作：

**核心工具**：
- `create_entities` - 创建实体节点
- `add_observations` - 为实体添加观察/事实
- `create_relations` - 创建实体间的关系
- `search_nodes` - 搜索节点
- `open_nodes` - 获取节点详情
- `delete_entities` / `delete_observations` / `delete_relations` - 删除操作

**示例**：
```python
# 创建实体
await mcp.call_tool('create_entities', {
    "entities": [
        {
            "name": "FastAPI",
            "entityType": "technology",
            "observations": [
                "FastAPI 是一个现代 Python Web 框架",
                "基于 Starlette 和 Pydantic",
                "支持自动生成 API 文档"
            ]
        }
    ]
})

# 创建关系
await mcp.call_tool('create_relations', {
    "relations": [
        {
            "from": "FastAPI",
            "to": "Starlette",
            "relationType": "基于"
        }
    ]
})

# 搜索
result = await mcp.call_tool('search_nodes', {
    "query": "Python Web 框架"
})
```

#### 4. HTTP Transport

除了 WebSocket，MCP 也支持 HTTP 调用：
```python
# mcp-server/src/protocol/http_transport.py
@app.post("/mcp/call_tool")
async def call_tool(request: ToolCallRequest):
    tool_name = request.tool_name
    arguments = request.arguments
    
    # 调用对应的工具
    result = await tool_registry.call(tool_name, **arguments)
    
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request.id
    }
```

**适用场景**：
- WebSocket - 适合实时交互（如聊天、进度推送）
- HTTP - 适合无状态调用（如知识图谱查询、文件操作）

---

## 🏗️ 实施阶段

### 阶段 1：基础优化（高优先级，2-3 小时）

**目标**：修复当前前端展示和会话管理问题

---

#### 任务 1.1：优化响应格式显示

**问题**：
前端当前直接显示原始 JSON：
```json
{
  "response": "我来查看这个文件的内容...",
  "session_id": "session_1786097031_ept10r4w",
  "model": "deepseek-chat"
}
```

**期望**：
只显示 `response` 字段的内容，隐藏 `session_id` 和 `model`

**修改文件**：
- `client/frontend/src/components/ChatInterface.tsx`

**实施细节**：
```typescript
// 当前代码（第 67-72 行）
addMessage({
  role: 'assistant',
  content: JSON.stringify(parsed.result, null, 2),  // ❌ 显示整个 JSON
});

// 修改为
const handleSend = async () => {
  if (!userMessage.trim()) return;
  
  // 添加用户消息
  addMessage({
    role: 'user',
    content: userMessage,
  });
  
  setUserMessage('');
  setIsLoading(true);
  
  try {
    // 调用 MCP chat 工具
    const response = await mcpClient.callTool('chat', {
      message: userMessage,
      session_id: sessionId  // ✅ 携带会话 ID
    });
    
    const parsed = mcpClient.parseResponse(response);
    
    // ✅ 只提取 response 字段
    const assistantMessage = parsed.result?.response || 
                            JSON.stringify(parsed.result, null, 2);
    
    addMessage({
      role: 'assistant',
      content: assistantMessage,
    });
    
    // ✅ 保存 session_id 用于下次调用
    if (parsed.result?.session_id) {
      setSessionId(parsed.result.session_id);
    }
  } catch (error) {
    console.error('Chat failed:', error);
    addMessage({
      role: 'assistant',
      content: '抱歉，发生了错误。请重试。',
    });
  } finally {
    setIsLoading(false);
  }
};
```

**应用的 ECC 模式**：无（基础修复）

**预计时间**：15 分钟

---

#### 任务 1.2：实现会话管理

**问题**：
每次发送消息都是新会话，LLM 无法记住上下文

**期望**：
- 自动保存 `session_id`
- 后续消息自动携带 `session_id` 实现多轮对话
- 支持"新建会话"按钮清空当前会话

**修改文件**：
- `client/frontend/src/components/ChatInterface.tsx`

**实施细节**：
```typescript
// 在 ChatInterface 组件中添加状态
const [sessionId, setSessionId] = useState<string | null>(null);

// handleSend 已在任务 1.1 中修改，包含了 session_id 逻辑

// 添加"新建会话"功能
const handleNewSession = () => {
  // 清空 session_id
  setSessionId(null);
  
  // 清空消息列表
  setMessages([]);
  
  // 可选：显示提示
  addMessage({
    role: 'system',
    content: '已开始新会话',
  });
};

// 在 UI 中添加按钮
<div className="flex items-center justify-between p-4 border-b">
  <h2 className="text-xl font-bold">Learning System</h2>
  <div className="flex gap-2">
    <Button 
      onClick={handleNewSession}
      variant="outline"
      size="sm"
    >
      新会话
    </Button>
    <Button 
      onClick={handleSummarize}
      variant="default"
      size="sm"
    >
      总结
    </Button>
    <Button 
      onClick={handleShowGraph}
      variant="outline"
      size="sm"
    >
      知识图谱
    </Button>
  </div>
</div>
```

**可选优化（状态管理）**：
如果需要在多个组件间共享 session 状态，可以在 `appStore.ts` 中添加：
```typescript
// client/frontend/src/store/appStore.ts
interface AppState {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  // ...其他状态
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
  // ...
}));
```

**应用的 ECC 模式**：
- 状态管理与持久化（参考 ECC 的 session 机制）

**预计时间**：30 分钟

---

#### 任务 1.3：添加 Markdown 渲染

**问题**：
LLM 返回的内容可能包含 Markdown 格式（代码块、列表、加粗等），但前端直接显示为纯文本

**期望**：
支持 Markdown 渲染，提升可读性

**新增依赖**：
```bash
cd client/frontend
npm install react-markdown remark-gfm
```

**修改文件**：
- `client/frontend/src/components/ChatInterface.tsx`

**实施细节**：
```typescript
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// 在消息渲染部分
{messages.map((msg, index) => (
  <div 
    key={index} 
    className={cn(
      'mb-4 p-3 rounded-lg',
      msg.role === 'user' ? 'bg-blue-50 ml-8' : 'bg-gray-50 mr-8',
      msg.role === 'system' && 'bg-yellow-50 text-center text-sm'
    )}
  >
    {msg.role === 'assistant' ? (
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        className="prose prose-sm max-w-none"
        components={{
          // 自定义代码块样式
          code({node, inline, className, children, ...props}) {
            return inline ? (
              <code className="bg-gray-200 px-1 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            ) : (
              <code className="block bg-gray-800 text-white p-2 rounded overflow-x-auto" {...props}>
                {children}
              </code>
            );
          }
        }}
      >
        {msg.content}
      </ReactMarkdown>
    ) : (
      <p className="whitespace-pre-wrap">{msg.content}</p>
    )}
  </div>
))}
```

**应用的 ECC 模式**：无（基础 UX 改进）

**预计时间**：20 分钟

---

**阶段 1 验收标准**：
- [ ] 前端只显示 LLM 回答内容，不显示 `session_id` 和 `model`
- [ ] 支持 Markdown 渲染（代码块、列表、加粗等）
- [ ] 多轮对话能保持上下文（LLM 记住之前的对话）
- [ ] "新会话"按钮能清空当前会话并开始新对话

---

### 阶段 2：知识总结确认流程（高优先级，4-5 小时）

**目标**：实现用户主导的知识提取和确认机制

---

#### 任务 2.1：设计知识总结 MCP 工具

**新增文件**：
- `mcp-server/src/tools/summarize_conversation.py`

**工具设计**：
```python
"""
知识总结工具 - 从对话中提取知识点
"""
import json
import re
import logging
from typing import Optional
from ..llm.factory import llm_factory

logger = logging.getLogger(__name__)

# Few-shot 提示词模板
EXTRACTION_PROMPT_TEMPLATE = """
请从以下对话中提取关键知识点，以 JSON 数组格式返回。

示例输入：
用户: 什么是 FastAPI？
助手: FastAPI 是一个现代、快速的 Python Web 框架，基于 Starlette 和 Pydantic。它的主要特点是高性能、自动生成 API 文档、支持类型提示。

用户: 它有什么优点？
助手: 主要优点包括：1. 性能接近 NodeJS 和 Go；2. 自动生成 OpenAPI 和 Swagger 文档；3. 类型提示支持减少错误；4. 异步支持。

示例输出：
[
  {{
    "title": "FastAPI 定义",
    "content": "FastAPI 是一个现代、快速的 Python Web 框架，基于 Starlette（ASGI 框架）和 Pydantic（数据验证）。",
    "tags": ["Python", "Web框架", "ASGI"],
    "type": "technology"
  }},
  {{
    "title": "FastAPI 核心特性",
    "content": "1. 高性能（性能接近 NodeJS 和 Go）\\n2. 自动生成 API 文档（OpenAPI 和 Swagger UI）\\n3. 类型提示支持（利用 Python 3.6+ 的类型注解）\\n4. 原生异步支持（async/await）",
    "tags": ["FastAPI", "特性", "性能"],
    "type": "concept"
  }},
  {{
    "title": "FastAPI 技术栈",
    "content": "FastAPI 构建在两个核心库之上：\\n- Starlette：提供 ASGI 支持和 Web 功能\\n- Pydantic：提供数据验证和序列化",
    "tags": ["FastAPI", "Starlette", "Pydantic"],
    "type": "concept"
  }}
]

现在请处理以下对话：
{conversation_text}

要求：
1. 每个知识点包含 title、content、tags、type 字段
2. title 简短明确（10 字以内）
3. content 详细完整（包含定义、特点、用途等）
4. tags 至少 2 个，最多 5 个
5. type 必须是 concept/technology/method/tool 之一
6. 至少提取 3 个知识点
7. 只提取实质性的技术知识，不包括问候语和重复内容
8. 直接返回 JSON 数组，不要添加额外说明
"""


async def summarize_conversation(
    conversation_text: str,
    extraction_prompt: Optional[str] = None
) -> dict:
    """
    从对话中提取知识点
    
    参数：
      conversation_text: 完整的对话文本
      extraction_prompt: 可选的自定义提取提示词
    
    返回：
      {
        "knowledge_points": [
          {
            "title": "知识点标题",
            "content": "详细内容",
            "tags": ["标签1", "标签2"],
            "type": "concept"
          }
        ],
        "count": 3
      }
    """
    try:
        # 构造提示词
        prompt = extraction_prompt or EXTRACTION_PROMPT_TEMPLATE.format(
            conversation_text=conversation_text
        )
        
        # 调用 LLM
        llm_client = llm_factory.create()
        response = await llm_client.chat(prompt, session_id=None)
        
        # 解析 JSON
        knowledge_points = []
        try:
            knowledge_points = json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 部分（LLM 可能返回额外文本）
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                knowledge_points = json.loads(json_match.group())
            else:
                raise ValueError("Failed to extract JSON from LLM response")
        
        # 验证和格式化返回的知识点
        validated_points = []
        for point in knowledge_points:
            # 必需字段检查
            if not all(k in point for k in ['title', 'content', 'tags', 'type']):
                logger.warning(f"Skipping invalid knowledge point: {point}")
                continue
            
            # 类型检查
            if point['type'] not in ['concept', 'technology', 'method', 'tool']:
                logger.warning(f"Invalid type {point['type']}, defaulting to 'concept'")
                point['type'] = 'concept'
            
            # 标签格式化
            if isinstance(point['tags'], str):
                point['tags'] = [tag.strip() for tag in point['tags'].split(',')]
            
            # 确保 tags 是列表
            if not isinstance(point['tags'], list):
                point['tags'] = []
            
            validated_points.append(point)
        
        if not validated_points:
            raise ValueError("No valid knowledge points extracted")
        
        return {
            "knowledge_points": validated_points,
            "count": len(validated_points)
        }
    
    except Exception as e:
        logger.error(f"Summarize conversation failed: {e}")
        return {
            "knowledge_points": [],
            "count": 0,
            "error": str(e)
        }
```

**注册到 server.py**：
```python
# 在 mcp-server/server.py 中注册工具
from src.tools.summarize_conversation import summarize_conversation

# 在 register_tools() 函数中添加
@server.call_tool()
async def summarize_conversation_tool(
    conversation_text: str,
    extraction_prompt: str = None
) -> dict:
    """从对话中提取知识点"""
    return await summarize_conversation(conversation_text, extraction_prompt)
```

**应用的 ECC 模式**：
- 工具分层（Tool 层）
- Prompt Engineering（Few-shot Learning）

**预计时间**：1.5 小时

---

#### 任务 2.2：前端实现总结确认 UI

**新增文件**：
- `client/frontend/src/components/KnowledgeConfirmDialog.tsx`

**KnowledgeConfirmDialog 组件**：
```typescript
import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface KnowledgePoint {
  title: string;
  content: string;
  tags: string[];
  type: string;
}

interface Props {
  knowledgePoints: KnowledgePoint[];
  onConfirm: (selectedPoints: KnowledgePoint[]) => void;
  onCancel: () => void;
}

export const KnowledgeConfirmDialog: React.FC<Props> = ({
  knowledgePoints,
  onConfirm,
  onCancel,
}) => {
  const [selected, setSelected] = useState<Set<number>>(
    new Set(knowledgePoints.map((_, i) => i)) // 默认全选
  );
  const [editedPoints, setEditedPoints] = useState(knowledgePoints);

  const handleToggle = (index: number) => {
    const newSelected = new Set(selected);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelected(newSelected);
  };

  const handleEdit = (index: number, field: string, value: any) => {
    const newPoints = [...editedPoints];
    newPoints[index] = { ...newPoints[index], [field]: value };
    setEditedPoints(newPoints);
  };

  const handleConfirm = () => {
    const selectedPoints = Array.from(selected).map((i) => editedPoints[i]);
    onConfirm(selectedPoints);
  };

  return (
    <Dialog open={true} onOpenChange={onCancel}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>确认知识点</DialogTitle>
          <DialogDescription>
            请检查提取的知识点，可以编辑或取消不需要的项
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {editedPoints.map((point, index) => (
            <Card
              key={index}
              className={!selected.has(index) ? 'opacity-50' : ''}
            >
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Checkbox
                    checked={selected.has(index)}
                    onCheckedChange={() => handleToggle(index)}
                  />
                  <Input
                    value={point.title}
                    onChange={(e) =>
                      handleEdit(index, 'title', e.target.value)
                    }
                    className="flex-1 font-semibold"
                    placeholder="知识点标题"
                  />
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <Textarea
                  value={point.content}
                  onChange={(e) =>
                    handleEdit(index, 'content', e.target.value)
                  }
                  rows={3}
                  placeholder="详细内容"
                />
                <div className="flex gap-2">
                  <Input
                    value={point.tags.join(', ')}
                    onChange={(e) =>
                      handleEdit(
                        index,
                        'tags',
                        e.target.value.split(',').map((t) => t.trim())
                      )
                    }
                    placeholder="标签（逗号分隔）"
                    className="flex-1"
                  />
                  <Select
                    value={point.type}
                    onValueChange={(value) => handleEdit(index, 'type', value)}
                  >
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="concept">概念</SelectItem>
                      <SelectItem value="technology">技术</SelectItem>
                      <SelectItem value="method">方法</SelectItem>
                      <SelectItem value="tool">工具</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            取消
          </Button>
          <Button onClick={handleConfirm} disabled={selected.size === 0}>
            确认添加 ({selected.size} 个)
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
```

**修改文件**：
- `client/frontend/src/components/ChatInterface.tsx`

**工具依赖**：
- ✅ `summarize_conversation` - 已存在（任务 2.1 创建）
- ✅ `add_knowledge` - 已补充（2026-08-07 新增，封装 create_entities）

**ChatInterface 集成**：
```typescript
import { KnowledgeConfirmDialog } from './KnowledgeConfirmDialog';

// 在 ChatInterface 组件中添加状态
const [showConfirmDialog, setShowConfirmDialog] = useState(false);
const [pendingKnowledge, setPendingKnowledge] = useState<KnowledgePoint[]>([]);

// 总结按钮处理函数
const handleSummarize = async () => {
  if (messages.length === 0) {
    alert('当前对话为空，无法总结');
    return;
  }

  setIsLoading(true);
  try {
    // 1. 构造对话历史文本
    const conversationText = messages
      .filter((m) => m.role !== 'system') // 过滤系统消息
      .map((m) => `${m.role === 'user' ? '用户' : '助手'}: ${m.content}`)
      .join('\n\n');

    // 2. 调用 summarize_conversation 工具
    const response = await mcpClient.callTool('summarize_conversation', {
      conversation_text: conversationText,
    });

    const parsed = mcpClient.parseResponse(response);

    // 检查是否有错误
    if (parsed.result.error) {
      throw new Error(parsed.result.error);
    }

    const knowledgePoints = parsed.result.knowledge_points;

    if (!knowledgePoints || knowledgePoints.length === 0) {
      alert('未能提取到有效的知识点，请尝试更详细的对话');
      return;
    }

    // 3. 显示确认对话框
    setPendingKnowledge(knowledgePoints);
    setShowConfirmDialog(true);
  } catch (error) {
    console.error('Summarize failed:', error);
    alert(`总结失败: ${error.message}`);
  } finally {
    setIsLoading(false);
  }
};

// 确认知识点处理函数
const handleConfirmKnowledge = async (selectedPoints: KnowledgePoint[]) => {
  setShowConfirmDialog(false);
  setIsLoading(true);

  try {
    // 4. 逐个添加到知识图谱
    let successCount = 0;
    for (const point of selectedPoints) {
      try {
        await mcpClient.callTool('add_knowledge', {
          title: point.title,
          content: point.content,
          tags: point.tags,
          type: point.type,
        });
        successCount++;
      } catch (error) {
        console.error(`Failed to add knowledge point: ${point.title}`, error);
      }
    }

    // 5. 显示成功提示
    alert(`成功添加 ${successCount}/${selectedPoints.length} 个知识点到知识图谱`);

    // 6. 可选：刷新知识图谱（如果当前显示图谱）
    // await handleLoadGraph();
  } catch (error) {
    console.error('Add knowledge failed:', error);
    alert('添加知识点失败，请查看控制台');
  } finally {
    setIsLoading(false);
  }
};

// 取消确认处理函数
const handleCancelConfirm = () => {
  setShowConfirmDialog(false);
  setPendingKnowledge([]);
};

// 在 JSX 中渲染确认对话框
{showConfirmDialog && (
  <KnowledgeConfirmDialog
    knowledgePoints={pendingKnowledge}
    onConfirm={handleConfirmKnowledge}
    onCancel={handleCancelConfirm}
  />
)}
```

**应用的 ECC 模式**：
- 确认机制（参考 `/plan` 的 WAIT for user CONFIRM）
- 质量门控（用户可以编辑和筛选知识点）

**预计时间**：2.5 小时

---

#### 任务 2.3：优化错误处理和用户反馈

**修改文件**：
- `client/frontend/src/components/ChatInterface.tsx`

**添加加载状态指示器**：
```typescript
// 在总结过程中显示进度
const [summaryProgress, setSummaryProgress] = useState<string>('');

const handleSummarize = async () => {
  // ... 前面的代码 ...
  
  try {
    setSummaryProgress('正在分析对话内容...');
    
    // 调用工具
    const response = await mcpClient.callTool('summarize_conversation', {
      conversation_text: conversationText,
    });
    
    setSummaryProgress('正在提取知识点...');
    
    // ... 处理响应 ...
    
    setSummaryProgress('');
  } catch (error) {
    setSummaryProgress('');
    // ... 错误处理 ...
  }
};

// 在 UI 中显示进度
{summaryProgress && (
  <div className="fixed bottom-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg">
    {summaryProgress}
  </div>
)}
```

**添加 Toast 通知**（可选）：
```bash
npm install sonner
```

```typescript
import { toast } from 'sonner';

// 替换 alert 为 toast
toast.success(`成功添加 ${successCount} 个知识点到知识图谱`);
toast.error('总结失败，请重试');
```

**应用的 ECC 模式**：
- 用户反馈和状态跟踪（参考 TodoWrite）

**预计时间**：1 小时

---

**阶段 2 验收标准**：
- [x] 点击"总结"按钮后，系统自动提取知识点 ✅ 
- [x] 显示确认对话框，用户可以查看、编辑、删除知识点 ✅
- [x] 用户可以取消选择不需要的知识点 ✅
- [x] 用户确认后，知识点添加到知识图谱（调用 MCP 工具）✅
- [x] 如果 LLM 提取失败或格式错误，显示友好的错误提示 ✅
- [x] 提取的知识点至少包含 3 个，且格式正确 ✅
- [x] 显示加载进度和成功/失败反馈 ✅

**任务 2 完成状态** (已完成 ✅):
- ✅ 后端工具层：`summarize_conversation` + `add_knowledge` (已实现)
- ✅ 前端 UI 组件：`KnowledgeConfirmDialog.tsx` (已实现)
- ✅ 前端集成：`ChatInterface.tsx` 中已实现 `handleSummarize` 和 `handleConfirmKnowledge`
- ✅ 错误处理：已添加错误提示和加载状态 (`summaryProgress`)
- ✅ 用户反馈：使用系统消息提示成功/失败

**实现文件**:
- `mcp-server/src/tools/summarize_conversation.py` - 知识提取工具
- `mcp-server/server.py` - 添加 `add_knowledge` 封装工具
- `client/frontend/src/components/KnowledgeConfirmDialog.tsx` - 确认对话框
- `client/frontend/src/components/ChatInterface.tsx` - 集成逻辑（第175-250行）

---

### 阶段 3：知识图谱增强（中优先级，2-3 小时）

**目标**：优化知识图谱可视化和交互

---

#### 任务 3.1：修复中文显示

**问题**：
知识图谱节点标签可能显示为英文 ID 或字段名

**期望**：
节点和边的标签都显示中文

**修改文件**：
- `mcp-server/src/tools/ui_knowledge_graph.py`

**实施细节**：
```python
async def ui_knowledge_graph() -> dict:
    """返回知识图谱的可视化数据"""
    from ..storage.mcp_memory_adapter import mcp_memory_adapter
    
    nodes = []
    edges = []
    
    try:
        # 从数据库查询所有实体
        entities = await mcp_memory_adapter.read_graph()
        
        # 处理节点
        node_map = {}  # id -> node data
        for entity in entities.get('entities', []):
            node_id = entity['name']
            node_map[node_id] = {
                "id": node_id,
                "label": entity['name'],  # ✅ 使用 name 作为 label
                "type": entity.get('entityType', 'concept'),
                "observations": entity.get('observations', []),
                "size": 10 + len(entity.get('observations', [])) * 2,  # 根据观察数量调整大小
                "color": get_type_color(entity.get('entityType', 'concept'))
            }
        
        # 处理边（关系）
        for relation in entities.get('relations', []):
            edges.append({
                "source": relation['from'],
                "target": relation['to'],
                "label": relation.get('relationType', '关联'),  # ✅ 使用中文关系名
                "type": "default"
            })
        
        nodes = list(node_map.values())
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to load knowledge graph: {e}")
        return {
            "nodes": [],
            "edges": [],
            "stats": {"node_count": 0, "edge_count": 0},
            "error": str(e)
        }


def get_type_color(node_type: str) -> str:
    """根据节点类型返回颜色"""
    colors = {
        "concept": "#60A5FA",      # 蓝色 - 概念
        "technology": "#34D399",    # 绿色 - 技术
        "method": "#FBBF24",        # 黄色 - 方法
        "tool": "#F87171",          # 红色 - 工具
        "person": "#A78BFA",        # 紫色 - 人物
        "organization": "#FB923C",  # 橙色 - 组织
    }
    return colors.get(node_type, "#9CA3AF")  # 默认灰色
```

**前端检查**：
- `client/frontend/src/components/KnowledgeGraph.tsx`

```typescript
// 确认显示的是 node.label 而不是 node.id
const renderNode = (node: GraphNode) => {
  return (
    <g transform={`translate(${node.x},${node.y})`}>
      <circle
        r={node.size || 10}
        fill={node.color || '#60A5FA'}
        stroke="#fff"
        strokeWidth={2}
        style={{ cursor: 'pointer' }}
      />
      <text
        dy="25"
        textAnchor="middle"
        fontSize="12"
        fill="#333"
      >
        {node.label}  {/* ✅ 显示 label，不是 id */}
      </text>
    </g>
  );
};
```

**应用的 ECC 模式**：无（基础修复）

**预计时间**：30 分钟

---

#### 任务 3.2：添加图谱交互功能

**修改文件**：
- `client/frontend/src/components/KnowledgeGraph.tsx`

**新增功能**：

**1. 节点点击显示详情**：
```typescript
const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

const handleNodeClick = async (node: GraphNode) => {
  try {
    // 调用 MCP 工具获取节点详情
    const response = await mcpClient.callTool('open_nodes', {
      names: [node.id]
    });
    
    const parsed = mcpClient.parseResponse(response);
    const nodeDetails = parsed.result;
    
    setSelectedNode({
      ...node,
      details: nodeDetails
    });
  } catch (error) {
    console.error('Failed to load node details:', error);
  }
};

// 详情面板
{selectedNode && (
  <div className="absolute top-4 right-4 w-80 bg-white rounded-lg shadow-lg p-4 max-h-96 overflow-y-auto">
    <div className="flex justify-between items-start mb-2">
      <h3 className="font-bold text-lg">{selectedNode.label}</h3>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setSelectedNode(null)}
      >
        ✕
      </Button>
    </div>
    
    <div className="space-y-2">
      <div>
        <span className="text-sm font-semibold text-gray-600">类型：</span>
        <span className="text-sm ml-2">{selectedNode.type}</span>
      </div>
      
      {selectedNode.observations && selectedNode.observations.length > 0 && (
        <div>
          <span className="text-sm font-semibold text-gray-600">观察：</span>
          <ul className="list-disc list-inside text-sm mt-1">
            {selectedNode.observations.map((obs, i) => (
              <li key={i}>{obs}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  </div>
)}
```

**2. 搜索和过滤**：
```typescript
const [searchQuery, setSearchQuery] = useState('');
const [filteredNodes, setFilteredNodes] = useState<GraphNode[]>([]);

const handleSearch = async () => {
  if (!searchQuery.trim()) {
    setFilteredNodes(nodes);
    return;
  }
  
  try {
    const response = await mcpClient.callTool('search_nodes', {
      query: searchQuery
    });
    
    const parsed = mcpClient.parseResponse(response);
    const results = parsed.result;
    
    // 高亮搜索结果
    const resultIds = new Set(results.map(r => r.name));
    const highlighted = nodes.map(node => ({
      ...node,
      highlighted: resultIds.has(node.id)
    }));
    
    setFilteredNodes(highlighted);
  } catch (error) {
    console.error('Search failed:', error);
  }
};

// 搜索框
<div className="absolute top-4 left-4 flex gap-2">
  <Input
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
    placeholder="搜索知识点..."
    className="w-64"
  />
  <Button onClick={handleSearch}>搜索</Button>
</div>
```

**3. 类型筛选**：
```typescript
const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());

const handleTypeFilter = (type: string) => {
  const newTypes = new Set(selectedTypes);
  if (newTypes.has(type)) {
    newTypes.delete(type);
  } else {
    newTypes.add(type);
  }
  setSelectedTypes(newTypes);
};

// 应用筛选
const visibleNodes = selectedTypes.size === 0 
  ? nodes 
  : nodes.filter(n => selectedTypes.has(n.type));

// 类型筛选按钮
<div className="absolute bottom-4 left-4 flex gap-2">
  {['concept', 'technology', 'method', 'tool'].map(type => (
    <Button
      key={type}
      variant={selectedTypes.has(type) ? 'default' : 'outline'}
      size="sm"
      onClick={() => handleTypeFilter(type)}
    >
      {type === 'concept' ? '概念' :
       type === 'technology' ? '技术' :
       type === 'method' ? '方法' : '工具'}
    </Button>
  ))}
</div>
```

**应用的 ECC 模式**：
- 交互式探索（参考 ECC 的 code-explorer）

**预计时间**：2 小时

---

#### 任务 3.3：优化图谱布局和视觉效果

**修改文件**：
- `client/frontend/src/components/KnowledgeGraph.tsx`

**优化项**：

**1. 力导向图参数调优**：
```typescript
// 优化 D3.js 力导向参数
const simulation = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(edges)
    .id(d => d.id)
    .distance(100)  // 增加边长度
    .strength(0.5)  // 降低吸引力
  )
  .force('charge', d3.forceManyBody()
    .strength(-300)  // 增加排斥力，避免节点重叠
  )
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide()
    .radius(d => d.size + 5)  // 碰撞检测，避免重叠
  );
```

**2. 添加边的箭头**：
```typescript
// 定义箭头标记
<defs>
  <marker
    id="arrowhead"
    markerWidth="10"
    markerHeight="10"
    refX="20"
    refY="3"
    orient="auto"
    markerUnits="strokeWidth"
  >
    <path d="M0,0 L0,6 L9,3 z" fill="#999" />
  </marker>
</defs>

// 在边上应用箭头
<line
  x1={edge.source.x}
  y1={edge.source.y}
  x2={edge.target.x}
  y2={edge.target.y}
  stroke="#999"
  strokeWidth={2}
  markerEnd="url(#arrowhead)"  // 添加箭头
/>
```

**3. 节点悬停效果**：
```typescript
const [hoveredNode, setHoveredNode] = useState<string | null>(null);

<circle
  r={node.size || 10}
  fill={node.color}
  stroke={hoveredNode === node.id ? '#000' : '#fff'}
  strokeWidth={hoveredNode === node.id ? 3 : 2}
  style={{ 
    cursor: 'pointer',
    transition: 'all 0.2s ease'
  }}
  onMouseEnter={() => setHoveredNode(node.id)}
  onMouseLeave={() => setHoveredNode(null)}
  onClick={() => handleNodeClick(node)}
/>
```

**4. 缩放和平移**：
```typescript
import { zoom } from 'd3-zoom';
import { select } from 'd3-selection';

useEffect(() => {
  const svg = select(svgRef.current);
  
  const zoomBehavior = zoom()
    .scaleExtent([0.5, 3])  // 缩放范围：50% - 300%
    .on('zoom', (event) => {
      select('.graph-container')
        .attr('transform', event.transform);
    });
  
  svg.call(zoomBehavior);
}, []);
```

**应用的 ECC 模式**：
- 视觉优化（参考 ECC 的 frontend-design）

**预计时间**：30 分钟

---

**阶段 3 验收标准**：
- [ ] 知识图谱节点和边都显示中文
- [ ] 点击节点能显示详情面板（观察、类型等）
- [ ] 搜索功能能高亮匹配的节点
- [ ] 类型筛选能过滤不同类型的节点
- [ ] 图谱支持缩放和平移
- [ ] 节点有悬停效果
- [ ] 边显示箭头指示方向
- [ ] 力导向布局合理，节点不重叠

---

### 阶段 4：Skill 封装（低优先级，2-3 小时）

**目标**：将知识总结流程封装为可复用的 Skill

---

#### 任务 4.1：设计 Skill 结构

**新增文件**：
- `mcp-server/skills/summarize_knowledge.yaml`

**Skill 定义**：
```yaml
name: summarize_knowledge
description: 从对话中总结知识点并添加到知识图谱
version: 1.0.0

triggers:
  - 用户点击"总结"按钮
  - 命令：/summarize

phases:
  - name: extract
    description: 从对话中提取知识点
    agent: knowledge_extractor
    tools:
      - summarize_conversation
    output: knowledge_points

  - name: confirm
    description: 等待用户确认知识点
    requires_user_input: true
    input_type: knowledge_confirmation
    output: confirmed_points

  - name: store
    description: 将确认的知识点存储到知识图谱
    agent: knowledge_organizer
    tools:
      - create_entities
      - add_observations
    input: confirmed_points
    output: storage_result

quality_gates:
  - phase: extract
    condition: knowledge_points.length >= 3
    message: "至少需要提取 3 个知识点"
  
  - phase: store
    condition: storage_result.success_count >= 1
    message: "至少需要成功存储 1 个知识点"

metadata:
  author: learning-system
  tags: [knowledge-management, summarization]
  complexity: medium
```

**应用的 ECC 模式**：
- Skill 封装（完整的触发条件 + 执行步骤 + 质量门控）

**预计时间**：1 小时

---

#### 任务 4.2：实现 Skill 执行器

**修改文件**：
- `mcp-server/src/agents/skill_executor.py`（如果不存在则新建）

**Skill 执行逻辑**：
```python
"""
Skill 执行器 - 执行 Skill 定义的工作流
"""
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SkillExecutor:
    """执行 Skill 定义的工作流"""
    
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.loaded_skills = {}
        self._load_skills()
    
    def _load_skills(self):
        """加载所有 Skill 定义"""
        for skill_file in self.skills_dir.glob("*.yaml"):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_def = yaml.safe_load(f)
                    self.loaded_skills[skill_def['name']] = skill_def
                    logger.info(f"Loaded skill: {skill_def['name']}")
            except Exception as e:
                logger.error(f"Failed to load skill {skill_file}: {e}")
    
    async def execute(
        self,
        skill_name: str,
        context: Dict[str, Any],
        user_input_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        执行 Skill
        
        参数：
          skill_name: Skill 名称
          context: 执行上下文（如对话历史）
          user_input_callback: 用户输入回调函数（用于确认步骤）
        
        返回：
          执行结果
        """
        skill_def = self.loaded_skills.get(skill_name)
        if not skill_def:
            raise ValueError(f"Skill not found: {skill_name}")
        
        results = {}
        current_data = context
        
        # 逐个执行 phase
        for phase in skill_def['phases']:
            phase_name = phase['name']
            logger.info(f"Executing phase: {phase_name}")
            
            try:
                # 如果需要用户输入
                if phase.get('requires_user_input'):
                    if not user_input_callback:
                        raise ValueError(f"Phase {phase_name} requires user input but no callback provided")
                    
                    # 调用回调函数等待用户确认
                    user_data = await user_input_callback(
                        phase.get('input_type'),
                        current_data.get(phase.get('input', 'data'))
                    )
                    current_data[phase['output']] = user_data
                else:
                    # 调用 agent 或工具执行
                    phase_result = await self._execute_phase(phase, current_data)
                    current_data[phase['output']] = phase_result
                
                # 检查质量门控
                if not self._check_quality_gates(skill_def, phase_name, current_data):
                    raise ValueError(f"Quality gate failed for phase: {phase_name}")
                
                results[phase_name] = current_data[phase['output']]
            
            except Exception as e:
                logger.error(f"Phase {phase_name} failed: {e}")
                results[phase_name] = {"error": str(e)}
                break
        
        return results
    
    async def _execute_phase(self, phase: Dict, context: Dict) -> Any:
        """执行单个 phase"""
        # 获取输入数据
        input_data = context.get(phase.get('input', 'data'))
        
        # 调用工具
        if 'tools' in phase:
            tool_name = phase['tools'][0]  # 简化：只取第一个工具
            from ..tools import tool_registry
            result = await tool_registry.call(tool_name, **input_data)
            return result
        
        # 调用 agent（简化实现）
        if 'agent' in phase:
            agent_name = phase['agent']
            # TODO: 实现 agent 调用逻辑
            logger.warning(f"Agent {agent_name} execution not implemented yet")
            return input_data
        
        return input_data
    
    def _check_quality_gates(
        self,
        skill_def: Dict,
        phase_name: str,
        current_data: Dict
    ) -> bool:
        """检查质量门控"""
        gates = skill_def.get('quality_gates', [])
        
        for gate in gates:
            if gate['phase'] == phase_name:
                # 简化：只检查 length 条件
                condition = gate['condition']
                if 'length' in condition:
                    field, op, value = condition.split()
                    field = field.replace('.length', '')
                    data_value = len(current_data.get(field, []))
                    
                    if op == '>=' and data_value < int(value):
                        logger.warning(f"Quality gate failed: {gate['message']}")
                        return False
        
        return True


# 全局实例
skill_executor = SkillExecutor()
```

**应用的 ECC 模式**：
- 工作流编排（phase 串行执行）
- 质量门控（每个 phase 完成后检查）

**预计时间**：1.5 小时

---

#### 任务 4.3：集成到前端

**修改文件**：
- `client/frontend/src/components/ChatInterface.tsx`

**使用 Skill 替代直接调用工具**：
```typescript
const handleSummarize = async () => {
  setIsLoading(true);
  
  try {
    // 调用 Skill 而不是直接调用工具
    const response = await mcpClient.callTool('execute_skill', {
      skill_name: 'summarize_knowledge',
      context: {
        messages: messages
          .filter(m => m.role !== 'system')
          .map(m => ({
            role: m.role,
            content: m.content
          }))
      }
    });
    
    const parsed = mcpClient.parseResponse(response);
    
    // 处理 Skill 执行结果
    if (parsed.result.confirm) {
      // Skill 返回需要确认的知识点
      setPendingKnowledge(parsed.result.confirm.knowledge_points);
      setShowConfirmDialog(true);
    } else if (parsed.result.store) {
      // Skill 已完成存储
      alert(`成功添加 ${parsed.result.store.success_count} 个知识点`);
    }
  } catch (error) {
    console.error('Skill execution failed:', error);
    alert('总结失败，请重试');
  } finally {
    setIsLoading(false);
  }
};
```

**应用的 ECC 模式**：
- Skill 调用（一键触发完整工作流）

**预计时间**：30 分钟

---

**阶段 4 验收标准**：
- [ ] Skill 定义文件存在且格式正确
- [ ] Skill 执行器能加载和解析 Skill 定义
- [ ] 前端调用 Skill 能触发完整工作流
- [ ] Skill 的确认步骤能正确暂停等待用户输入
- [ ] 质量门控能正确检查并阻止不合格的结果
- [ ] Skill 执行失败时能返回友好的错误信息

---
单元测试

  前端组件测试：
  // client/frontend/src/components/__tests__/ChatInterface.test.tsx
  describe('ChatInterface', () => {
    test('should save session_id after first message', async () => {
      const { getByPlaceholderText, getByText } = render(<ChatInterface />);

      // 发送消息
      const input = getByPlaceholderText('输入消息...');
      fireEvent.change(input, { target: { value: '什么是 FastAPI？' } });
      fireEvent.click(getByText('发送'));

      // 验证 session_id 被保存
      await waitFor(() => {
        expect(mockMcpClient.callTool).toHaveBeenCalledWith('chat', {
          message: '什么是 FastAPI？',
          session_id: null
        });
      });
    });

    test('should reuse session_id in subsequent messages', async () => {
      // ... 测试多轮对话
    });
  });

  // client/frontend/src/components/__tests__/KnowledgeConfirmDialog.test.tsx
  describe('KnowledgeConfirmDialog', () => {
    test('should allow editing knowledge points', () => {
      const mockPoints = [
        { title: 'FastAPI', content: '...', tags: ['Python'], type: 'technology' }
      ];
      const { getByDisplayValue } = render(
        <KnowledgeConfirmDialog
          knowledgePoints={mockPoints}
          onConfirm={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      const titleInput = getByDisplayValue('FastAPI');
      fireEvent.change(titleInput, { target: { value: 'FastAPI 框架' } });

      expect(titleInput.value).toBe('FastAPI 框架');
    });
  });

  后端工具测试：
  # mcp-server/tests/test_summarize_conversation.py
  import pytest
  from src.tools.summarize_conversation import summarize_conversation

  @pytest.mark.asyncio
  async def test_summarize_valid_conversation():
      conversation = """
      用户: 什么是 FastAPI？
      助手: FastAPI 是一个现代 Python Web 框架...
      """

      result = await summarize_conversation(conversation)

      assert result['count'] >= 3
      assert all('title' in p for p in result['knowledge_points'])
      assert all('content' in p for p in result['knowledge_points'])

  @pytest.mark.asyncio
  async def test_summarize_handles_invalid_json():
      conversation = "无意义的对话"

      result = await summarize_conversation(conversation)

      # 应该降级处理，返回 error 而不是抛出异常
      assert 'error' in result or result['count'] == 0

  ---
  集成测试

  前后端交互测试：
  // client/frontend/src/__tests__/integration/knowledge-summary.test.tsx
  describe('Knowledge Summary Integration', () => {
    test('complete knowledge summary flow', async () => {
      // 1. 发送多轮对话
      await sendMessage('什么是 FastAPI？');
      await sendMessage('它有什么优点？');

      // 2. 点击总结按钮
      const summarizeBtn = screen.getByText('总结');
      fireEvent.click(summarizeBtn);

      // 3. 等待确认对话框出现
      await waitFor(() => {
        expect(screen.getByText('确认知识点')).toBeInTheDocument();
      });

      // 4. 确认添加
      const confirmBtn = screen.getByText(/确认添加/);
      fireEvent.click(confirmBtn);

      // 5. 验证知识点已添加
      await waitFor(() => {
        expect(screen.getByText(/成功添加/)).toBeInTheDocument();
      });
    });
  });

  MCP 工具链测试：
  # mcp-server/tests/test_knowledge_workflow.py
  @pytest.mark.asyncio
  async def test_knowledge_extraction_to_storage():
      # 1. 提取知识点
      result1 = await summarize_conversation(sample_conversation)
      assert result1['count'] > 0

      # 2. 存储到知识图谱
      from src.storage.mcp_memory_adapter import mcp_memory_adapter

      for point in result1['knowledge_points']:
          await mcp_memory_adapter.create_entities([{
              "name": point['title'],
              "entityType": point['type'],
              "observations": [point['content']]
          }])

      # 3. 验证能检索到
      result2 = await mcp_memory_adapter.search_nodes(point['title'])
      assert len(result2) > 0

  ---
  E2E 场景测试

  场景 1：多轮对话并总结
  1. 用户打开聊天界面
  2. 用户问："什么是 FastAPI？"
     - 验证：收到 LLM 回答
  3. 用户问："它的优点是什么？"
     - 验证：LLM 记住上下文，回答 FastAPI 的优点
  4. 用户点击"总结"按钮
     - 验证：显示确认对话框，列出 3+ 个知识点
  5. 用户编辑第一个知识点的标题
     - 验证：标题更新成功
  6. 用户取消选择第二个知识点
     - 验证：该知识点不再被选中
  7. 用户点击"确认添加"
     - 验证：显示成功消息
  8. 用户打开知识图谱
     - 验证：能看到新添加的知识点节点

  场景 2：新会话测试
  1. 用户进行多轮对话（3 轮）
  2. 用户点击"新会话"按钮
     - 验证：消息列表清空
     - 验证：显示"已开始新会话"提示
  3. 用户问："Python 是什么？"
     - 验证：LLM 不记得之前关于 FastAPI 的对话

  场景 3：知识图谱交互
  1. 用户打开知识图谱
     - 验证：显示所有节点和边
  2. 用户点击一个节点
     - 验证：显示详情面板，包含观察列表
  3. 用户在搜索框输入"FastAPI"并搜索
     - 验证：相关节点被高亮
  4. 用户点击"技术"类型筛选
     - 验证：只显示 technology 类型的节点
  5. 用户缩放图谱
     - 验证：图谱能正常缩放

  ---
  📚 相关学习概念（面试准备）

  1. 会话管理（Session Management）

  概念：
  在多轮对话中保持上下文，让 AI 记住之前说过的内容。

  实现方式：
  - 客户端管理：前端保存 session_id，每次请求携带
  - 服务端缓存：服务端用 session_id 作为 key 缓存历史消息
  - 过期策略：设置 TTL（如 30 分钟无活动则过期）

  面试要点：
  - "我在项目中实现了基于 session_id 的会话管理，前端通过 useState 保存会话 ID，后端使用字典缓存历史消息"
  - "支持多会话切换，用户可以点击'新会话'按钮清空上下文"
  - "考虑了内存管理，会话有过期时间，避免无限增长"

  ---
  2. 知识图谱（Knowledge Graph）

  概念：
  用图结构表示知识，节点是实体，边是关系。

  核心组成：
  - 实体（Entity）：知识点本身（如"FastAPI"）
  - 属性（Attribute）：实体的特征（如类型、标签）
  - 关系（Relation）：实体间的连接（如"FastAPI 基于 Starlette"）

  存储方案：
  - 图数据库：Neo4j（原生图存储）
  - 关系数据库 + 图查询：PostgreSQL（本项目使用）
  - 向量数据库：Pinecone + pgvector（支持语义搜索）

  面试要点：
  - "我用 PostgreSQL + pgvector 实现了知识图谱，支持关系查询和向量搜索"
  - "通过 MCP 协议封装了 create_entities、create_relations 等操作"
  - "前端用 D3.js 力导向图可视化，支持拖拽、缩放、搜索"

  ---
  3. RAG（Retrieval-Augmented Generation）

  概念：
  检索增强生成，先检索相关知识，再让 LLM 生成回答。

  工作流程：
  用户提问
    → 向量化查询
    → 检索知识图谱
    → 将知识作为上下文
    → LLM 生成回答

  优势：
  - 减少幻觉（基于真实知识）
  - 可追溯（提供引用来源）
  - 知识可更新（无需重新训练模型）

  面试要点：
  - "虽然当前版本没有完整实现 RAG，但设计上预留了接口"
  - "知识图谱的 search_nodes 可以作为 RAG 的检索层"
  - "下一步可以将检索结果注入到 LLM 的 prompt 中"

  ---
  4. Prompt Engineering

  概念：
  设计有效的提示词，引导 LLM 生成期望的输出。

  技巧：
  - 明确输出格式：要求返回 JSON 或特定结构
  - Few-shot Learning：提供示例输入和输出
  - 分步骤引导：Chain-of-Thought（思维链）
  - 角色设定：让 LLM 扮演特定角色

  本项目应用：
  # Few-shot 示例
  EXTRACTION_PROMPT_TEMPLATE = """
  示例输入：
  用户: 什么是 FastAPI？
  助手: FastAPI 是...

  示例输出：
  [{"title": "FastAPI 定义", ...}]

  现在请处理以下对话：
  {conversation_text}

  面试要点：
  - "我用 Few-shot Learning 提升了知识提取的准确性"
  - "通过明确要求 JSON 格式，避免了解析错误"
  - "加入了质量要求（至少 3 个知识点），确保输出可用"

  ---
  5. MCP 协议（Model Context Protocol）

  概念：
  统一的 AI 工具调用协议，类似于 REST API 但专为 AI Agent 设计。

  核心特性：
  - 标准化接口：所有工具遵循统一格式
  - 类型安全：参数和响应有 JSON Schema 定义
  - 可组合：工具可以调用其他工具
  - 可发现：客户端可以列出所有可用工具

  为什么需要 MCP：
  - 传统方式：每个 LLM 服务商都有自己的工具格式（OpenAI Function Calling、Anthropic Tool Use）
  - MCP 方式：统一协议，工具定义一次，所有模型都能用

  面试要点：
  - "我实践了重构后的 MCP 协议，完整实现了 30+ 工具"
  - "通过 MCP 封装了知识图谱操作，前端无需直接访问数据库"
  - "支持 WebSocket 和 HTTP 两种传输方式，适应不同场景"

  ---
  6. Multi-Agent 系统

  概念：
  多个专门的 AI Agent 协作完成复杂任务。

  设计模式：
  - 管道模式：Agent1 → Agent2 → Agent3（串行）
  - 并行模式：Agent1、Agent2、Agent3 同时执行
  - 对抗模式：Generator Agent vs Evaluator Agent

  本项目设计：
  knowledge-organizer  → 整理知识
  quiz-generator      → 生成题目
  progress-tracker    → 分析进度
  knowledge-verifier  → 验证准确性

  面试要点：
  - "我设计了 Multi-Agent 架构，每个 Agent 负责特定领域"
  - "Agent 之间通过 MCP 工具通信，保持松耦合"
  - "未来可以并行执行多个 Agent，提高效率"

  ---
  7. 确认机制（Confirmation Pattern）

  概念：
  在关键决策点暂停，等待用户确认后再执行，避免在错误方向上浪费资源。

  ECC 模式：
  generate plan → WAIT for user CONFIRM → execute plan

  本项目应用：
  extract knowledge → SHOW preview → WAIT for user edit/confirm → store to graph

  优势：
  - 人机协作（AI 提供建议，人做决策）
  - 质量控制（用户可以修正 AI 的错误）
  - 增强信任（用户知道系统不会"擅自行动"）

  面试要点：
  - "我实现了知识总结的确认流程，用户可以编辑、删除提取的知识点"
  - "参考了 ECC 的 /plan 模式，在关键点等待用户输入"
  - "这种设计提升了用户对 AI 的信任度"

  ---
  ⚠️ 风险和缓解措施

  风险 1：LLM 提取知识点不准确

  影响：高

  表现：
  - 提取的知识点过于宽泛或细碎
  - 提取了非技术内容（如问候语）
  - 重复提取相同内容

  缓解措施：
  1. 优化 Prompt：使用 Few-shot 示例，明确要求
  2. 后处理验证：检查必需字段，过滤无效知识点
  3. 用户确认：让用户最终决定哪些知识点有效
  4. 迭代改进：收集用户反馈，持续优化提取逻辑

  ---
  风险 2：用户体验过于复杂

  影响：中

  表现：
  - 确认对话框字段过多，用户不知道如何填写
  - 知识图谱交互不直观，用户不知道如何操作

  缓解措施：
  1. 简化 UI：只显示核心字段（标题、内容），隐藏高级选项
  2. 提供默认值：自动填充类型和标签，用户可选修改
  3. 添加引导：首次使用时显示操作提示
  4. 用户测试：邀请真实用户测试，收集反馈

  ---
  风险 3：知识图谱查询性能

  影响：中

  表现：
  - 节点数量增长后，图谱加载缓慢
  - 搜索响应时间过长

  缓解措施：
  1. 分页加载：一次只加载部分节点（如 100 个）
  2. 索引优化：为常用查询字段（name、type）添加索引
  3. 缓存策略：使用 Redis 缓存热点查询结果
  4. 图谱剪枝：只显示与当前主题相关的子图

  ---
  风险 4：会话状态丢失

  影响：低

  表现：
  - 用户刷新页面后，当前会话丢失
  - 服务端重启后，所有会话清空

  缓解措施：
  1. 前端持久化：将 session_id 保存到 localStorage
  2. 服务端持久化：将会话历史保存到 Redis（而非内存）
  3. 会话恢复：页面加载时自动恢复上次的会话
  4. 明确提示：告知用户"新会话"会清空历史

  ---
  🎯 实施优先级总结

  P0（必须完成）：

  - ✅ 阶段 1：基础优化（会话管理、响应格式）
  - ✅ 阶段 2：知识总结确认流程

  P1（强烈建议）：

  - ⭐ 阶段 3：知识图谱增强（中文显示、交互）

  P2（可选）：

  - 💡 阶段 4：Skill 封装

  ---
  📝 后续扩展方向

  完成当前计划后，可以考虑：

  1. 学习路径推荐：根据知识图谱生成个性化学习路径
  2. 模拟面试：基于知识图谱自动生成面试题
  3. 学习进度分析：可视化学习进度和薄弱环节
  4. 知识导入导出：支持从 Markdown、PDF 导入知识
  5. 协作学习：多用户共享知识图谱
