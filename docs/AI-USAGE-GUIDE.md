# Learning System MCP Server - AI 使用指南

## 项目概述

基于 MCP 2026-07-28 协议的学习系统，支持知识图谱管理、会话分析和任务管理。

**核心特点：**
- 双传输层：stdio（Claude Desktop）+ HTTP（Web/CLI）
- 无状态设计
- 17 个 MCP 工具
- Web 可视化客户端

---

## 快速启动

### 启动 HTTP 服务器

```bash
cd E:\Desktop\learning-system\mcp-server
python http_server.py
```

访问：http://localhost:8080

---

## 17 个可用工具

1. `analyze_session` - 分析会话内容
2. `save_knowledge` - 保存知识点
3. `search_knowledge` - 搜索知识图谱
4. `get_knowledge_graph` - 获取知识图谱
5. `delete_knowledge` - 删除知识（需确认）
6. `track_project` - 追踪项目
7. `delete_project` - 删除项目（需确认）
8. `explore_technology` - 探索技术
9. `rebuild_index` - 重建索引（需确认）
10. `analyze_project_deep` - 深度分析项目（长任务）
11. `vectorize_knowledge_graph` - 向量化图谱（长任务）
12. `research_technology_deep` - 深度调研（长任务）
13. `tasks/get` - 查询任务状态
14. `tasks/list` - 列出任务
15. `tasks/cancel` - 取消任务
16. `invalidate_cache` - 失效缓存
17. `cache_stats` - 缓存统计

---

## API 调用示例

### 列出工具

```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

### 调用工具

```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"cache_stats","arguments":{}},"id":2}'
```

---

## 架构说明

```
MCPServer (核心)
    |
    +-- StdioTransport (Claude Desktop)
    +-- HTTPTransport (Web/CLI)
```

---

## MCP 2026 特性

1. **无状态** - 无 session ID
2. **MRTR** - 危险操作二次确认
3. **Tasks** - 异步长任务（10分钟级）
4. **MCP Apps** - UI 模板支持

---

## 文件结构

```
mcp-server/
├── http_server.py       # HTTP 入口
├── server.py            # stdio 入口
├── src/protocol/        # 协议层
├── src/tools/           # UI 工具
├── static/index.html    # Web 客户端
└── templates/           # UI 模板
```

---

## 配置

```python
# config.py
http_host = "0.0.0.0"
http_port = 8080
jwt_secret = "auto-generated"
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
