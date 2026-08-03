# 缓存策略实现文档

## 概述

Phase 3 实现了 MCP 2026-07-28 协议的缓存策略，通过 `_meta.ttlMs` 和 `_meta.cacheScope` 字段告知客户端如何缓存结果，减少重复计算。

## 核心组件

### 1. CacheManager（缓存管理器）

**位置**: `src/cache/cache_manager.py`

**职责**:
- 跟踪工具缓存配置
- 管理缓存失效标记
- 自动清理过期标记

**关键方法**:

```python
# 注册工具缓存配置
cache_manager.register_tool("search_knowledge", ttl_seconds=3600, scope="user")

# 失效单个或多个缓存
cache_manager.invalidate(["search_knowledge:python", "get_project:proj-001"])

# 按模式失效（支持通配符）
cache_manager.invalidate_pattern("search_knowledge:*")

# 检查是否失效
is_invalid = cache_manager.is_invalidated("search_knowledge:python")

# 获取统计信息
stats = cache_manager.get_stats()
```

### 2. @cacheable 装饰器

**位置**: `src/cache/cache_decorator.py`

**作用**: 自动为 MCP 工具添加缓存元数据

**用法**:

```python
from src.cache import cacheable
from src.protocol.result_types import MCPResult

@cacheable(ttl_seconds=3600, scope="user")
async def search_knowledge(query: str) -> MCPResult:
    # 查询知识图谱
    return MCPResult(data={"results": [...]})
```

**参数**:
- `ttl_seconds`: 缓存生存时间（秒）
- `scope`: 缓存范围
  - `"user"`: 用户级缓存（默认）
  - `"session"`: 会话级缓存
  - `"public"`: 公共缓存（所有用户共享）

**效果**:

装饰器会自动在 `MCPResult` 的 `meta` 中添加：

```python
{
    "ttlMs": 3600000,      # 转换为毫秒
    "cacheScope": "user"
}
```

## 已实现的缓存策略

### 工具缓存配置

| 工具 | TTL | Scope | 原因 |
|------|-----|-------|------|
| `analyze_session` | 5分钟 | session | 会话分析结果，会话内短期有效 |
| `search_knowledge` | 1小时 | user | 知识搜索结果，用户级缓存 |
| `get_knowledge_graph` | 1小时 | user | 知识图谱，用户级缓存 |
| `track_project` | 1天 | user | 项目信息，变化频率低 |
| `explore_technology` | 1小时 | public | 技术资源，所有用户共享 |
| `tasks/get` | 5秒/1分钟 | user | 任务状态，运行中5秒刷新，完成后1分钟 |
| `tasks/list` | 10秒 | user | 任务列表，短期缓存 |
| `cache_stats` | 10秒 | user | 统计信息，实时性要求不高 |

### 不缓存的操作

以下操作不添加缓存元数据（ttlMs=0 或不设置）：

- `save_knowledge`: 写操作，每次都执行
- `delete_knowledge`: 危险操作，需要实时确认
- `delete_project`: 危险操作，需要实时确认
- `rebuild_index`: 长任务，不适合缓存
- `tasks/cancel`: 控制操作，立即生效

## 自动缓存失效

### 知识更新时自动失效

当知识被保存或删除时，自动失效相关缓存：

```python
@server.tool("save_knowledge")
async def save_knowledge(...):
    # 保存知识点
    # ...
    
    # 自动失效知识搜索和图谱缓存
    cache_manager.invalidate_pattern("search_knowledge:*")
    cache_manager.invalidate_pattern("get_knowledge_graph:*")
```

同样的逻辑也应用于 `delete_knowledge` 工具。

### 手动失效缓存

用户可以通过 `invalidate_cache` 工具手动失效缓存：

```python
# 失效特定工具的所有缓存
await invalidate_cache(tools=["search_knowledge", "get_knowledge_graph"])

# 失效特定模式的缓存
await invalidate_cache(patterns=["search_knowledge:python", "get_project:proj-*"])
```

## 缓存清理

### 自动清理

CacheManager 启动后会自动清理过期的失效标记：

- **清理间隔**: 每1小时
- **保留时间**: 24小时
- **清理对象**: 失效标记（`_invalidation_marks`）

### 生命周期管理

```python
# 启动时
await cache_manager.start_cleanup_task()

# 关闭时
await cache_manager.stop_cleanup_task()
```

## MCP 协议层实现

### 响应格式

带缓存元数据的 MCP 响应：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "results": [...],
    "count": 5
  },
  "_meta": {
    "ttlMs": 3600000,
    "cacheScope": "user"
  }
}
```

### 客户端行为

客户端根据 `_meta` 字段决定缓存策略：

1. **ttlMs**: 缓存生存时间（毫秒）
   - 客户端在 ttl 内直接返回缓存，不发送请求
   - ttl 过期后重新请求服务器

2. **cacheScope**: 缓存范围
   - `"user"`: 按用户隔离缓存
   - `"session"`: 按会话隔离缓存
   - `"public"`: 全局共享缓存

## 测试

### 运行测试

```bash
cd mcp-server
python -m pytest ../tests/test_cache.py -v
```

### 测试覆盖

- ✅ CacheManager 基础功能（注册、失效、统计）
- ✅ 模式匹配失效（通配符支持）
- ✅ 自动清理过期标记
- ✅ @cacheable 装饰器（元数据添加）
- ✅ 不同缓存范围（user/session/public）
- ✅ 无效范围检测
- ✅ 非 MCPResult 类型处理
- ✅ 集成测试（失效流程、清理任务）
- ✅ 常见 TTL 值验证

**测试结果**: 12/12 通过 ✅

## 使用示例

### 示例 1: 添加缓存到新工具

```python
from src.cache import cacheable

@server.tool("get_user_stats")
@cacheable(ttl_seconds=600, scope="user")  # 10分钟用户级缓存
async def get_user_stats(user_id: str) -> MCPResult:
    stats = await compute_stats(user_id)
    return MCPResult(data=stats)
```

### 示例 2: 知识更新后失效缓存

```python
@server.tool("update_knowledge")
async def update_knowledge(knowledge_id: str, data: dict) -> MCPResult:
    # 更新知识
    await memory_manager.update(knowledge_id, data)
    
    # 失效相关缓存
    cache_manager.invalidate_pattern("search_knowledge:*")
    cache_manager.invalidate_pattern(f"get_knowledge:{knowledge_id}")
    
    return MCPResult(data={"status": "updated"})
```

### 示例 3: 查看缓存统计

```python
# 调用 cache_stats 工具
stats = await cache_stats()

# 返回结果
{
    "registered_tools": 8,
    "invalidated_caches": 3,
    "tools": {
        "search_knowledge": [3600, "user"],
        "get_knowledge_graph": [3600, "user"],
        ...
    }
}
```

## 面试要点

### 1. 为什么需要缓存策略？

**问题**: 反复查询相同的知识会导致什么问题？

**回答**:
- 每次查询都要访问 MCP Memory，增加延迟
- 重复计算浪费资源（语义搜索、图谱遍历）
- 用户体验差（等待时间长）

**解决方案**: 通过 `_meta` 字段告知客户端缓存策略，客户端在 ttl 内直接返回缓存。

### 2. 如何设计 TTL 值？

**原则**:
- 查询操作：较长 TTL（1小时 - 1天）
- 写操作：不缓存（ttl=0）
- 实时数据：短 TTL（5-10秒）
- 公共资源：长 TTL（1天+），scope=public

**示例**:
- 知识搜索：1小时（数据更新频率较低）
- 任务状态：5秒（运行中需要实时更新）
- 项目信息：1天（几乎不变）

### 3. 自动失效机制

**问题**: 如果用户添加了新知识，旧的搜索缓存怎么办？

**回答**: 实现了自动失效机制：

```python
# 保存知识时
cache_manager.invalidate_pattern("search_knowledge:*")
cache_manager.invalidate_pattern("get_knowledge_graph:*")
```

所有知识相关的缓存都会被标记为失效，客户端下次会重新请求。

### 4. 缓存范围的选择

**user vs session vs public**:

- `user`: 用户私有数据（知识图谱、项目列表）
- `session`: 会话内临时数据（会话分析结果）
- `public`: 全局共享数据（技术文档、公开资源）

### 5. 与 LLM Cache 的区别

**LLM Cache** (`src/utils/llm_cache.py`):
- 内部优化，减少 API 调用
- 基于 (messages, model, temperature) 哈希
- 用户不可见

**MCP Cache** (Phase 3):
- 协议层规范，告知客户端缓存策略
- 基于 `_meta.ttlMs` 和 `_meta.cacheScope`
- 客户端实现缓存逻辑

**互补关系**: LLM Cache 优化内部 API 成本，MCP Cache 优化用户体验。

## 下一步

Phase 3 完成后，继续：

- **Phase 4**: MCP Apps（交互式 UI）
- **Phase 5**: Extensions（动态工具注册）
- **Phase 6**: 集成测试和优化

---

**文档版本**: 1.0  
**完成日期**: 2026-08-03  
**Phase 状态**: ✅ Phase 3 完成
