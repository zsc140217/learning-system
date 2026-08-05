# API 参考文档

**文档版本**: 1.0.0  
**更新时间**: 2026-08-04  
**适用项目**: Learning System

---

## 工具总览

| 分类 | 工具数量 | 说明 |
|-----|---------|------|
| 核心工具 | 4 | 基础功能（会话分析、知识保存等） |
| MRTR 工具 | 3 | 危险操作需二次确认 |
| Tasks 工具 | 3 | 长任务管理（5-15 分钟） |
| 查询工具 | 3 | 任务状态查询 |
| Extension 工具 | 13 | 动态扩展工具 |
| **总计** | **26** | - |

---

## 核心工具

### 1. analyze_session

分析会话内容，提取知识点和学习路径。

**参数**:
- `session_id` (string, 必需): 会话 ID，格式 `sess-YYYYMMDD-HHMMSS`
- `options` (object, 可选): 分析选项
  - `depth` (string): 分析深度 `quick|standard|deep`，默认 `standard`
  - `extract_projects` (boolean): 是否提取项目引用，默认 `true`

**返回**:
```json
{
  "session_id": "sess-20260804-143022",
  "knowledge_points": [
    {
      "title": "FastAPI 依赖注入",
      "category": "web_framework",
      "mastery": 0.7
    }
  ],
  "projects": ["proj-travel-system"],
  "technologies": ["FastAPI", "Pydantic"],
  "duration_minutes": 45
}
```

**缓存**: 5 分钟，用户级别

---

### 2. save_knowledge

保存知识点到知识图谱（MCP Memory）。

**参数**:
- `knowledge` (object, 必需): 知识点对象
  - `title` (string): 知识点标题
  - `category` (string): 分类 `framework|library|concept|pattern`
  - `content` (string): 详细内容
  - `tags` (array): 标签列表
  - `related_to` (array, 可选): 相关知识点 ID
  - `prerequisite_of` (array, 可选): 前置依赖 ID

**返回**:
```json
{
  "knowledge_id": "k-fastapi-001",
  "status": "saved",
  "relationships_created": 2
}
```

**缓存**: 不缓存

---

### 3. track_project

追踪项目进展，分析代码变化。

**参数**:
- `project_id` (string, 必需): 项目 ID，格式 `proj-{项目名}`
- `project_path` (string, 必需): 项目路径（绝对路径）
- `analysis_type` (string, 可选): 分析类型
  - `quick`: 快速扫描（文件统计）
  - `standard`: 标准分析（架构提取）
  - `deep`: 深度分析（启动长任务）

**返回**:
```json
{
  "project_id": "proj-travel-system",
  "structure": {
    "total_files": 42,
    "languages": {"Python": 35, "JavaScript": 7}
  },
  "highlights": ["Multi-Agent 架构设计"],
  "last_updated": "2026-08-04T14:30:22Z"
}
```

**缓存**: 1 天，用户级别

---

### 4. explore_technology

探索新技术，生成学习路径。

**参数**:
- `technology` (string, 必需): 技术名称
- `focus_areas` (array, 可选): 关注领域 `["basics", "advanced", "best_practices", "production"]`
- `depth` (string, 可选): 调研深度 `overview|detailed`

**返回**:
```json
{
  "technology": "FastAPI",
  "learning_path": [
    {"title": "Python 基础", "estimated_hours": 20}
  ],
  "resources": [
    {"type": "official_docs", "url": "https://fastapi.tiangolo.com"}
  ]
}
```

**缓存**: 1 天，公共级别

---

## MRTR 工具

### 5. delete_knowledge

删除知识节点（危险操作，需要二次确认）。

**参数**:
- `knowledge_ids` (array, 必需): 要删除的知识点 ID 列表
- `request_state` (string, 可选): JWT token（第 2 轮提供）

**第 1 轮返回**:
```json
{
  "_meta": {
    "io.modelcontextprotocol/inputRequired": {
      "message": "⚠️ 将删除 3 个知识节点，此操作不可逆",
      "fields": [
        {"name": "confirm", "type": "boolean", "label": "确认删除"}
      ],
      "requestState": "eyJhbGci..."
    }
  }
}
```

**第 2 轮返回**:
```json
{
  "deleted_count": 3,
  "status": "completed"
}
```

**缓存**: 不缓存

---

### 6. delete_project

删除项目及相关数据（危险操作）。

**参数**:
- `project_id` (string, 必需): 项目 ID
- `request_state` (string, 可选): JWT token（第 2 轮提供）

**返回**: 与 `delete_knowledge` 类似

**缓存**: 不缓存

---

### 7. rebuild_index

重建知识图谱索引（耗时操作）。

**参数**:
- `scope` (string, 必需): 重建范围 `all|knowledge|projects`
- `request_state` (string, 可选): JWT token（第 2 轮提供）

**返回**:
```json
{
  "indexed_nodes": 1250,
  "duration_seconds": 45,
  "status": "completed"
}
```

**缓存**: 不缓存

---

## Tasks 工具

### 8. analyze_project_deep

深度分析项目代码（5-10 分钟长任务）。

**参数**:
- `project_path` (string, 必需): 项目路径
- `options` (object, 可选): 分析选项
  - `include_tests` (boolean): 是否分析测试代码，默认 `true`
  - `extract_patterns` (boolean): 是否提取设计模式，默认 `true`

**返回**:
```json
{
  "_meta": {
    "io.modelcontextprotocol.tasks/taskHandle": {
      "task_id": "task-abc123de",
      "status": "running",
      "progress": 0.0,
      "eta_seconds": 600
    }
  }
}
```

**任务完成后结果** (通过 tasks/get 获取):
```json
{
  "architecture_patterns": ["Multi-Agent", "Event-Driven"],
  "highlights": ["完整的 MCP 2026 实现"],
  "code_quality": {
    "total_lines": 10142,
    "test_coverage": 100
  }
}
```

**缓存**: 1 小时，用户级别

---

### 9. vectorize_knowledge_graph

向量化知识图谱（3-5 分钟长任务）。

**参数**:
- `scope` (string, 可选): 向量化范围 `all|recent|category`

**返回**:
```json
{
  "_meta": {
    "io.modelcontextprotocol.tasks/taskHandle": {
      "task_id": "task-xyz789ab",
      "status": "running",
      "progress": 0.0,
      "eta_seconds": 300
    }
  }
}
```

**缓存**: 不缓存

---

### 10. research_technology_deep

深度技术调研（10-15 分钟长任务）。

**参数**:
- `technology` (string, 必需): 技术名称
- `research_dimensions` (array, 必需): 调研维度 `["history", "ecosystem", "best_practices", "case_studies", "comparison"]`

**返回**:
```json
{
  "_meta": {
    "io.modelcontextprotocol.tasks/taskHandle": {
      "task_id": "task-def456gh",
      "status": "running",
      "progress": 0.0,
      "eta_seconds": 900
    }
  }
}
```

**缓存**: 1 天，公共级别

---

## 查询工具

### 11. tasks/get

查询任务状态。

**参数**:
- `task_id` (string, 必需): 任务 ID

**返回**:
```json
{
  "task_id": "task-abc123de",
  "status": "running",
  "progress": 0.6,
  "message": "分析架构模式...",
  "result": null,
  "eta_seconds": 240
}
```

**缓存**: 不缓存

---

### 12. tasks/list

列出所有任务。

**参数**:
- `status` (string, 可选): 过滤状态 `running|completed|failed|all`，默认 `all`

**返回**:
```json
{
  "tasks": [
    {
      "task_id": "task-abc123de",
      "name": "analyze_project_deep",
      "status": "running",
      "progress": 0.6
    }
  ],
  "total": 2
}
```

**缓存**: 不缓存

---

### 13. tasks/cancel

取消正在运行的任务。

**参数**:
- `task_id` (string, 必需): 任务 ID

**返回**:
```json
{
  "task_id": "task-abc123de",
  "status": "cancelled"
}
```

**缓存**: 不缓存

---

## Extension 工具

Extension 工具需要客户端声明支持对应扩展后才能使用。

### Python 分析器 (io.learning-system.analyzer.python v1.0.0)

#### 14. analyze_python_decorators

分析 Python 文件中的装饰器使用。

**参数**: `file_path` (string, 必需)

**返回**:
```json
{
  "decorators": [
    {"name": "app.post", "line": 15, "type": "route"}
  ],
  "total": 2
}
```

---

#### 15. detect_python_framework

检测 Python 项目使用的框架。

**参数**: `project_path` (string, 必需)

**返回**:
```json
{
  "framework": "FastAPI",
  "version": "0.104.1",
  "confidence": 0.95
}
```

---

#### 16. extract_python_type_hints

提取 Python 文件的类型提示。

**参数**: `file_path` (string, 必需)

**返回**:
```json
{
  "functions": [
    {
      "name": "analyze_session",
      "parameters": [{"name": "session_id", "type": "str"}],
      "return_type": "MCPResult"
    }
  ],
  "type_coverage": 0.85
}
```

---

#### 17. analyze_python_async

分析 Python 异步代码使用。

**参数**: `file_path` (string, 必需)

**返回**:
```json
{
  "async_functions": 12,
  "await_expressions": 45,
  "asyncio_usage": ["create_task", "gather"]
}
```

---

### TypeScript 分析器 (io.learning-system.analyzer.typescript v1.0.0)

#### 18. detect_react_components

检测 React 组件。

**参数**: `file_path` (string, 必需)

**返回**:
```json
{
  "components": [
    {
      "name": "SessionSummary",
      "type": "function",
      "hooks": ["useState", "useEffect"]
    }
  ]
}
```

---

#### 19. analyze_react_hooks

分析 React Hooks 使用。

**参数**: `file_path` (string, 必需)

**返回**:
```json
{
  "hooks": [
    {"name": "useState", "count": 3, "type": "builtin"}
  ]
}
```

---

#### 20. extract_typescript_interfaces

提取 TypeScript 接口定义。

**参数**: `file_path` (string, 必需)

**返回**:
```json
{
  "interfaces": [
    {
      "name": "MCPResult",
      "properties": [
        {"name": "data", "type": "any"}
      ]
    }
  ]
}
```

---

#### 21. detect_frontend_framework

检测前端框架。

**参数**: `project_path` (string, 必需)

**返回**:
```json
{
  "framework": "React",
  "version": "18.2.0",
  "bundler": "Vite"
}
```

---

### 安全存储扩展 (io.learning-system.secure-storage v1.0.0)

#### 22. oauth_initiate

发起 OAuth 2.0 授权流程。

**参数**: 
- `provider` (string, 必需): `github|google|custom`
- `scopes` (array, 必需): 权限范围

**返回**:
```json
{
  "authorization_url": "https://provider.com/oauth/authorize?...",
  "state": "csrf-token-xyz"
}
```

---

#### 23. oauth_complete

完成 OAuth 授权。

**参数**: 
- `code` (string, 必需): 授权码
- `state` (string, 必需): CSRF token

**返回**:
```json
{
  "access_token": "encrypted_token",
  "expires_in": 3600
}
```

---

#### 24. oauth_refresh_token

刷新 access token。

**参数**: `refresh_token` (string, 必需)

**返回**:
```json
{
  "access_token": "new_encrypted_token",
  "expires_in": 3600
}
```

---

#### 25. secure_store_credential

加密存储凭证。

**参数**: 
- `key` (string, 必需): 凭证键名
- `value` (string, 必需): 凭证值

**返回**:
```json
{
  "key": "github_token",
  "encrypted": true
}
```

---

#### 26. secure_retrieve_credential

检索加密凭证。

**参数**: `key` (string, 必需)

**返回**:
```json
{
  "key": "github_token",
  "value": "decrypted_value"
}
```

---

## 总结

本文档涵盖了 Learning System 的所有 26 个 MCP 工具。

**下一步**: 查看 [部署指南](deployment-guide.md)。
