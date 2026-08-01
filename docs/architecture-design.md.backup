# Learning System 架构设计

**版本**: 1.0  
**日期**: 2026-08-01

---

## 1. 系统概述

Learning System是一个**AI驱动的学习成长系统**，基于MCP 2026-07-28协议，通过4个专业Agent实现：
- 📝 自动总结会话知识
- 🗂️ 管理知识图谱
- 📊 追踪项目经验
- 🔍 探索前沿技术

---

## 2. 核心架构

### 2.1 分层设计

```
Layer 1: 用户界面层 (Claude Code + MCP Apps)
    ↓ MCP 2026-07-28
Layer 2: 编排层 (MCP Server + Agent Bus)
    ↓
Layer 3: Agent层 (4个专业Agent)
    ↓
Layer 4: 资源层 (Memory MCP + ECC Skills + 文件系统)
```

### 2.2 四个Agent

1. **Session Analyzer** - 分析会话，提取知识点
2. **Memory Manager** - 管理知识图谱，生成复习计划
3. **Project Tracker** - 追踪项目，提取面试亮点
4. **Tech Explorer** - 探索技术，生成学习路径

---

## 3. 数据流

```
会话结束 → Session Analyzer
    ↓ (提取知识)
Memory Manager (保存到Memory MCP)
    ↓ (事件通知)
Project Tracker / Tech Explorer
    ↓
返回用户 (MCP App可视化)
```

---

## 4. 存储架构

### 三层存储

1. **Memory MCP** (主存储)
   - 热缓存：0ms自动注入
   - 冷存储：~50ms语义搜索

2. **文件系统** (补充)
   - `data/sessions/` - 会话历史(Markdown)
   - `data/projects/` - 项目分析(JSON)
   - `data/knowledge/` - 知识快照(JSON)

3. **SQLite** (元数据)
   - sessions、projects、reviews、analytics

---

## 5. 技术栈

| 组件 | 技术 |
|-----|------|
| 协议 | MCP 2026-07-28 |
| 后端 | Python 3.12 + FastAPI |
| 存储 | Memory MCP + SQLite |
| LLM | Claude API (Opus/Sonnet) |
| Skills | ECC (281个) |

---

## 6. MCP协议应用

| 特性 | 应用场景 |
|-----|---------|
| 无状态 | ID显式传递 |
| MRTR | 删除确认 |
| Tasks | 长时任务(项目分析) |
| Apps | 可视化(知识图谱) |

---

**详细设计见完整文档**
