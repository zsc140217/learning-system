# Learning System - 完整使用指南

**更新时间**: 2026-08-04  
**状态**: 生产就绪

---

## 📋 快速开始（3 步配置）

### 步骤 1：生成 JWT 密钥

```bash
cd E:\Desktop\learning-system
python -c "import secrets; print(secrets.token_hex(32))"
```

**复制输出的密钥**，例如：`a7b3c9d2e4f5g6h7i8j9k0l1m2n3o4p5q6r7s8t9u0v1w2x3y4z5a6b7c8d9e0f1`

---

### 步骤 2：配置 Claude Desktop

**Windows 配置文件位置**：
```
%APPDATA%\Claude\claude_desktop_config.json
```

**配置内容**（复制整段）：
```json
{
  "mcpServers": {
    "learning-system": {
      "command": "python",
      "args": [
        "E:\\Desktop\\learning-system\\mcp-server\\server.py"
      ],
      "env": {
        "JWT_SECRET": "粘贴步骤1生成的密钥",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**注意**：
1. 替换 `JWT_SECRET` 为步骤 1 生成的密钥
2. 路径使用双反斜杠 `\\` 或正斜杠 `/`

---

### 步骤 3：重启 Claude Desktop

1. 完全关闭 Claude Desktop
2. 重新打开
3. 查看底部状态栏，应该显示 "learning-system" 连接成功

---

## 🤖 AI 如何知道工具用法？

### 答案：MCP 协议自动发现（不需要 Skill）

**工作流程**：
```
1. Claude Desktop 连接 MCP Server
         ↓
2. 发送 tools/list 请求
         ↓
3. MCP Server 返回所有工具的元数据
   - 工具名称
   - 参数定义（从函数签名提取）
   - 说明文档（从 docstring 提取）
         ↓
4. Claude 自动理解工具用途
         ↓
5. 用户对话时，Claude 自动选择合适的工具调用
```

### 示例：analyze_session 工具

```python
@server.tool("analyze_session")
async def analyze_session(
    session_data: str,      # ← AI 知道这是字符串参数
    session_id: str = None  # ← AI 知道这是可选参数
) -> MCPResult:
    """
    分析会话内容，提取知识点  # ← AI 读这个说明
    
    Args:
        session_data: 会话内容 (Markdown格式)  # ← AI 知道参数含义
        session_id: 可选的会话ID
    """
    ...
```

**AI 自动学到**：
- 工具名：`analyze_session`
- 用途：分析会话内容，提取知识点
- 参数说明：从 docstring 提取

**不需要 Skill！** MCP 协议自动完成工具发现。

---

## 🎨 MCP Apps 如何呈现？

### 答案：Claude Desktop 自动渲染 UI

**工作流程**：
```
1. MCP Server 返回带 uiTemplate 的响应
         ↓
2. Claude Desktop 接收到 _meta 字段
         ↓
3. 检测到 "io.modelcontextprotocol/uiTemplate"
         ↓
4. Claude Desktop 渲染成可视化界面
   - 卡片、图表、按钮、表单
         ↓
5. 用户在 Claude 对话窗口中看到 UI
```

**UI 在哪里显示？** 
- ✅ 在 Claude Desktop 对话窗口中
- ❌ 不是独立网页
- ❌ 不需要浏览器

---

## 🔧 如何升级 MCP 项目？

### 1. 添加新工具

**在 `server.py` 中添加**：
```python
@server.tool("new_tool_name")
async def new_tool(param1: str) -> MCPResult:
    """工具说明（AI 会读这个）"""
    result = await do_something(param1)
    return MCPResult(data={"result": result})
```

**重启 Claude Desktop** - 新工具自动生效！

### 2. 添加 MCP App UI

```python
@server.tool("show_dashboard")
async def show_dashboard() -> MCPResult:
    return MCPResult(
        data={"stats": {...}},
        meta={
            "io.modelcontextprotocol/uiTemplate": {
                "templateId": "dashboard",
                "data": {...}
            }
        }
    )
```

### 3. 添加 MRTR 二次确认

```python
@server.tool("dangerous_operation")
async def dangerous_operation(
    data: str,
    request_state: str = None
) -> MCPResult:
    if not request_state:
        # 第 1 轮：返回确认请求
        token = jwt_handler.generate_request_state(...)
        return MCPResult(data={...}, meta={...})
    # 第 2 轮：验证并执行
    ...
```

---

## 📚 可用工具列表（17 个）

### 核心工具
1. `analyze_session` - 分析会话内容
2. `save_knowledge` - 保存知识点
3. `track_project` - 追踪项目
4. `explore_technology` - 探索技术

### MRTR 工具（需确认）
5. `delete_knowledge` - 删除知识
6. `delete_project` - 删除项目
7. `rebuild_index` - 重建索引

### Tasks 工具（长任务）
8. `analyze_project_deep` - 深度项目分析
9. `vectorize_knowledge_graph` - 图谱向量化
10. `research_technology_deep` - 深度技术调研

### 查询工具
11. `tasks/get` - 查询任务状态
12. `tasks/list` - 列出任务
13. `tasks/cancel` - 取消任务

### 知识工具
14. `search_knowledge` - 搜索知识图谱
15. `get_knowledge_graph` - 获取知识图谱

### 缓存工具
16. `invalidate_cache` - 失效缓存
17. `cache_stats` - 缓存统计

---

## 🎯 使用示例

### 示例 1：分析会话

```
你：帮我分析这段学习记录：
User: 什么是 FastAPI 依赖注入？
Assistant: FastAPI 使用 Depends() 实现依赖注入...

Claude：[自动调用 analyze_session 工具]
Claude：已提取到 1 个知识点：FastAPI 依赖注入（掌握度 70%）
```

### 示例 2：搜索知识

```
你：搜索我之前学过的关于路由的知识

Claude：[调用 search_knowledge 工具]
Claude：找到 3 个相关知识点...
```

### 示例 3：深度项目分析

```
你：分析我的项目 E:\Desktop\travel-system

Claude：[调用 analyze_project_deep 工具]
Claude：已启动深度分析任务，预计 10 分钟完成
```

---

## 🔍 故障排查

### 问题 1：Claude Desktop 看不到工具

**检查配置文件**：
```bash
# 查看配置文件位置
echo %APPDATA%\Claude\claude_desktop_config.json

# 测试 server.py 能否运行
cd E:\Desktop\learning-system
python mcp-server\server.py
```

### 问题 2：工具调用失败

**查看日志**：
- Claude Desktop 日志：`%APPDATA%\Claude\logs\`
- MCP Server 日志：命令行窗口

---

## 📝 总结

### 核心要点

1. **不需要 Skill** - MCP 协议自动发现工具
2. **UI 在 Claude 中** - MCP Apps 在对话窗口渲染
3. **升级很简单** - 添加工具 → 重启 Claude Desktop

### 工作原理

```
Claude Desktop (Client)
         ↕️ JSON-RPC 2.0
Learning System (Server)
         ↓
    17 个 MCP 工具
```

**现在就可以使用了！** 🎉
