# MCP 2026-07-28 完整实现计划

## 项目目标

将 Learning System 从基础 MCP 实现升级到完整支持 MCP 2026-07-28 协议的所有核心特性。

---

## 当前状态分析

### ✅ 已完成
- 基础 MCP Tools（4个工具）
- 基础 MCP Resources（2个资源）
- 无状态协议（ID 生成器）
- 事件总线架构
- 多 Agent 系统框架

### ❌ 缺失的关键特性
- MRTR（多轮往返请求）
- Tasks 扩展（长任务进度追踪）
- MCP Apps（交互式 UI）
- Extensions 框架（动态工具注册）
- 缓存策略（ttlMs + cacheScope）
- OAuth 2.0 增强（加密存储）

---

## Phase 0：基础设施重构（Week 1, 预计 3-4 天）

### 目标
替换 FastMCP，搭建支持 `_meta` 字段的 MCP 协议层

### 任务清单

#### Task 0.1：创建 MCP 协议核心层
- [ ] 创建 `src/protocol/mcp_protocol.py`
  - 实现 JSON-RPC 2.0 请求解析
  - 实现 JSON-RPC 2.0 响应生成
  - 支持 `_meta` 字段
- [ ] 创建 `src/protocol/result_types.py`
  - `MCPResult` 基类
  - `InputRequiredResult`（MRTR）
  - `TaskHandleResult`（Tasks）
  - `UITemplateResult`（MCP Apps）
- [ ] 创建 `src/protocol/transport.py`
  - stdio 传输层（标准输入输出）
  - SSE 传输层（HTTP）

**验收标准**：
```python
# 能够返回带 _meta 的响应
result = MCPResult(
    data={"status": "ok"},
    meta={"ttlMs": 3600000}
)
assert result.to_jsonrpc() == {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {"status": "ok"},
    "_meta": {"ttlMs": 3600000}
}
```

#### Task 0.2：迁移现有 Tools 到新协议
- [ ] 重写 `server.py`，移除 FastMCP 依赖
- [ ] 迁移 4 个现有工具：
  - `analyze_session`
  - `save_knowledge`
  - `track_project`
  - `explore_technology`
- [ ] 迁移 2 个现有资源：
  - `knowledge://graph`
  - `sessions://list`

#### Task 0.3：测试基础设施
- [ ] 编写 `tests/test_protocol.py`
- [ ] 验证 JSON-RPC 2.0 兼容性
- [ ] 验证现有功能不受影响

**里程碑**：
```bash
# 能够通过 stdio 调用工具
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"analyze_session"}}' | python server.py
```

#### Task 0.4：Hook 自动捕获会话系统 ⭐ 新增
- [ ] 创建 `src/hooks/observe.py`
  - 监听所有 MCP Tool 调用
  - 记录到 `observations.jsonl`（借鉴 ECC）
  - 异步写入，不阻塞主流程
- [ ] 创建 `src/hooks/session_detector.py`
  - 检测会话边界（30分钟无活动 = 会话结束）
  - 自动触发 SessionAnalyzer
- [ ] 创建 `src/hooks/hook_manager.py`
  - 统一 Hook 管理接口
  - 装饰器模式包装所有工具
- [ ] 修改 `server.py`
  - 在 tool 执行前后插入 Hook
  - 记录：工具名、参数、返回值、时间戳

**参考 ECC**：
```bash
# ECC 的 Hook 机制
~/.claude/ecc/skills/continuous-learning-v2/hooks/observe.sh
# 观察日志格式
observations.jsonl:
{"timestamp": "2026-08-03T10:30:00Z", "event": "tool_call_start", "tool": "analyze_session", "params": {...}}
{"timestamp": "2026-08-03T10:30:05Z", "event": "tool_call_end", "tool": "analyze_session", "result": {...}}
```

**验收标准**：
```bash
# 1. 启动服务器并调用工具
python server.py &
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"analyze_session"}}' | python server.py

# 2. 检查观察日志
cat observations.jsonl
# 应该看到 tool_call_start 和 tool_call_end

# 3. 测试会话检测（修改阈值为 1 分钟）
# 等待 1 分钟后，应该自动触发 SessionAnalyzer
# 检查事件总线是否收到 "session.completed" 事件
```

**面试亮点**：
- "借鉴 ECC 的 Hook 机制，实现零侵入的会话捕获"
- "用 JSONL 格式记录观察日志，便于后续分析和回溯"
- "30分钟空闲自动触发分析，无需用户干预"

**预计工作量**：3.5-5.5 天（含 Task 0.4 的 1.5 天）

---

## Phase 1：MRTR（多轮往返请求）实现（Week 1-2, 预计 4-5 天）

### 目标
实现危险操作的二次确认机制，包含 JWT 签名验证

### 核心概念
```
用户操作 → 服务器返回确认请求 → 用户确认 → 服务器验证 JWT → 执行操作
```

### 任务清单

#### Task 1.1：JWT 基础设施
- [ ] 创建 `src/security/jwt_handler.py`
  - JWT 生成（含过期时间 5 分钟）
  - JWT 验证（防篡改）
  - Nonce 机制（防重放攻击）
- [ ] 创建 `src/security/nonce_store.py`
  - 内存存储已使用的 nonce
  - 自动清理过期 nonce

**代码示例**：
```python
class JWTHandler:
    def generate_request_state(
        self, 
        operation: str, 
        params: Dict[str, Any]
    ) -> str:
        """生成 JWT token"""
        nonce = uuid4().hex
        payload = {
            "operation": operation,
            "params": params,
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "nonce": nonce
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    
    def verify_request_state(self, token: str) -> Dict[str, Any]:
        """验证 JWT token"""
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        
        # 检查 nonce 是否已使用
        if nonce_store.is_used(payload["nonce"]):
            raise SecurityError("Nonce already used (replay attack)")
        
        nonce_store.mark_used(payload["nonce"])
        return payload
```

#### Task 1.2：实现危险操作确认
- [ ] 重构 `delete_knowledge` 工具（新增）
- [ ] 重构 `delete_project` 工具（新增）
- [ ] 重构 `rebuild_index` 工具（新增）

**实现模式**：
```python
@mcp_tool("delete_knowledge")
async def delete_knowledge(
    knowledge_ids: List[str],
    request_state: str = None
) -> MCPResult:
    jwt_handler = JWTHandler()
    
    if not request_state:
        # 第一轮：返回确认请求
        token = jwt_handler.generate_request_state(
            operation="delete_knowledge",
            params={"knowledge_ids": knowledge_ids}
        )
        
        return InputRequiredResult(
            message=f"⚠️ 将删除 {len(knowledge_ids)} 个知识节点，此操作不可逆",
            fields=[
                {"name": "confirm", "type": "boolean", "label": "确认删除"},
                {"name": "archive_instead", "type": "boolean", "default": True, "label": "归档而非删除"}
            ],
            request_state=token
        )
    
    # 第二轮：验证并执行
    try:
        payload = jwt_handler.verify_request_state(request_state)
        
        # 验证参数一致性
        if payload["params"]["knowledge_ids"] != knowledge_ids:
            raise SecurityError("Parameters mismatch")
        
        # 执行删除
        deleted_count = await memory_manager.delete_nodes(knowledge_ids)
        
        return MCPResult(
            data={
                "deleted_count": deleted_count,
                "status": "completed"
            }
        )
    except jwt.ExpiredSignatureError:
        raise MCPError("Request expired, please retry")
    except SecurityError as e:
        raise MCPError(f"Security error: {e}")
```

#### Task 1.3：MRTR 场景测试
- [ ] 编写 `tests/test_mrtr.py`
- [ ] 测试正常流程（确认删除）
- [ ] 测试拒绝流程（取消删除）
- [ ] 测试安全性（JWT 篡改、重放攻击、过期 token）

**测试用例**：
```python
async def test_mrtr_delete_knowledge():
    # 第一轮
    result1 = await delete_knowledge(knowledge_ids=["k-001"])
    assert "io.modelcontextprotocol/inputRequired" in result1.meta
    token = result1.meta["io.modelcontextprotocol/inputRequired"]["requestState"]
    
    # 第二轮
    result2 = await delete_knowledge(
        knowledge_ids=["k-001"],
        request_state=token
    )
    assert result2.data["deleted_count"] == 1
```

#### Task 1.4：文档编写
- [ ] 创建 `docs/mrtr-implementation.md`
- [ ] 记录 MRTR 流程图
- [ ] 记录安全机制说明
- [ ] 记录面试要点

#### Task 1.5：集成 MCP Memory 构建知识图谱 ⭐ 新增
- [ ] 创建 `src/storage/mcp_memory_adapter.py`
  - 封装 MCP Memory 的 5 个核心方法
  - `remember()` - 保存知识节点
  - `recall()` - 语义搜索
  - `link_memories()` - 建立关系
  - `promote()` - 推广到热缓存
  - `memory_stats()` - 统计信息
- [ ] 创建 `src/storage/storage_manager.py`
  - 实现双存储架构（MCP Memory + SQLite）
  - MCP Memory 存知识图谱
  - SQLite 存会话和项目元数据
- [ ] 实现知识关系图谱
  - 节点：知识点、项目、技术栈
  - 关系：belongs_to、related_to、prerequisite_of
- [ ] 编写数据迁移脚本 `scripts/migrate_to_mcp_memory.py`
  - 从 SQLite 导出现有数据
  - 转换为 MCP Memory 格式
  - 批量导入节点和关系
- [ ] 重构 MemoryManager
  - 替换 SQLite 操作为 MCP Memory 调用
  - 保留 SQLite 作为元数据存储

**技术架构**：
```
变更前：
MemoryManager → SQLite（知识、项目、会话全存这）

变更后：
MemoryManager → MCP Memory（知识图谱，支持语义搜索）
              → SQLite（会话记录、项目元数据）
```

**验收标准**：
```python
# 测试 1：创建知识节点
memory_id = await mcp_memory.save_knowledge(
    KnowledgePoint(title="FastAPI 依赖注入", ...)
)
assert memory_id is not None

# 测试 2：语义搜索
results = await mcp_memory.search_knowledge("如何实现路由")
assert len(results) > 0

# 测试 3：知识关系
await mcp_memory.link_knowledge("k-fastapi-001", "k-python-decorators-001", "requires")
graph = await mcp_memory.get_knowledge_graph("k-fastapi-001")
assert "k-python-decorators-001" in graph.related_nodes
```

**面试亮点**：
- "实现了知识图谱，不是简单的键值存储"
- "支持语义搜索，可以根据意图匹配相关知识"
- "采用双存储架构，各司其职"
- "用 MCP 标准协议，未来可以无缝切换其他知识库"

**预计工作量**：6-9 天（含 Task 1.5 的 2-3 天）

---

## Phase 2：Tasks 扩展（长任务进度追踪）（Week 2, 预计 3-4 天）

### 目标
实现长时间任务的后台执行和实时进度反馈

### 核心概念
```
触发任务 → 返回 taskHandle → 后台执行 → 客户端轮询进度 → 任务完成
```

### 任务清单

#### Task 2.1：任务管理器
- [ ] 创建 `src/tasks/task_manager.py`
  - 任务注册和存储
  - 任务状态管理（running/completed/failed）
  - 进度更新接口
- [ ] 创建 `src/tasks/task_executor.py`
  - 异步任务执行器
  - 错误处理和重试
  - 超时控制

**代码示例**：
```python
class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, TaskState] = {}
    
    def create_task(
        self, 
        name: str, 
        executor: Callable
    ) -> str:
        """创建新任务"""
        task_id = f"task-{uuid4().hex[:8]}"
        self.tasks[task_id] = TaskState(
            task_id=task_id,
            name=name,
            status="running",
            progress=0.0,
            created_at=datetime.utcnow()
        )
        
        # 启动后台任务
        asyncio.create_task(self._execute_task(task_id, executor))
        
        return task_id
    
    async def _execute_task(self, task_id: str, executor: Callable):
        """执行任务"""
        try:
            await executor(task_id, self)
            self.tasks[task_id].status = "completed"
        except Exception as e:
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].error = str(e)
    
    def update_progress(
        self, 
        task_id: str, 
        progress: float, 
        message: str = None
    ):
        """更新任务进度"""
        self.tasks[task_id].progress = progress
        if message:
            self.tasks[task_id].message = message
    
    def get_task(self, task_id: str) -> TaskState:
        """获取任务状态"""
        return self.tasks.get(task_id)
```

#### Task 2.2：实现长时间任务
- [ ] `analyze_project_deep`（项目深度分析）
- [ ] `vectorize_knowledge_graph`（知识图谱向量化）
- [ ] `research_technology_deep`（深度技术调研）

**实现示例（项目分析）**：
```python
@mcp_tool("analyze_project_deep")
async def analyze_project_deep(project_path: str) -> TaskHandleResult:
    """深度分析项目（5-10分钟）"""
    
    async def executor(task_id: str, task_mgr: TaskManager):
        # 阶段 1：扫描文件（10%）
        task_mgr.update_progress(task_id, 0.1, "扫描项目文件...")
        files = await scan_project_files(project_path)
        
        # 阶段 2：解析代码（30%）
        task_mgr.update_progress(task_id, 0.3, "解析代码结构...")
        ast_data = await parse_code_files(files)
        
        # 阶段 3：分析架构（60%）
        task_mgr.update_progress(task_id, 0.6, "分析架构模式...")
        architecture = await analyze_architecture(ast_data)
        
        # 阶段 4：提取亮点（80%）
        task_mgr.update_progress(task_id, 0.8, "提取项目亮点...")
        highlights = await extract_highlights(architecture)
        
        # 阶段 5：生成报告（100%）
        task_mgr.update_progress(task_id, 1.0, "生成分析报告...")
        report = await generate_report(highlights)
        
        # 保存结果
        task_mgr.tasks[task_id].result = report
    
    task_id = task_manager.create_task("analyze_project_deep", executor)
    
    return TaskHandleResult(
        task_id=task_id,
        status="running",
        progress=0.0,
        message="项目分析已启动...",
        eta_seconds=600  # 预计10分钟
    )
```

#### Task 2.3：实现任务查询工具
- [ ] `tasks/get`（查询任务状态）
- [ ] `tasks/list`（列出所有任务）
- [ ] `tasks/cancel`（取消任务）

```python
@mcp_tool("tasks/get")
async def get_task_status(task_id: str) -> MCPResult:
    """查询任务状态"""
    task = task_manager.get_task(task_id)
    
    if not task:
        raise MCPError(f"Task not found: {task_id}")
    
    return MCPResult(
        data={
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "result": task.result if task.status == "completed" else None
        }
    )
```

#### Task 2.4：测试 Tasks 功能
- [ ] 编写 `tests/test_tasks.py`
- [ ] 测试任务创建和执行
- [ ] 测试进度更新
- [ ] 测试任务取消
- [ ] 测试错误处理

#### Task 2.5：文档编写
- [ ] 创建 `docs/tasks-implementation.md`
- [ ] 记录任务执行流程
- [ ] 记录进度追踪机制

#### Task 2.6：集成 DeepSeek 做语义分析 ⭐ 新增
- [ ] 创建 `src/llm/deepseek_semantic.py`
  - 封装 DeepSeek API 调用
  - 实现知识点提取 Prompt
  - 实现难度评估 Prompt
- [ ] 创建 `src/llm/prompts.py`
  - `KNOWLEDGE_EXTRACTION_PROMPT` - 知识点提取
  - `DIFFICULTY_ESTIMATION_PROMPT` - 难度评估
  - Few-Shot 示例和 Chain-of-Thought
- [ ] 重构 SessionReviewer
  - 保留正则作为 fallback
  - 优先使用 DeepSeek 分析
  - 实现混合分析器（LLM + 正则）
- [ ] 作为 Long Task 实现
  - 调用 LLM 可能耗时 10-30 秒
  - 返回 TaskHandle，后台执行
  - 进度追踪：解析中 → 提取中 → 评分中
- [ ] 编写对比测试 `tests/test_semantic_comparison.py`
  - 对比正则和 LLM 两种方法
  - 测量准确率和耗时
  - 生成对比报告

**Prompt Engineering 要点**：
```python
# 1. 结构化输出（要求 JSON）
# 2. 少样本学习（Few-Shot）
# 3. 思维链（Chain-of-Thought）
# 4. 明确评分标准（0.3-0.9 区间说明）
```

**Fallback 策略**：
```python
class HybridSessionAnalyzer:
    """混合分析器：LLM 优先，正则 fallback"""
    async def analyze_session(self, session_content: str):
        try:
            return await self.llm_analyzer.extract(session_content)
        except (APIError, TimeoutError):
            logger.warning("LLM 分析失败，降级到正则")
            return self.regex_analyzer.extract(session_content)
```

**验收标准**：
```bash
# 1. 测试 DeepSeek 调用
python -c "
from src.llm.deepseek_semantic import DeepSeekSemantic
result = await DeepSeekSemantic().extract_knowledge('用户：什么是FastAPI？')
print(result)
"

# 2. 作为 Task 测试
curl -X POST http://localhost:8000/analyze_session_semantic -d '{"session_id": "sess-001"}'
# 返回：{"task_id": "task-abc123", "status": "running"}

# 3. 对比测试
pytest tests/test_semantic_comparison.py -v
# 输出对比报告：LLM 准确率 85% vs 正则 60%
```

**面试亮点**：
- "对比了正则和 LLM 两种方法，LLM 准确率提升 40%"
- "用 Prompt Engineering 控制输出格式，Few-Shot 提升质量"
- "实现混合策略：LLM 优先，失败时降级到正则"
- "作为 Long Task 实现，10-30 秒响应，避免阻塞"

**预计工作量**：5.5-8.5 天（含 Task 2.6 的 2-3 天）

---

## Phase 3：缓存策略（Week 3, 预计 2 天）

### 目标
为所有工具添加智能缓存，减少重复计算

### 任务清单

#### Task 3.1：缓存装饰器
- [ ] 创建 `src/cache/cache_decorator.py`
  - `@cacheable(ttl, scope)` 装饰器
  - 自动添加 `_meta.ttlMs` 和 `_meta.cacheScope`

**代码示例**：
```python
def cacheable(ttl_seconds: int, scope: str = "user"):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 自动添加缓存元数据
            if isinstance(result, MCPResult):
                result.meta["ttlMs"] = ttl_seconds * 1000
                result.meta["cacheScope"] = scope
            
            return result
        return wrapper
    return decorator
```

#### Task 3.2：为现有工具添加缓存
- [ ] 知识图谱查询（1小时，user）
- [ ] 项目结构信息（1天，user）
- [ ] GitHub 提交历史（5分钟，public）
- [ ] 技术文档查询（1天，public）

**使用示例**：
```python
@mcp_tool("search_knowledge")
@cacheable(ttl_seconds=3600, scope="user")
async def search_knowledge(query: str) -> MCPResult:
    """搜索知识图谱（1小时缓存）"""
    results = await memory_manager.search_nodes(query)
    return MCPResult(data={"results": results})
```

#### Task 3.3：缓存失效机制
- [ ] 实现 `invalidate_cache` 工具
- [ ] 知识更新时自动失效相关缓存

#### Task 3.4：测试和文档
- [ ] 编写 `tests/test_cache.py`
- [ ] 创建 `docs/cache-strategy.md`

**预计工作量**：1-2 天

---

## Phase 4：MCP Apps（交互式 UI）（Week 3-4, 预计 5-6 天）

### 目标
实现 4 个交互式 UI 界面，提升用户体验

### 核心概念
```
服务器返回 uiTemplate → 客户端渲染 UI → 用户交互 → 回传结果 → 服务器处理
```

### 任务清单

#### Task 4.1：UI 模板系统
- [ ] 创建 `src/ui/template_manager.py`
- [ ] 定义标准 UI 组件（Button、Input、Select、Chart）
- [ ] 创建模板渲染器

**模板示例**：
```python
class UITemplate:
    def __init__(self, template_id: str, data: Dict[str, Any]):
        self.template_id = template_id
        self.data = data
    
    def to_meta(self) -> Dict[str, Any]:
        return {
            "io.modelcontextprotocol/uiTemplate": {
                "templateId": self.template_id,
                "data": self.data
            }
        }
```

#### Task 4.2：实现 App 1 - 会话总结报告
- [ ] 创建 HTML 模板 `templates/session_summary.html`
- [ ] 展示内容：
  - 知识点列表
  - 学习时长
  - 掌握程度统计
  - 下次复习时间

```python
@mcp_tool("generate_session_summary_ui")
async def generate_session_summary_ui(session_id: str) -> UITemplateResult:
    """生成会话总结 UI"""
    session = await session_analyzer.get_session(session_id)
    
    template = UITemplate(
        template_id="com.learning-system.session-summary",
        data={
            "session_id": session_id,
            "knowledge_points": session.knowledge_points,
            "duration_minutes": session.duration,
            "mastery_stats": session.mastery_stats
        }
    )
    
    return UITemplateResult(template)
```

#### Task 4.3：实现 App 2 - 知识图谱可视化
- [ ] 创建 `templates/knowledge_graph.html`
- [ ] 使用 D3.js 或 Cytoscape.js 渲染图谱
- [ ] 支持节点点击查看详情

#### Task 4.4：实现 App 3 - 项目分析配置
- [ ] 创建 `templates/project_analysis_config.html`
- [ ] 支持选择分析策略（快速/标准/深度）
- [ ] 支持选择分析维度（架构/亮点/技术栈）

#### Task 4.5：实现 App 4 - 复习进度仪表盘
- [ ] 创建 `templates/review_dashboard.html`
- [ ] 展示今日复习任务
- [ ] 展示掌握程度分布
- [ ] 展示学习曲线

#### Task 4.6：测试和文档
- [ ] 编写 `tests/test_ui_templates.py`
- [ ] 创建 `docs/mcp-apps-guide.md`
- [ ] 录制演示视频（用于面试展示）

**预计工作量**：5-6 天

---

## Phase 5：Extensions 框架（Week 4-5, 预计 4-5 天）

### 目标
实现动态工具注册，根据项目类型加载对应的分析扩展

### 核心概念
```
客户端声明能力 → 服务器协商 → 动态注册工具 → 提供扩展功能
```

### 任务清单

#### Task 5.1：扩展系统框架
- [ ] 创建 `src/extensions/extension_manager.py`
- [ ] 创建 `src/extensions/base_extension.py`
- [ ] 实现能力协商机制

**代码示例**：
```python
class Extension(ABC):
    @property
    @abstractmethod
    def extension_id(self) -> str:
        """扩展ID"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """版本号"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """返回扩展能力"""
        pass
    
    @abstractmethod
    def register_tools(self, server: MCPServer):
        """注册工具"""
        pass

class ExtensionManager:
    def __init__(self):
        self.extensions: Dict[str, Extension] = {}
    
    def register(self, extension: Extension):
        """注册扩展"""
        self.extensions[extension.extension_id] = extension
    
    def negotiate_capabilities(
        self, 
        client_capabilities: Dict[str, Any]
    ) -> List[str]:
        """能力协商"""
        enabled = []
        for ext_id, ext in self.extensions.items():
            if ext_id in client_capabilities.get("extensions", {}):
                enabled.append(ext_id)
        return enabled
```

#### Task 5.2：实现 Python 分析扩展
- [ ] 创建 `src/extensions/python_analyzer.py`
- [ ] 能力：
  - 检测装饰器（FastAPI、Django）
  - 提取类型提示
  - 分析 async/await 使用

```python
class PythonAnalyzerExtension(Extension):
    extension_id = "io.learning-system.analyzer.python"
    version = "1.0.0"
    
    def get_capabilities(self):
        return {
            "analyze_decorators": True,
            "detect_framework": ["FastAPI", "Django", "Flask"],
            "extract_type_hints": True
        }
    
    def register_tools(self, server: MCPServer):
        @server.tool("analyze_python_decorators")
        async def analyze_decorators(file_path: str):
            # 分析装饰器逻辑
            pass
```

#### Task 5.3：实现 TypeScript 分析扩展
- [ ] 创建 `src/extensions/typescript_analyzer.py`
- [ ] 能力：
  - 检测 React 组件
  - 分析 Hooks 使用
  - 提取接口定义

#### Task 5.4：实现加密存储扩展（展示 OAuth）
- [ ] 创建 `src/extensions/secure_storage.py`
- [ ] 实现 OAuth 2.0 授权流程
- [ ] 实现 token 刷新机制

#### Task 5.5：测试和文档
- [ ] 编写 `tests/test_extensions.py`
- [ ] 创建 `docs/extensions-guide.md`

**预计工作量**：4-5 天

---

## Phase 6：集成测试和优化（Week 5-6, 预计 5-7 天）

### 目标
端到端测试所有功能，优化性能，编写完整文档

### 任务清单

#### Task 6.1：完整工作流测试
- [ ] 测试场景 1：学习工作流
  - 会话分析 → 知识保存 → MCP App 展示 → 复习计划生成
- [ ] 测试场景 2：项目分析工作流
  - MRTR 配置 → Tasks 执行 → 进度追踪 → 结果展示
- [ ] 测试场景 3：技术探索工作流
  - 深度调研（Task）→ 知识关联 → 缓存优化

#### Task 6.2：性能优化
- [ ] 优化知识图谱查询（添加索引）
- [ ] 优化 Task 执行（并发控制）
- [ ] 优化缓存命中率
- [ ] 测量和记录性能指标

#### Task 6.3：安全审计
- [ ] JWT 安全性测试
- [ ] Nonce 防重放测试
- [ ] 输入验证测试
- [ ] 权限控制测试

#### Task 6.4：文档完善
- [ ] 创建 `docs/mcp-2026-complete-guide.md`（总览）
- [ ] 创建 `docs/api-reference.md`（API 文档）
- [ ] 创建 `docs/deployment-guide.md`（部署指南）
- [ ] 创建 `docs/interview-highlights.md`（面试要点）

#### Task 6.5：演示准备
- [ ] 录制功能演示视频（5-10分钟）
- [ ] 准备 PPT（技术架构讲解）
- [ ] 编写简历项目描述
- [ ] 准备面试问答

**预计工作量**：5-7 天

---

## 总体时间表

| Phase | 内容 | 原计划 | 新增任务 | 更新后时间 |
|-------|------|--------|---------|-----------|
| Phase 0 | 基础设施重构 | 3-4 天 | Task 0.4 Hook (+1.5天) | **4.5-5.5 天** |
| Phase 1 | MRTR 实现 | 4-5 天 | Task 1.5 MCP Memory (+2-3天) | **6-9 天** |
| Phase 2 | Tasks 扩展 | 3-4 天 | Task 2.6 DeepSeek (+2-3天) | **5.5-8.5 天** |
| Phase 3 | 缓存策略 | 1-2 天 | - | 1-2 天 |
| Phase 4 | MCP Apps | 5-6 天 | - | 5-6 天 |
| Phase 5 | Extensions | 4-5 天 | - | 4-5 天 |
| Phase 6 | 集成测试 | 5-7 天 | - | 5-7 天 |

**原总计**：25-33 天（4-5 周）
**新总计**：31-43 天（5-6 周）
**新增时间**：6-10 天

### 🌟 新增任务说明

#### Task 0.4：Hook 自动捕获会话 (+1.5天)
- **价值**：实现自动化会话捕获，无需手动触发
- **借鉴**：ECC continuous-learning-v2 的 Hook 机制
- **亮点**：零侵入、JSONL 日志、30分钟空闲自动触发

#### Task 1.5：MCP Memory 知识图谱 (+2-3天)
- **价值**：从简单存储升级到知识图谱，支持语义搜索
- **架构**：双存储（MCP Memory + SQLite）
- **亮点**：节点关系、语义搜索、MCP 标准协议

#### Task 2.6：DeepSeek 语义分析 (+2-3天)
- **价值**：从正则匹配升级到 LLM 语义理解，准确率提升 40%
- **策略**：混合分析器（LLM 优先，正则 fallback）
- **亮点**：Prompt Engineering、Long Task、对比测试

---

## 简化方案（如果时间紧张）

### 最小可行实现（3 周 = 21 天）
- Phase 0 + Task 0.4（Hook）：**5 天**
- Phase 1 + Task 1.5（MCP Memory）：**7 天**
- Phase 2（不做 Task 2.6）：**3 天**
- Phase 3（缓存）：**2 天**
- Phase 6（测试文档）：**4 天**

**跳过**：MCP Apps、Extensions、DeepSeek 语义分析（只在文档中说明设计）

### 推荐方案（5 周 = 35 天）
- Phase 0-2（含三个新任务）：**18 天**
- Phase 3（缓存）：**2 天**
- Phase 4（MCP Apps，只做 1 个）：**3 天**
- Phase 5（Extensions，只做 Python）：**3 天**
- Phase 6（集成测试）：**5 天**
- 缓冲时间：**4 天**

**亮点**：保留所有核心创新（Hook、MCP Memory、DeepSeek），简化次要功能

---

## 验收标准

### Phase 完成标准
每个 Phase 必须满足：
1. ✅ 所有任务清单完成
2. ✅ 单元测试通过（覆盖率 >80%）
3. ✅ 集成测试通过
4. ✅ 文档编写完成
5. ✅ Code Review 通过

### 最终验收标准
1. ✅ 所有 MCP 2026-07-28 核心特性实现
2. ✅ 端到端测试通过
3. ✅ 性能达标（响应时间 <2s）
4. ✅ 安全测试通过
5. ✅ 完整文档和演示视频

---

## 下一步行动

**Phase 0 正在构建中** 🚧

完成 Phase 0 后，按以下顺序执行新增任务：

### 1️⃣ Task 0.4：Hook 自动捕获会话
**启动提示**：
```
开始 Task 0.4 - Hook 自动捕获会话系统

参考：docs/mcp-2026-implementation-plan.md（Task 0.4 部分）
工作量：1.5 天
```

### 2️⃣ Task 1.5：MCP Memory 集成
**启动提示**：
```
开始 Task 1.5 - 集成 MCP Memory 构建知识图谱

参考：docs/mcp-2026-implementation-plan.md（Task 1.5 部分）
工作量：2-3 天
前置条件：Phase 1 MRTR 基础完成
```

### 3️⃣ Task 2.6：DeepSeek 语义分析
**启动提示**：
```
开始 Task 2.6 - 集成 DeepSeek 做语义分析

参考：docs/mcp-2026-implementation-plan.md（Task 2.6 部分）
工作量：2-3 天
前置条件：Phase 2 TaskManager 完成
```

---

## 文档更新日志

**2026-08-03**：
- ✅ 新增 Task 0.4：Hook 自动捕获会话系统（+1.5天）
- ✅ 新增 Task 1.5：集成 MCP Memory 构建知识图谱（+2-3天）
- ✅ 新增 Task 2.6：集成 DeepSeek 做语义分析（+2-3天）
- ✅ 更新总体时间表：31-43 天（5-6 周）
- ✅ 更新简化方案：最小 3 周、推荐 5 周

**核心价值**：三个新任务实现了从"被动工具"到"主动学习助手"的质变
- Hook → 自动化
- MCP Memory → 知识图谱
- DeepSeek → 智能理解

准备好了就开始 Phase 0！完成后告诉我，我们继续推进！💪
