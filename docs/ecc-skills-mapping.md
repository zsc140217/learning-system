# ECC Skills 集成方案

> ⚠️ **重要更新**: ECC Skills 不是 Python SDK！
>
> **正确理解**:
> - ECC Skills = Claude Code 的命令（用户手动触发）
> - 不能通过 `invoke_skill()` 在代码中调用
> - 我们的策略：分析 ECC 源码，提取算法，自己实现
>
> **参考文档**: `docs/ARCHITECTURE_CORRECTION.md`

**版本**: 2.0  
**日期**: 2026-08-01

---

## 1. 可用Skills总览

**ECC版本**: v2.1.0  
**Skills总数**: 281个  
**已验证可用**: 6个核心Skills

---

## 2. 4个Agent的Skills映射

### 2.1 Session Analyzer → SessionAnalyzerV2

| 参考来源 | 我们的实现 | 状态 |
|---------|----------|------|
| ECC `continuous-learning-v2` | `SessionAnalyzerV2` | 🚧 开发中 |

**开发策略**:
1. 分析 ECC `continuous-learning-v2` 源码
2. 提取核心算法（会话分段、模式识别、评分）
3. 用 Python 重新实现
4. 增加学习场景的优化（难度评估、复习计划）

**调用方式**:
```python
# ❌ 错误方式（ECC Skills 不能这样调用）
# from ecc import invoke_skill
# result = await invoke_skill("continuous-learning-v2", ...)

# ✅ 正确方式：自己实现
from src.agents.session_analyzer import SessionAnalyzer

analyzer = SessionAnalyzer("analyzer_001", bus)
await analyzer.start()

# 发布事件触发分析
await bus.publish({
    "type": "session.completed",
    "session_id": "sess_001",
    "transcript": [...]
})

# 说明：
# SessionAnalyzer 基于对 ECC continuous-learning-v2 的分析
# 提取了核心算法，用 Python 重新实现
# 详见：docs/ecc-analysis/continuous-learning-v2.md
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

### 2.3 Project Tracker → ProjectTrackerV2

| 参考来源 | 我们的实现 | 状态 |
|---------|----------|------|
| ECC `codebase-onboarding` | `ProjectTrackerV2` | ⏳ 待开发 |
| ECC `agent-architecture-audit` | 辅助分析 | ⏳ 待开发 |

**开发策略**:
1. 分析 ECC `codebase-onboarding` 源码
2. 提取代码库分析算法
3. 增加面试亮点提取功能

**调用方式**:
```python
# ✅ 正确方式：自己实现
from src.agents.project_tracker import ProjectTracker

tracker = ProjectTracker("tracker_001", bus)
result = await tracker.analyze_project("/path/to/project")
```

---

### 2.4 Tech Explorer → TechExplorerV2

| 参考来源 | 用途 | 优先级 |
|---------|------|-------|
| Exa `web_search_exa` | Web搜索 | P0 |
| ECC `deep-research` | 深度调研参考 | P1 |

**调用方式**:
```python
# 使用Exa插件（这个可以直接调用）
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
    "reference_skills": ["continuous-learning-v2"],
    "implementation": "SessionAnalyzer",
    "status": "active"
  },
  "memory_manager": {
    "primary_tools": ["memory-mcp"],
    "implementation": "MemoryManager",
    "status": "active"
  },
  "project_tracker": {
    "reference_skills": ["codebase-onboarding"],
    "implementation": "ProjectTrackerV2",
    "status": "planned"
  },
  "tech_explorer": {
    "primary_tools": ["web_search_exa"],
    "reference_skills": ["deep-research"],
    "implementation": "TechExplorerV2",
    "status": "planned"
  }
}
```

---

## 4. 依赖检查

### 必需
- ✅ ECC v2.1.0 已安装（用于参考分析）
- ✅ Memory MCP v0.8.0 已安装
- ✅ Exa插件 已安装

### 可选
- ⏳ GitHub MCP (代码分析)
- ⏳ Context7 MCP (文档查询)

---

## 5. 测试验证

```bash
# 验证ECC Skills可用性（手动测试）
/continuous-learning-v2
/instinct-status

# 验证Memory MCP
python -c "import hot_memory_mcp; print(hot_memory_mcp.__version__)"

# 测试我们的实现
python -m pytest tests/test_session_analyzer.py -v
python -m pytest tests/test_memory_manager.py -v
```

---

## 6. 核心理念

**从 ECC 学习，而非依赖 ECC**

- 📖 分析 ECC Skills 源码，理解算法逻辑
- 🔨 用 Python 重新实现，适配我们的场景
- ✨ 针对学习和面试场景优化
- 🎯 展示算法分析和创新能力

---

**维护说明**: 随着ECC更新，定期检查新Skills并更新分析
