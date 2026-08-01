# ECC Skills 集成方案

**版本**: 1.0  
**日期**: 2026-08-01

---

## 1. 可用Skills总览

**ECC版本**: v2.1.0  
**Skills总数**: 281个  
**已验证可用**: 6个核心Skills

---

## 2. 4个Agent的Skills映射

### 2.1 Session Analyzer

| Skill | 用途 | 优先级 |
|-------|------|-------|
| `continuous-learning-v2` | 提取会话中的instinct模式 | P0 |

**调用方式**:
```python
from ecc import invoke_skill

result = await invoke_skill(
    "continuous-learning-v2",
    session_data=session_transcript
)
```

---

### 2.2 Memory Manager

| 工具 | 用途 | 优先级 |
|-----|------|-------|
| Memory MCP `remember()` | 保存知识 | P0 |
| Memory MCP `recall()` | 语义搜索 | P0 |
| Memory MCP `link_memories()` | 建立关系 | P0 |
| Memory MCP `promote()` | 推广到热缓存 | P1 |
| Memory MCP `memory_stats()` | 统计信息 | P2 |

**调用方式**:
```python
from hot_memory_mcp import MemoryMCP

mcp = MemoryMCP()
await mcp.remember(
    content="LangChain是一个LLM应用开发框架",
    metadata={"type": "technology", "tags": ["AI", "Python"]}
)
```

---

### 2.3 Project Tracker

| Skill | 用途 | 优先级 |
|-------|------|-------|
| `codebase-onboarding` | 深度分析代码库 | P0 |
| `agent-architecture-audit` | 审计Agent架构 | P1 |
| `agent-harness-construction` | 分析Agent设计 | P2 |

**调用方式**:
```python
result = await invoke_skill(
    "codebase-onboarding",
    project_path="/path/to/project"
)
```

---

### 2.4 Tech Explorer

| 工具/Skill | 用途 | 优先级 |
|-----------|------|-------|
| Exa `web_search_exa` | Web搜索 | P0 |
| `deep-research` | 深度调研 | P1 (需安装firecrawl) |

**调用方式**:
```python
# 使用Exa插件
from mcp.plugins.exa import web_search_exa

results = await web_search_exa(
    query="vLLM技术原理",
    numResults=10
)
```

---

## 3. Skills配置文件

**位置**: `mcp-server/config/ecc_skills.json`

```json
{
  "session_analyzer": {
    "primary_skills": ["continuous-learning-v2"],
    "enabled": true
  },
  "memory_manager": {
    "primary_tools": ["memory-mcp"],
    "enabled": true
  },
  "project_tracker": {
    "primary_skills": ["codebase-onboarding"],
    "optional_skills": ["agent-architecture-audit"],
    "enabled": true
  },
  "tech_explorer": {
    "primary_tools": ["web_search_exa"],
    "optional_skills": ["deep-research"],
    "enabled": true
  }
}
```

---

## 4. 依赖检查

### 必需
- ✅ ECC v2.1.0 已安装
- ✅ Memory MCP v0.8.0 已安装
- ✅ Exa插件 已安装

### 可选
- ⏳ GitHub MCP (代码分析)
- ⏳ Context7 MCP (文档查询)
- ⏳ Firecrawl MCP (deep-research依赖)

---

## 5. 测试验证

```bash
# 验证ECC Skills
claude plugins list | grep ecc

# 验证Memory MCP
python -c "import hot_memory_mcp; print(hot_memory_mcp.__version__)"

# 测试continuous-learning-v2
/instinct-status
```

---

**维护说明**: 随着ECC更新，定期检查新Skills并更新映射
