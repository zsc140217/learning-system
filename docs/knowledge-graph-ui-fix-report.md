# 知识图谱 UI 显示问题排查与修复报告

## 📋 问题概述

**症状：** 前端点击 "Knowledge Graph" 按钮后无法显示知识图谱可视化界面

**根本原因：** MCP 2026 协议的 UI Template 在数据传输链路中丢失，同时 React 严格模式导致 WebSocket 消息处理器失效

**修复时间：** 2026-08-06  
**涉及模块：** MCP Server、WebSocket Server、MCP HTTP Client、前端 WebSocket/MCP Client

---

## 🔍 问题排查过程

### 1. 初步定位：协议链路追踪

#### 1.1 前端请求验证

前端发送的请求格式正确：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "ui_knowledge_graph",
    "arguments": {}
  }
}
```

#### 1.2 MCP Server 端测试

直接测试 MCP Server HTTP 接口：
```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ui_knowledge_graph","arguments":{}}}'
```

**发现：** MCP Server 正确返回 `_meta` 字段，数据结构完整：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {...},
  "_meta": {
    "io.modelcontextprotocol/uiTemplate": {
      "templateId": "com.learning-system.knowledge-graph",
      "template": "<html>...</html>",
      "data": {
        "nodes": [...],
        "edges": [...]
      }
    }
  }
}
```

**结论：** MCP Server 层面没有问题。

---

### 2. 数据传输链路分析

完整的数据流：
```
前端 → WebSocket → MCP Client (stdio) → MCP Server → 响应
```

#### 2.1 发现问题 1：MCP Server 返回结构错误

**文件：** `mcp-server/server.py:510-531`

**问题：**
```python
# 错误：访问不存在的属性
result = await generate_knowledge_graph_ui(...)
return MCPResult(
    data=result.data,  # ❌ 属性名错误，应该是 template_data
    meta={
        "io.modelcontextprotocol/uiTemplate": {
            "template": result.template,  # ❌ 应该加载 HTML 文件内容
            "data": result.data
        }
    }
)
```

**修复：**
```python
# 正确：加载 HTML 模板内容
from pathlib import Path
template_html = ""
if result.template_path:
    template_file = Path(result.template_path)
    if template_file.exists():
        template_html = template_file.read_text(encoding="utf-8")

return MCPResult(
    data=result.template_data,  # ✓ 正确属性名
    meta={
        "io.modelcontextprotocol/uiTemplate": {
            "templateId": result.template_id,
            "template": template_html,  # ✓ HTML 内容
            "data": result.template_data
        }
    }
)
```

**MCP 2026 协议要点：**
- `template` 必须是 HTML 字符串，不能是文件路径
- `_meta` 字段用于传递协议扩展信息（UI Template、MRTR、Tasks）

---

#### 2.2 发现问题 2：空数据未降级到演示数据

**文件：** `mcp-server/src/tools/ui_knowledge_graph.py:162-168`

**问题：**
```python
# 只在异常时降级，空数据时不降级
try:
    graph_data = load_real_data()
    # ❌ 没有检查数据是否为空
except Exception as e:
    graph_data = _get_demo_graph_data()
```

**修复：**
```python
try:
    graph_data = load_real_data()
    
    # ✓ 空数据降级
    if len(graph_data['nodes']) == 0:
        logger.info("No data in knowledge graph, using demo data")
        graph_data = _get_demo_graph_data()
except Exception as e:
    graph_data = _get_demo_graph_data()
```

**Python 特色：数据降级策略**
- 异常处理：`try/except`
- 空数据检查：`if len(data) == 0`
- 演示数据作为后备（Graceful Degradation）

---

#### 2.3 发现问题 3：MCP Client 丢弃 `_meta` 字段

**文件：** `client/backend/mcp_client.py:102-112`

**问题：**
```python
response = json.loads(response_line)

if "error" in response:
    raise RuntimeError(f"MCP Error: {response['error']}")

return response.get("result", {})  # ❌ 丢弃 _meta
```

**修复：**
```python
response = json.loads(response_line)

if "error" in response:
    raise RuntimeError(f"MCP Error: {response['error']}")

# ✓ 保留 _meta
result = response.get("result", {})
if "_meta" in response:
    result["_meta"] = response["_meta"]

return result
```

**关键点：** 这是最严重的问题，导致前端永远收不到 UI Template！

---

### 3. 架构问题：stdio vs HTTP 通信

#### 3.1 发现问题 4：WebSocket Server 使用 stdio 导致死锁

**文件：** `client/backend/config.py:55-64`

**问题配置：**
```python
mcp_server=MCPServerConfig(
    name="learning-system",
    command="python",
    args=["server.py"],  # stdio 模式
    cwd=str(mcp_server_path),
)
```

**实际情况：**
- WebSocket Server 启动时通过 stdio 创建 MCP Server 子进程
- 但系统已经有独立的 HTTP 模式 MCP Server 在运行（端口 8080）
- stdio 子进程启动失败或通信死锁

**解决方案：** 创建 `mcp_http_client.py`，直接通过 HTTP 调用

```python
class MCPHTTPClient:
    """通过 HTTP 与 MCP Server 通信，避免 stdio 死锁问题"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.jsonrpc_url = f"{base_url}/jsonrpc"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None):
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
            "params": params or {}
        }
        
        response = await self.client.post(self.jsonrpc_url, json=request)
        data = response.json()
        
        # 返回完整响应结构
        return {
            "result": data.get("result", {}),
            "_meta": data.get("_meta")
        }
```

**架构优势：**
- ✅ 稳定：HTTP 协议成熟，无死锁风险
- ✅ 可调试：可用 curl 直接测试
- ✅ 解耦：MCP Server 可独立重启

---

#### 3.2 发现问题 5：HTTP Client 数据结构错误

**文件：** `client/backend/mcp_http_client.py:52-54`


**第一次修复（错误）：**
```python
# ❌ 将 result 内容和 _meta 放在同一层级
result = data.get("result", {})
if "_meta" in data:
    result["_meta"] = data["_meta"]
return result
```

这导致返回：
```python
{
    "nodes": [...],     # result 的内容
    "edges": [...],
    "_meta": {...}      # 混在一起
}
```

**正确修复：**
```python
# ✓ 保持 result 和 _meta 在顶层
return {
    "result": data.get("result", {}),
    "_meta": data.get("_meta")
}
```

返回正确结构：
```python
{
    "result": {
        "nodes": [...],
        "edges": [...]
    },
    "_meta": {...}
}
```

---

### 4. 前端问题：React 严格模式导致消息处理器丢失

#### 4.1 关键日志分析

```
websocket.ts:25 [WebSocket] Raw message received: {...}
websocket.ts:27 [WebSocket] Parsed message: {...}
websocket.ts:28 [WebSocket] Calling 0 handler(s)  ← 关键！
mcpClient.ts:73 [MCPClient] Request 1 timeout - no response received
```

**发现：** WebSocket 收到消息，但 `messageHandlers` 集合是空的（0 个处理器）！

#### 4.2 React 严格模式双重挂载问题

**React Strict Mode 行为：**
```
第一次挂载：
  ├─ 创建 mcpClient 实例
  ├─ 注册消息处理器 → wsService.onMessage()
  └─ 连接 WebSocket

立即卸载：
  └─ 断开 WebSocket

第二次挂载：
  ├─ 重新连接 WebSocket ✓
  └─ 但 mcpClient 是单例，未重新注册处理器 ✗
```

#### 4.3 修复：重新注册机制

**文件：** `client/frontend/src/services/mcpClient.ts`

**修复前：**
```typescript
export class MCPClient {
  constructor() {
    wsService.onMessage(this.handleMessage.bind(this));  // 只注册一次
  }
}
```

**修复后：**
```typescript
export class MCPClient {
  private cleanupHandler: (() => void) | null = null;

  constructor() {
    this.registerMessageHandler();
  }

  private registerMessageHandler() {
    // 清理旧处理器
    if (this.cleanupHandler) {
      this.cleanupHandler();
    }
    
    // 注册新处理器
    this.cleanupHandler = wsService.onMessage(this.handleMessage.bind(this));
    console.log('[MCPClient] Message handler registered');
  }

  // 公开方法供外部重新注册
  reregisterHandler() {
    this.registerMessageHandler();
  }
}
```

**文件：** `client/frontend/src/App.tsx`

```typescript
wsService
  .connect(WS_URL)
  .then(() => {
    console.log('[App] WebSocket connected');
    setConnected(true);
    // 连接成功后重新注册
    mcpClient.reregisterHandler();  ✓
  })
```

**前端特色：**
- React 严格模式在开发环境下强制双重挂载检测副作用
- 单例服务需要处理重新初始化逻辑
- 生命周期清理函数（cleanup handler）

---

## 📊 完整数据流（修复后）

```
┌─────────────────────────────────────────────────────────────────┐
│ 前端发送请求                                                      │
│ {jsonrpc: "2.0", id: 1, method: "tools/call", ...}              │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ WebSocket Server (websocket_server.py)                          │
│ - 接收 JSON-RPC 请求                                             │
│ - 转发到 MCP HTTP Client                                         │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCP HTTP Client (mcp_http_client.py)                            │
│ - HTTP POST → http://localhost:8080/jsonrpc                     │
│ - 保持 {result: {...}, _meta: {...}} 结构                        │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCP Server (server.py via http_server.py)                       │
│ ├─ 调用 ui_knowledge_graph 工具                                  │
│ ├─ 生成 UITemplateResult                                         │
│ ├─ 加载 HTML 模板内容 ✓                                          │
│ ├─ 检查空数据并降级 ✓                                            │
│ └─ 返回: {result: {...}, _meta: {uiTemplate: {...}}}            │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCP HTTP Client                                                  │
│ - 保留 _meta 字段 ✓                                              │
│ - 返回完整结构                                                   │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ WebSocket Server                                                 │
│ - 转发 _meta 字段 ✓                                              │
│ - 构建 JSON-RPC 响应                                             │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 前端收到完整响应                                                  │
│ {jsonrpc: "2.0", id: 1, result: {...}, _meta: {uiTemplate}}     │
│ ├─ WebSocket 消息处理器正常工作 ✓                                │
│ ├─ mcpClient.parseResponse() 提取 uiTemplate                     │
│ ├─ 传递 data 到 KnowledgeGraphView                               │
│ └─ D3.js 渲染知识图谱 ✓                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🐛 修复的所有问题总结

### Python 后端问题

| # | 文件 | 问题 | 根本原因 | 修复方式 |
|---|------|------|----------|----------|
| 1 | `server.py:510-531` | 属性名错误 `result.data` | 代码与类定义不一致 | 改为 `result.template_data` |
| 2 | `server.py:520` | `template` 是路径而非内容 | MCP 2026 协议理解错误 | 用 `Path.read_text()` 加载 HTML |
| 3 | `ui_knowledge_graph.py:162-168` | 空数据不降级 | 缺少边界检查 | 添加 `if len(nodes) == 0` |
| 4 | `mcp_client.py:102-112` | 丢弃 `_meta` 字段 | 只返回 `result` | 合并 `_meta` 到返回值 |
| 5 | `config.py:55-64` | stdio 通信死锁 | 架构设计问题 | 改用 HTTP 通信 |
| 6 | `mcp_http_client.py:52-54` | 数据结构扁平化 | 错误的字段合并逻辑 | 保持顶层结构 |

### 前端问题

| # | 文件 | 问题 | 根本原因 | 修复方式 |
|---|------|------|----------|----------|
| 7 | `mcpClient.ts:20-22` | 消息处理器丢失 | React 严格模式双重挂载 | 添加重新注册机制 |
| 8 | `App.tsx:13-28` | 未重新注册处理器 | 缺少连接后回调 | 调用 `reregisterHandler()` |
| 9 | `App.tsx:4` | 缺少 `mcpClient` 导入 | 遗漏导入语句 | 添加 `import` |

---


## 🎓 技术要点与最佳实践

### 1. MCP 2026 协议规范

**UI Template 规范：**
```typescript
{
  "_meta": {
    "io.modelcontextprotocol/uiTemplate": {
      "templateId": "唯一标识符",
      "template": "完整的 HTML 字符串（不是路径！）",
      "data": {
        // 结构化数据供模板渲染
      }
    }
  }
}
```

**协议扩展字段：**
- `io.modelcontextprotocol/uiTemplate` - UI 组件
- `io.modelcontextprotocol/inputRequired` - MRTR 用户确认
- `io.modelcontextprotocol.tasks/taskHandle` - 长任务句柄

### 2. Python 异常处理与降级策略

```python
# 三层降级策略
try:
    # 第一优先：真实数据
    data = load_from_database()
    
    # 第二检查：数据完整性
    if not data or len(data['nodes']) == 0:
        logger.info("No data, using demo")
        data = get_demo_data()
        
except DatabaseError as e:
    # 第三降级：异常兜底
    logger.error(f"Database failed: {e}")
    data = get_demo_data()
```

### 3. TypeScript 消息处理器生命周期

```typescript
class MessageClient {
  private cleanupHandler: (() => void) | null = null;

  register() {
    // 先清理旧的
    if (this.cleanupHandler) {
      this.cleanupHandler();
    }
    
    // 再注册新的
    this.cleanupHandler = service.onMessage(this.handler);
  }
}
```

### 4. stdio vs HTTP 通信选型

| 特性 | stdio | HTTP |
|------|-------|------|
| 稳定性 | 易死锁 | 高 |
| 调试性 | 困难 | 容易（curl） |
| 解耦性 | 紧耦合 | 松耦合 |
| 性能 | 略高 | 足够 |
| 适用场景 | 单进程工具 | 分布式服务 |

**建议：** 生产环境使用 HTTP，开发工具使用 stdio

---

## ✅ 验证方法

### 1. MCP Server 测试

```bash
curl -X POST http://localhost:8080/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ui_knowledge_graph","arguments":{}}}' \
  | python -c "import sys, json; data=json.load(sys.stdin); \
    print('_meta exists:', '_meta' in data); \
    print('Nodes:', len(data.get('_meta',{}).get('io.modelcontextprotocol/uiTemplate',{}).get('data',{}).get('nodes',[])))"
```

期望输出：
```
_meta exists: True
Nodes: 8
```

### 2. WebSocket 完整链路测试

```python
# test_websocket_flow.py
import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "ui_knowledge_graph", "arguments": {}}
        }))
        
        response = json.loads(await ws.recv())
        assert "_meta" in response
        assert "io.modelcontextprotocol/uiTemplate" in response["_meta"]
        print("✓ Test passed")

asyncio.run(test())
```

### 3. 前端浏览器测试

1. 打开 `http://localhost:3000`
2. 控制台应显示：
   ```
   [WebSocket] Connected
   [App] WebSocket connected
   [MCPClient] Message handler registered  ← 关键
   ```
3. 点击 "Knowledge Graph" 按钮
4. 应显示 D3.js 力导向图

---

## 🚀 服务启动命令

```bash
# Terminal 1 - MCP Server (HTTP 模式)
cd E:\Desktop\learning-system\mcp-server
python http_server.py

# Terminal 2 - WebSocket Server
cd E:\Desktop\learning-system\client\backend
python websocket_server.py

# Terminal 3 - Frontend
cd E:\Desktop\learning-system\client\frontend
npm run dev
```

**端口占用：**
- 8080：MCP Server HTTP 端口
- 8000：WebSocket Server 端口
- 3000：前端开发服务器端口

---

## 📚 相关文档

- [MCP 2026 协议规范](../mcp-features-mapping.md)
- [架构思路](../架构思路.md)
- [Phase 3 前端完成报告](./phase3-frontend-completion.md)
- [Phase 4 集成完成报告](./phase4-completion-report.md)

---

## 🎯 核心收获

### 技术层面

1. **协议理解的重要性：** MCP 2026 的 `_meta` 字段必须在整个链路中保持传递
2. **架构选型影响调试效率：** HTTP 比 stdio 更适合分布式架构
3. **前端框架特性：** React 严格模式会暴露副作用问题，必须正确处理
4. **数据降级策略：** 生产系统必须有多层后备方案

### 调试方法论

1. **分层验证：** 从最底层（MCP Server）往上逐层测试
2. **协议追踪：** 用 curl/浏览器开发者工具验证每一跳
3. **日志驱动：** 在关键节点添加详细日志
4. **结构化思维：** 画出完整数据流图，定位断点

### 项目特色

- **MCP 2026 协议实践：** UI Template、MRTR、Tasks 完整实现
- **多语言协作：** Python 后端 + TypeScript 前端
- **现代化架构：** FastAPI + React + D3.js + WebSocket
- **面试准备价值：** 真实的分布式系统调试案例

---

## 💡 面试要点提炼

### 1. 问题排查思路（STAR 法则）

**Situation（情境）：**
"在开发学习系统的知识图谱可视化功能时，前端无法显示图谱。这是一个涉及 Python 后端、WebSocket 中间层和 React 前端的分布式系统问题。"

**Task（任务）：**
"需要快速定位问题，确保 MCP 2026 协议的 UI Template 能正确传递到前端，并成功渲染 D3.js 图表。"

**Action（行动）：**
"我采用分层验证法：
1. 用 curl 直接测试 MCP Server HTTP 接口，确认 `_meta` 字段正确返回
2. 检查 WebSocket 中间层的数据转发逻辑
3. 在浏览器开发者工具中查看 WebSocket 消息
4. 添加详细日志追踪数据流
5. 发现了 9 个具体问题，涉及协议理解错误、架构设计缺陷和 React 生命周期问题"

**Result（结果）：**
"成功修复所有问题，知识图谱正常显示。这次排查让我深入理解了：
- MCP 2026 协议的 `_meta` 字段传递机制
- stdio vs HTTP 通信的权衡
- React 严格模式对单例服务的影响
- 完整的前后端调试方法论"

### 2. 技术亮点

**MCP 2026 协议实践：**
- "实现了 UI Template 功能，让 AI 能动态生成可交互的前端组件"
- "理解了 `_meta` 字段在协议扩展中的作用"

**架构演进：**
- "从 stdio 通信重构为 HTTP 通信，提升了系统的稳定性和可调试性"
- "创建了 `mcp_http_client.py` 解决进程间通信死锁问题"

**前端工程化：**
- "处理了 React 严格模式下的单例服务生命周期问题"
- "实现了消息处理器的动态重新注册机制"

### 3. 可讨论的深度话题

- **协议设计：** 为什么 MCP 选择 `_meta` 而不是直接在 `result` 中？
- **通信方式：** stdio、HTTP、WebSocket 的场景选择
- **错误处理：** 多层降级策略的设计原则
- **前端状态管理：** 单例服务在 React 中的最佳实践

---

## 📝 经验总结

### 做得好的地方

1. **系统化排查：** 从底层到上层，用测试验证每一层
2. **详细日志：** 在关键节点添加日志，快速定位问题
3. **协议理解：** 深入理解 MCP 2026 规范，而不是猜测
4. **文档记录：** 完整记录排查过程，便于回顾和面试准备

### 需要改进的地方

1. **提前测试：** 应该在开发阶段就用 curl 测试每个接口
2. **架构评审：** stdio vs HTTP 的选择应该在设计阶段就确定
3. **单元测试：** 缺少针对 `_meta` 字段传递的集成测试

### 后续优化方向

1. 添加端到端测试覆盖完整数据流
2. 实现 `_meta` 字段的自动验证
3. 优化 WebSocket 重连逻辑
4. 添加性能监控和错误上报

---

**文档版本：** v1.0  
**最后更新：** 2026-08-06  
**作者：** Claude (Opus 5)  
**会话成本：** $109.11（包含完整排查、修复与文档编写）

---

## 🔖 附录：关键代码片段索引

详细代码修复请参考以下文件：

- `mcp-server/server.py` - MCP Server UI Template 返回逻辑
- `mcp-server/src/tools/ui_knowledge_graph.py` - 数据降级策略
- `client/backend/mcp_http_client.py` - HTTP 客户端实现
- `client/backend/websocket_server.py` - WebSocket 消息转发
- `client/frontend/src/services/mcpClient.ts` - 消息处理器注册
- `client/frontend/src/App.tsx` - WebSocket 连接生命周期

所有修改已提交至 Git，可通过 `git log` 查看详细变更历史。

