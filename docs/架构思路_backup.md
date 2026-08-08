# Learning System AI-First 架构设计方案

> **核心理念**：让 LLM 成为编排者，MCP Server 只提供原子能力

---

## 一、当前架构 vs 目标架构

### 1.1 当前架构的问题

```
用户 
  ↓
自定义客户端（你的 LLM）
  ↓
MCP Server: track_project()
  └─ 硬编码流程：
     1. 检测框架
     2. 扫描文件
     3. 分析依赖
     4. 提取亮点
     5. 生成报告
```

**问题**：
- ❌ 工作流固定，无法灵活调整
- ❌ 新需求要改服务端代码
- ❌ LLM 只是被动调用工具，不参与决策
- ❌ 无法复用 ECC 生态的 skills

### 1.2 目标架构（AI-first）

```
用户："帮我准备这个项目的面试"
  ↓
客户端 LLM 读取 Skill 指南（interview-prep.md）
  ├─ 理解流程：分析项目 → 提取亮点 → 生成面试材料
  ├─ 动态决策：需要哪些工具？如何组合？
  └─ 调用原子化的 MCP Tools：
      ├─ project/detect_framework()
      ├─ project/scan_structure()
      ├─ knowledge/search()
      └─ knowledge/save()
```

**优势**：
- ✅ 工作流由 Skill 定义，易于修改和扩展
- ✅ LLM 根据上下文动态决策
- ✅ 服务端只提供能力，不含业务逻辑
- ✅ 可复用 ECC 的 skills 和 MCP servers

---

## 二、架构分层设计

### Layer 1: MCP Server（服务端）- 原子能力层

**职责**：提供最小粒度的工具，不包含业务逻辑

#### 2.1 项目分析模块（拆分 track_project）

**现状问题**：
```python
@server.tool("track_project")
async def track_project(project_path: str):
    # 做了太多事：检测框架 + 扫描文件 + 分析依赖 + 提取亮点
    # 这是"策略"，不应该在服务端硬编码
```

**改造方案**：拆分为原子操作

```python
@server.tool("project/detect_framework")
async def detect_framework(project_path: str) -> MCPResult:
    """
    只负责检测框架
    输入：项目路径
    输出：{framework: "FastAPI", confidence: 0.9, evidence: [...]}
    """
    
@server.tool("project/scan_structure")
async def scan_structure(project_path: str) -> MCPResult:
    """
    只负责扫描目录结构和文件统计
    输入：项目路径
    输出：{directories: [...], files: {...}, stats: {...}}
    """
    
@server.tool("project/analyze_dependencies")
async def analyze_dependencies(project_path: str) -> MCPResult:
    """
    只负责分析依赖包
    输入：项目路径
    输出：{dependencies: [...], versions: {...}}
    """
    
@server.tool("project/extract_patterns")
async def extract_patterns(project_path: str) -> MCPResult:
    """
    只负责提取代码模式和约定
    输入：项目路径
    输出：{naming_convention: "snake_case", patterns: [...]}
    """
```

**关键点**：
- 每个工具只做一件事
- 输入输出清晰，不含复杂逻辑
- 如何组合这些工具？由客户端的 Skill 决定

#### 2.2 知识图谱模块（保持现状，已经够原子化）

```python
@server.tool("knowledge/search")        # 已有 search_knowledge
@server.tool("knowledge/save")          # 已有 save_knowledge
@server.tool("knowledge/get_graph")     # 已有 get_knowledge_graph
@server.tool("knowledge/create_relation")  # 新增：建立节点关系
@server.tool("knowledge/delete_nodes")  # 已有 delete_knowledge
```

#### 2.3 外部资源模块（新增）

```python
@server.tool("resource/query_docs")
async def query_docs(library: str, query: str) -> MCPResult:
    """
    查询技术文档（集成 Context7 MCP）
    输入：library="FastAPI", query="如何实现依赖注入"
    输出：{content: "...", examples: [...], source: "official"}
    """
    
@server.tool("resource/web_search")
async def web_search(query: str, result_count: int = 10) -> MCPResult:
    """
    网络搜索（集成 Exa MCP）
    输入：query="FastAPI 最佳实践", result_count=10
    输出：{results: [...], sources: [...]}
    """
```

**实现方式**：
- 在你的 MCP Server 中调用其他 MCP Server（Context7, Exa）
- 或者客户端直接连接多个 MCP Server

---

### Layer 2: Skills（客户端配置）- AI 工作流层

**核心概念**：Skill 是给 LLM 看的"说明书"，不是代码

#### 2.4 Skill 是什么？

**Skill 文件示例**（interview-prep.md）：

```markdown
---
name: interview-prep
description: 准备技术面试，分析项目技术栈，生成面试材料和常见问答
---

# 面试准备 Skill

## 触发条件
- 用户说"准备面试"、"复习项目"、"项目介绍"
- 用户询问"如何在面试中介绍这个项目"

## 工作流程

### Step 1: 了解面试目标
询问用户：
- 面试的岗位和级别？（实习 / 初级 / 中级 / 高级）
- 目标公司技术栈？（如果知道）
- 重点准备方向？（后端 / 前端 / 全栈）

### Step 2: 分析项目
并行调用以下 MCP 工具：
1. project/detect_framework(project_path)
2. project/scan_structure(project_path)
3. project/analyze_dependencies(project_path)
4. knowledge/search("project:" + project_name)

### Step 3: 提取技术亮点
基于 Step 2 的结果，识别：
- 技术选型亮点：为什么选这个框架？
- 架构设计亮点：采用了什么模式？
- 技术深度亮点：实现了哪些有难度的功能？

如果内部知识不足，调用 resource/query_docs 补充。

### Step 4: 生成面试材料
输出包含：
1. 项目一句话介绍（30秒电梯演讲）
2. 技术栈清单
3. 核心功能模块（用 STAR 法则描述）
4. 技术难点与解决方案
5. 常见面试问题（10-15个，附答案要点）

### Step 5: 保存到知识图谱
调用 knowledge/save 保存项目信息和技术节点。
```

**关键点**：
- Skill 是 **Markdown 文件**，不是代码
- LLM 读取后理解流程，动态执行
- 每个 Step 都清晰说明：调用什么工具、期望什么结果

#### 2.5 客户端如何使用 Skill？

**方式 1：系统提示加载（推荐）**

客户端在启动时：
```python
# 客户端代码示例
def load_skills(skills_dir: str) -> str:
    """扫描 skills 目录，生成系统提示"""
    skills = []
    for skill_file in Path(skills_dir).glob("**/*.md"):
        # 解析 frontmatter
        with open(skill_file) as f:
            content = f.read()
            # 提取 name 和 description
            name = extract_frontmatter(content, "name")
            desc = extract_frontmatter(content, "description")
            skills.append(f"- {name}: {desc}")
    
    return f"""
可用的 Skills：
{chr(10).join(skills)}

当用户的请求匹配某个 skill 的触发条件时，读取该 skill 的完整内容并按照流程执行。
"""

# 在系统提示中添加
system_prompt = f"""
你是一个学习助手。

{load_skills("./skills/")}

MCP Tools 可用：
- project/detect_framework
- project/scan_structure
- knowledge/search
- knowledge/save
...
"""
```

**方式 2：动态加载（按需）**

```python
# 当 LLM 判断需要某个 skill 时
def execute_skill(skill_name: str, user_context: dict):
    # 读取 skill 文件
    skill_content = read_skill_file(f"./skills/{skill_name}.md")
    
    # 将 skill 内容注入到 LLM 上下文
    messages = [
        {"role": "system", "content": "按照以下 skill 指南执行"},
        {"role": "system", "content": skill_content},
        {"role": "user", "content": user_context["request"]}
    ]
    
    # LLM 根据 skill 指南调用 MCP tools
    response = llm.chat(messages)
    return response
```

#### 2.6 Skills 目录结构

```
learning-system/
  skills/
    interview-prep.md          # 面试准备
    tech-deep-dive.md          # 技术深度学习
    project-review.md          # 项目快速复习
    codebase-onboarding.md     # 代码库入门（可复用 ECC）
```

**每个 skill 包含**：
- Frontmatter（name, description）
- 触发条件
- 工作流程（Step by Step）
- 输出格式
- 质量要求

---

### Layer 3: 客户端实现

#### 2.7 客户端架构

```
客户端（Python/TypeScript/其他）
  ├─ LLM 接口层（调用你的 LLM API）
  ├─ MCP Client（连接 MCP Server）
  ├─ Skill 管理器（加载和解析 skills）
  └─ 对话管理器（管理会话状态）
```

**核心流程**：
```python
# 伪代码
class LearningSystemClient:
    def __init__(self):
        self.mcp_client = MCPClient("http://localhost:8000")
        self.skill_manager = SkillManager("./skills/")
        self.llm = YourLLMAPI()
    
    async def handle_user_message(self, user_message: str):
        # 1. 构建系统提示（包含可用 skills）
        system_prompt = self.build_system_prompt()
        
        # 2. LLM 处理消息（可能调用 MCP tools）
        response = await self.llm.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ], tools=self.mcp_client.list_tools())
        
        # 3. 如果 LLM 请求调用工具
        if response.tool_calls:
            for tool_call in response.tool_calls:
                result = await self.mcp_client.call_tool(
                    tool_call.name,
                    tool_call.arguments
                )
                # 将结果返回给 LLM
                response = await self.llm.continue_chat(result)
        
        return response
    
    def build_system_prompt(self) -> str:
        """构建包含 skills 列表的系统提示"""
        skills_summary = self.skill_manager.get_skills_summary()
        return f"""
你是学习系统助手。

可用的 Skills：
{skills_summary}

当用户请求匹配某个 skill 时，读取该 skill 的完整内容并执行。

可用的 MCP Tools：
{self.mcp_client.list_tools()}
"""
```

#### 2.8 MCP Client 实现

```python
class MCPClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.transport = StdioTransport()  # 或 HTTP Transport
    
    async def call_tool(self, tool_name: str, args: dict):
        """调用 MCP tool"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            },
            "id": generate_id()
        }
        response = await self.transport.send(request)
        return response["result"]
    
    def list_tools(self) -> list:
        """获取可用工具列表"""
        # 连接 MCP Server，获取 tools/list
        return [
            {"name": "project/detect_framework", "description": "..."},
            {"name": "knowledge/search", "description": "..."},
            # ...
        ]
```

---

## 三、MCP 2026 新特性的应用

### 3.1 MRTR（多轮往返请求）

**应用场景**：危险操作需要用户确认

**客户端实现**：
```python
async def handle_tool_call(self, tool_name: str, args: dict):
    result = await self.mcp_client.call_tool(tool_name, args)
    
    # 检查是否需要用户确认（MRTR）
    if result.get("_meta", {}).get("io.modelcontextprotocol/inputRequired"):
        # 第一轮：服务端返回确认请求
        input_required = result["_meta"]["io.modelcontextprotocol/inputRequired"]
        
        # 展示给用户
        user_choice = await self.ui.show_confirmation(
            message=input_required["message"],
            fields=input_required["fields"]
        )
        
        # 第二轮：带着 requestState 和用户选择再次调用
        result = await self.mcp_client.call_tool(
            tool_name,
            {**args, "request_state": input_required["requestState"], **user_choice}
        )
    
    return result
```

**示例流程**：
```
用户：删除这个知识节点
  ↓
LLM 调用：knowledge/delete_nodes(["node-123"])
  ↓
MCP Server 返回（第一轮）：
{
  "_meta": {
    "io.modelcontextprotocol/inputRequired": {
      "message": "⚠️ 将删除知识节点，不可逆",
      "fields": [{"name": "confirm", "type": "boolean"}],
      "requestState": "JWT_TOKEN"
    }
  }
}
  ↓
客户端展示确认对话框
  ↓
用户点击"确认"
  ↓
客户端再次调用：knowledge/delete_nodes(["node-123"], request_state="JWT_TOKEN", confirm=true)
  ↓
MCP Server 验证 JWT，执行删除（第二轮）
```

### 3.2 Tasks 扩展（长时间任务）

**应用场景**：项目深度分析（5-10分钟）

**客户端实现**：
```python
async def handle_long_task(self, tool_name: str, args: dict):
    result = await self.mcp_client.call_tool(tool_name, args)
    
    # 检查是否返回 taskHandle
    if result.get("_meta", {}).get("io.modelcontextprotocol.tasks/taskHandle"):
        task_handle = result["_meta"]["io.modelcontextprotocol.tasks/taskHandle"]
        task_id = task_handle["task_id"]
        
        # 显示进度条
        while True:
            status = await self.mcp_client.call_tool("tasks/get", {"task_id": task_id})
            
            # 更新进度条
            await self.ui.update_progress(
                progress=status["progress"],
                message=status["message"]
            )
            
            if status["status"] == "completed":
                return status["result"]
            elif status["status"] == "failed":
                raise Exception(status["error"])
            
            await asyncio.sleep(2)  # 每2秒查询一次
```

**示例流程**：
```
用户：深度分析这个项目
  ↓
LLM 调用：analyze_project_deep(project_path)
  ↓
MCP Server 返回：
{
  "_meta": {
    "io.modelcontextprotocol.tasks/taskHandle": {
      "task_id": "task-001",
      "status": "running",
      "progress": 0.0,
      "message": "扫描项目文件..."
    }
  }
}
  ↓
客户端显示进度条：[████░░░░░░] 40% 分析架构模式...
  ↓
客户端轮询：tasks/get(task_id="task-001")
  ↓
任务完成，返回结果
```

### 3.3 MCP Apps（交互式 UI）

**应用场景**：知识图谱可视化、项目配置选择

**客户端实现**：
```python
async def handle_mcp_app(self, result: dict):
    # 检查是否返回 uiTemplate
    if result.get("_meta", {}).get("uiTemplate"):
        ui_template = result["_meta"]["uiTemplate"]
        
        # 根据 templateId 渲染 UI
        if ui_template["templateId"] == "knowledge-graph-viz":
            # 渲染知识图谱可视化
            graph_data = ui_template["data"]
            await self.ui.render_knowledge_graph(graph_data)
        
        elif ui_template["templateId"] == "project-analysis-config":
            # 渲染配置选择器
            config = await self.ui.show_config_dialog(ui_template["data"])
            
            # 用户交互后，通过 MCP 协议回传结果
            await self.mcp_client.call_tool(
                "project/analyze",
                {"config": config}
            )
```

**示例：知识图谱可视化**


---

## 四、无状态协议的深入影响

### 4.1 核心原则

MCP 2026 的无状态设计：
- 每个请求都是独立的，不依赖 connection/session 状态
- 所有状态通过 ID 显式传递
- 服务端不保存会话信息

### 4.2 客户端必须承担的职责

客户端需要管理：
1. 会话状态（session_id, user_id）
2. 对话历史（LLM 上下文）
3. 项目上下文（当前项目路径）
4. 长任务状态（running_tasks）
5. MRTR 待确认（pending_confirmations）
6. MCP Apps 状态（active_apps）
7. 知识图谱缓存（利用 MCP 缓存策略）

### 4.3 每次 MCP 调用都要带上下文



---

## 五、MCP Apps 完整设计

### 5.1 MCP App 定义

- 服务端返回的交互式 UI 组件（HTML/React）
- 在客户端沙箱中渲染（iframe + CSP）
- 通过 postMessage 双向通信
- 用户交互结果通过 MCP 协议回传

### 5.2 MCP App 生命周期

1. 触发：用户请求可视化
2. 服务端返回：uiTemplate + 初始数据
3. 客户端渲染：创建沙箱 iframe
4. 用户交互：点击、筛选、修改
5. 客户端响应：调用 MCP 工具更新数据
6. 清理：关闭 App，销毁 iframe

### 5.3 具体示例

#### App 1: 知识图谱可视化

服务端返回 templateId + 图数据，客户端用 vis.js 渲染。
用户点击节点 → postMessage → 客户端调用 knowledge/get_details → 更新显示。

#### App 2: 项目分析配置器

服务端返回表单 HTML，用户选择配置 → postMessage → 客户端开始深度分析。

---

## 六、客户端完整功能模块

### 6.1 核心架构



### 6.2 任务管理器

负责：
- 提交长任务
- 轮询进度（tasks/get）
- 更新 UI 进度条
- 处理任务完成/失败

### 6.3 MRTR 处理器

负责：
- 检测 inputRequired
- 显示确认对话框
- 带 requestState 再次调用
- JWT 验证（服务端处理）

---

## 七、完整场景实现

### 场景1：面试准备
1. LLM 读取 interview-prep skill
2. 询问用户目标
3. 并行调用项目分析工具
4. 生成面试材料
5. 保存到知识图谱

### 场景2：知识图谱可视化
1. 调用 knowledge/get_graph
2. 检测到 uiTemplate
3. 渲染 MCP App
4. 用户点击节点
5. 更新详情显示

### 场景3：深度项目分析
1. 提交长任务
2. 显示进度条
3. 后台轮询 tasks/get
4. 任务完成返回结果

### 场景4：删除知识节点
1. 第一轮：返回确认请求（MRTR）
2. 显示对话框
3. 第二轮：带 requestState 执行删除

---

## 八、客户端技术选型

### 推荐方案：FastAPI + React

**前端（React）**：
- 对话界面
- MCP App 渲染容器（iframe 沙箱）
- 进度条/通知
- 知识图谱可视化

**后端（FastAPI）**：
- WebSocket Server（实时通信）
- MCP Client（连接 MCP Server）
- LLM API 调用
- Skill/State/Task/MRTR/App Manager

**优势**：
- 前后端分离，易于扩展
- React 生态丰富
- MCP Apps 渲染简单
- 支持实时更新
- 易于部署

---

## 九、最终架构图

To use the fastapi command, please install "fastapi[standard]":

	pip install "fastapi[standard]"

---

## 十、实施路线

### Phase 1: MCP Server 原子化（2天）
- 拆分 track_project 为 4 个工具
- 简化 explore_technology
- 测试原子工具

### Phase 2: 客户端基础（3天）
- FastAPI 后端框架
- React 前端框架
- WebSocket 通信
- SkillManager 实现

### Phase 3: MCP 协议集成（2天）
- MCPClient 实现
- TaskManager（轮询）
- MRTRHandler（二次确认）
- AppManager（App 渲染）

### Phase 4: Skills 编写（1天）
- interview-prep.md
- tech-deep-dive.md
- project-review.md

### Phase 5: 端到端测试（1天）
- 完整场景测试
- 优化 Skill 指南
- 性能优化

**总计：9天完成 MVP**

---

## 文档完成

本架构方案详细说明了：
1. AI-first 设计理念
2. MCP Server 原子化改造
3. Skills 在客户端的使用
4. 无状态协议的影响
5. MCP Apps 的完整实现
6. 客户端功能模块设计
7. 完整场景实现
8. 技术选型建议

**下一步**：开始实施 Phase 1 的 MCP Server 重构。
