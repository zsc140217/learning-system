# MCP 2026-07-28 特性映射文档

## 文档目的

本文档详细记录了如何在 **Learning System** 项目中应用 MCP 2026-07-28 协议的所有核心特性。

---

## 一、特性覆盖清单

| MCP特性 | 应用场景 | 实现优先级 | 覆盖度 |
|---------|---------|-----------|--------|
| 无状态协议 | 所有Agent通信 | P0 | 100% |
| MRTR（多轮往返请求） | 危险操作确认 | P0 | 90% |
| Tasks扩展 | 长时间任务 | P1 | 80% |
| MCP Apps | 交互式UI | P1 | 70% |
| Extensions框架 | 功能扩展 | P2 | 60% |
| 缓存策略 | 知识查询 | P2 | 50% |
| Resources | 项目文件 | P3 | 30% |
| OAuth 2.0增强 | 加密存储 | P3 | 20% |

---

## 二、无状态协议应用

### 2.1 核心原则

```
所有状态通过ID显式传递，不依赖隐式状态
```

### 2.2 状态标识符设计

#### 会话状态
```json
{
  "session_id": "sess-20260731-143022",
  "format": "sess-{日期}-{时间}",
  "lifecycle": "会话结束后归档",
  "storage": "SQLite + 知识图谱"
}
```

#### 知识状态
```json
{
  "knowledge_id": "k-langchain-001",
  "format": "k-{技术名}-{序号}",
  "lifecycle": "永久存储",
  "storage": "Memory MCP (知识图谱)"
}
```

#### 项目状态
```json
{
  "project_id": "proj-travel-system",
  "format": "proj-{项目名}",
  "lifecycle": "永久存储",
  "storage": "SQLite + 知识图谱"
}
```

---

## 三、MRTR（多轮往返请求）应用

### 3.1 核心场景清单

| 场景 | 危险程度 | MRTR必需 | JWT必需 |
|------|---------|---------|---------|
| 删除知识节点 | 高 | ✅ | ✅ |
| 删除项目 | 高 | ✅ | ✅ |
| 重建索引 | 中 | ✅ | ✅ |
| 项目分析配置 | 低 | ✅ | ❌ |

### 3.2 场景1：知识删除确认

**第1轮：返回InputRequiredResult**
```json
{
  "result": {
    "_meta": {
      "io.modelcontextprotocol/inputRequired": {
        "message": "⚠️ 将删除知识节点：LangChain",
        "fields": [
          {"name": "confirm", "type": "boolean"},
          {"name": "archive_instead", "type": "boolean", "default": true}
        ],
        "requestState": "eyJhbGci...JWT..."
      }
    }
  }
}
```

**JWT Payload：**
```json
{
  "operation": "delete_knowledge",
  "knowledge_ids": ["k-langchain-001"],
  "timestamp": 1722334567890,
  "exp": 1722334867890,
  "nonce": "abc123xyz"
}
```

---

## 四、Tasks扩展应用

### 4.1 长时间任务清单

| 任务类型 | 预计耗时 | 进度追踪 | 优先级 |
|---------|---------|---------|--------|
| 项目代码扫描 | 5-10分钟 | ✅ | P1 |
| 知识图谱向量化 | 3-5分钟 | ✅ | P1 |
| 深度技术调研 | 10-15分钟 | ✅ | P2 |

### 4.2 Task 1: 项目代码扫描

**触发条件：**
```
用户：「分析我的差旅系统」
```

**返回Task：**
```json
{
  "result": {
    "_meta": {
      "io.modelcontextprotocol.tasks/taskHandle": {
        "task_id": "task-analysis-20260731-001",
        "status": "running",
        "progress": 0.0,
        "message": "扫描项目文件中..."
      }
    }
  }
}
```

**执行流程：**
```
阶段1（10%）：扫描文件
阶段2（30%）：解析代码
阶段3（60%）：分析架构
阶段4（80%）：提取亮点
阶段5（100%）：生成报告
```

---

## 五、MCP Apps应用

### 5.1 Apps清单

| App名称 | 用途 | 交互性 | 优先级 |
|---------|-----|--------|--------|
| 会话总结报告 | 展示学习成果 | 低 | P1 |
| 知识图谱可视化 | 节点关系图 | 高 | P1 |
| 项目分析配置 | 策略选择 | 高 | P1 |
| 复习进度仪表盘 | 进度展示 | 中 | P2 |

---

## 六、Extensions扩展框架

### 6.1 扩展清单

| Extension名称 | 功能 | 版本 | 优先级 |
|--------------|-----|------|--------|
| io.learning-system.analyzer.python | Python项目深度分析 | 1.0.0 | P1 |
| io.learning-system.analyzer.typescript | TypeScript项目分析 | 1.0.0 | P1 |
| io.learning-system.secure-storage | 加密存储（OAuth） | 1.0.0 | P3 |
| io.learning-system.sync | 多端同步 | 1.0.0 | P3 |

### 6.2 Extension 1: 语言分析扩展

**Python分析扩展**
```json
{
  "extensionId": "io.learning-system.analyzer.python",
  "version": "1.0.0",
  "capabilities": {
    "analyze_decorators": true,
    "detect_framework": ["FastAPI", "Django", "Flask"],
    "extract_type_hints": true
  }
}
```

**能力协商：**
```json
{
  "clientCapabilities": {
    "extensions": {
      "io.learning-system.analyzer.python": {"version": "1.0.0"},
      "io.learning-system.analyzer.typescript": {"version": "1.0.0"}
    }
  }
}
```

**动态工具注册：**
```python
if project_has_python_files:
    启用python扩展
    暴露工具：
    - analyze_python_decorators
    - detect_fastapi_routes
    - extract_pydantic_models
```

### 6.3 Extension 2: 加密存储扩展（展示OAuth特性）

**OAuth授权流程（SEP-2468, SEP-837, SEP-2351）**

**步骤1：发现授权服务器（SEP-2351）**
```
优先路径：/.well-known/oauth-authorization-server
回退路径：/.well-known/openid-configuration
```

**步骤2：动态注册（SEP-837）**
```json
{
  "client_name": "Learning System",
  "redirect_uris": ["http://localhost:8080/callback"],
  "application_type": "native",
  "token_endpoint_auth_method": "none"
}
```

**步骤3：授权请求（SEP-2207）**
```
scope: "read write offline_access"
        ↑ 请求refresh_token
```

**步骤4：验证iss参数（SEP-2468）**
```python
callback_params = parse_callback()
if callback_params["iss"] != expected_issuer:
    raise SecurityError("issuer不匹配")
```

**步骤5：Token刷新（SEP-2207）**
```json
{
  "grant_type": "refresh_token",
  "refresh_token": "xyz..."
}
```

**步骤6：Scope累积（SEP-2350）**
```
第1次授权：scope="read"
第2次授权：scope="write"
→ 最终权限：read + write（累积）
```

### 6.4 Extension 3: 多端同步扩展

**冲突解决（MRTR + MCP App）**
```json
{
  "_meta": {
    "io.modelcontextprotocol/inputRequired": {
      "message": "知识图谱冲突",
      "fields": [
        {
          "name": "resolution",
          "type": "string",
          "enum": ["keep_local", "use_remote", "merge"]
        }
      ],
      "uiTemplate": {
        "templateId": "com.learning-system.conflict-resolver",
        "data": {
          "local_version": {"mastery": 4, "last_review": "2026-07-31"},
          "remote_version": {"mastery": 3, "last_review": "2026-07-30"}
        }
      }
    }
  }
}
```

---

## 七、缓存策略

### 7.1 缓存场景清单

| 数据类型 | TTL | 缓存范围 | 失效条件 |
|---------|-----|---------|---------|
| 知识图谱查询结果 | 1小时 | user | 知识更新 |
| 项目结构信息 | 1天 | user | 代码变更 |
| GitHub提交历史 | 5分钟 | public | 无 |
| 技术文档（Context7） | 1天 | public | 无 |

### 7.2 实现示例

**场景1：知识图谱查询**
```python
@Tool(name="search_knowledge")
def search_knowledge(query: str):
    result = memory_mcp.search_nodes(query)
    return {
        "nodes": result,
        "_meta": {
            "ttlMs": 3600000,  # 1小时
            "cacheScope": "user"
        }
    }
```

**场景2：项目结构**
```python
@Tool(name="get_project_structure")
def get_project_structure(project_id: str):
    structure = analyze_structure(project_id)
    return {
        "structure": structure,
        "_meta": {
            "ttlMs": 86400000,  # 1天
            "cacheScope": "user"
        }
    }
```

**场景3：不缓存的数据**
```python
@Tool(name="get_review_plan")
def get_review_plan(date: str):
    # 复习计划每次都重新计算
    plan = generate_plan(date)
    return {
        "plan": plan,
        "_meta": {
            "ttlMs": 0  # 不缓存
        }
    }
```

---

## 八、Resources应用

### 8.1 Resources清单

| Resource类型 | URI格式 | MimeType | 优先级 |
|-------------|---------|----------|--------|
| 项目文件 | file:///path/to/project/... | text/plain | P3 |
| 知识文档 | memory://knowledge/{id} | text/markdown | P3 |
| 会话记录 | session://sess-{id} | application/json | P3 |

### 8.2 实现示例

**暴露项目文件为Resource**
```python
# Server注册Resources
server.add_resource({
    "uri": "file:///path/to/travel-system/src/agents/orchestrator_agent.py",
    "name": "Orchestrator Agent源码",
    "mimeType": "text/plain",
    "description": "差旅系统的Agent编排器"
})
```

**Client读取Resource**
```json
{
  "method": "resources/read",
  "params": {
    "uri": "file:///path/to/travel-system/src/agents/orchestrator_agent.py"
  }
}
```

**返回内容**
```json
{
  "contents": [
    {
      "uri": "file://...",
      "mimeType": "text/plain",
      "text": "# Orchestrator Agent代码..."
    }
  ]
}
```

---

## 九、实施优先级总结

### Phase 1：核心功能（Week 1-2）

**P0：必须实现**
- ✅ 无状态协议（所有ID设计）
- ✅ MRTR基础（知识删除、项目分析配置）
- ✅ 第一个MCP App（会话总结报告）
- ✅ Session Agent基础版
- ✅ Memory Agent基础版

**关键里程碑：**
```
能够：
1. 会话结束自动总结
2. 保存到知识图谱
3. 用MCP App展示总结
```

### Phase 2：完整Agent系统（Week 3-4）

**P1：重要功能**
- ✅ Tasks扩展（项目扫描、向量化）
- ✅ Project Agent + Explorer Agent
- ✅ 所有MCP Apps（知识图谱、进度仪表盘）
- ✅ MRTR完整实现（JWT验证）

**关键里程碑：**
```
能够：
1. 分析项目代码
2. 深度技术调研
3. 可视化知识图谱
4. 追踪学习进度
```

### Phase 3：高级特性（Week 5-6）

**P2-P3：增强功能**
- ✅ Extensions（语言分析扩展）
- ✅ 缓存策略优化
- ✅ OAuth加密存储（可选）
- ✅ 多端同步（可选）
- ✅ Resources暴露（可选）

---

## 十、开发检查清单

### MCP协议合规性检查

#### 无状态协议 ✓
- [ ] 所有状态通过ID显式传递
- [ ] 不依赖session/connection状态
- [ ] 每个请求携带必要的_meta信息

#### MRTR ✓
- [ ] 危险操作返回InputRequiredResult
- [ ] JWT签名和验证实现
- [ ] 5分钟过期时间
- [ ] Nonce防重放攻击
- [ ] 用户确认后验证参数一致性

#### Tasks ✓
- [ ] 返回taskHandle
- [ ] 实时更新progress
- [ ] 提供eta预估
- [ ] 支持tasks/get查询进度
- [ ] 任务完成后通知

#### MCP Apps ✓
- [ ] 声明uiTemplate
- [ ] 安全沙箱（CSP）
- [ ] postMessage通信
- [ ] 交互结果通过MCP协议回传

#### Extensions ✓
- [ ] 客户端声明capabilities
- [ ] 服务端根据能力动态注册工具
- [ ] 版本协商

#### 缓存 ✓
- [ ] 返回ttlMs
- [ ] 声明cacheScope（user/public）
- [ ] 适当的失效策略

---

## 十一、测试场景

### 场景1：完整的学习工作流
```
1. 用户学习MCP协议（会话中）
2. Session Agent分析会话
3. Memory Agent保存到知识图谱
4. MCP App展示会话总结
5. 3天后：Memory Agent生成复习计划
6. 用户复习MCP协议
7. Memory Agent更新掌握程度
```

### 场景2：项目分析工作流
```
1. 用户：「分析差旅系统」
2. MRTR：选择分析策略（MCP App）
3. Task：后台扫描代码（10分钟）
4. Project Agent提取亮点
5. Memory Agent关联技术知识
6. MCP App展示项目报告
```

### 场景3：技术探索工作流
```
1. 用户：「调研vLLM」
2. MCP App：选择调研方向
3. Task：深度调研（15分钟）
4. Explorer Agent生成报告
5. Memory Agent创建技术节点
6. Tech Radar更新
```

---

## 文档完成 ✅

本文档详细记录了MCP 2026-07-28协议在Learning System项目中的应用设计。

**下次会话待办：**
1. 查找ECC可用Skills
2. 映射Skills到4个Agent
3. 编写详细的架构设计文档
4. 编写知识图谱Schema文档

**参考文档：**
- `mcp\架构思路.md`（整体架构）
- `docs\MCP_2026-07-28_技术规范.md`（协议规范）
