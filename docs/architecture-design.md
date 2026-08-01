# Learning System 架构设计

**版本**: 2.0  
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
Layer 4: 资源层 (Memory MCP + 文件系统)
```

### 2.2 四个Agent（自研算法，参考ECC）

1. **SessionAnalyzerV2**
   - 参考: ECC `continuous-learning-v2`
   - 功能: 会话分析、知识提取、难度评估
   - 创新: 增加复习计划生成、记忆曲线计算

2. **MemoryManager**
   - 基于: Memory MCP Python SDK
   - 功能: 知识图谱管理、语义搜索、关联推荐
   - 创新: 自动去重、智能分类、热度追踪

3. **ProjectTrackerV2**
   - 参考: ECC `codebase-onboarding`
   - 功能: 代码库分析、技术栈识别、架构理解
   - 创新: 面试亮点提取、问题生成、贡献度统计

4. **TechExplorerV2**
   - 参考: ECC `deep-research` + Exa插件
   - 功能: 技术调研、资源推荐、学习路径规划
   - 创新: 质量评分、知识图谱扩展、实战建议

---

## 3. 数据流

```
会话结束 → SessionAnalyzerV2
    ↓ (提取知识)
MemoryManager (保存到Memory MCP)
    ↓ (事件通知)
ProjectTrackerV2 / TechExplorerV2
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
| 后端 | Python 3.12 + FastMCP |
| 存储 | Memory MCP + SQLite |
| LLM | Claude API (Opus/Sonnet) |
| 参考 | ECC Skills (分析算法) |

---

## 6. 与 ECC Skills 的关系

### 6.1 ECC Skills 的作用

**ECC Skills ≠ Python SDK**

ECC Skills 是 Claude Code 的命令，用户手动触发：
- `/continuous-learning-v2` - 分析会话提取模式
- `/codebase-onboarding` - 分析代码库结构
- `/deep-research` - 深度技术调研

**不能在 Python 代码中直接调用！**

---

### 6.2 我们的策略：提取与改进

```
步骤1: 分析 ECC Skills 源码
    ↓
步骤2: 提取核心算法
    ↓
步骤3: 用 Python 重新实现
    ↓
步骤4: 针对学习场景优化
    ↓
步骤5: 集成到我们的 MCP Server
```

**价值**:
- ✅ 学习业界最佳实践
- ✅ 展示算法分析能力
- ✅ 展示改进创新能力
- ✅ 提升项目独立性

---

### 6.3 算法对比

| 维度 | ECC Skills | 我们的实现 |
|-----|-----------|----------|
| **调用方式** | 用户手动命令 | MCP 自动化 |
| **语言** | TypeScript | Python |
| **场景** | 通用开发 | 学习+面试准备 |
| **知识存储** | ECC 内部 | Memory MCP |
| **创新点** | - | 难度评估、复习计划、面试题生成 |

---

### 6.4 两种使用方式

#### 方式1: ECC Skills（手动辅助）
```
用户结束学习会话
    ↓
手动运行: /continuous-learning-v2
    ↓
ECC 分析并展示结果
    ↓
用户决定是否手动保存
```

#### 方式2: Learning System（自动化）
```
用户结束学习会话
    ↓
调用 MCP 工具: analyze_session()
    ↓
SessionAnalyzerV2 自动分析（使用提取的算法）
    ↓
自动保存到 Memory MCP
    ↓
生成复习计划和面试题
    ↓
推送通知给用户
```

**两种方式互补！**

---

## 7. MCP协议应用

| 特性 | 应用场景 |
|-----|---------|
| 无状态 | ID显式传递 |
| MRTR | 删除确认 |
| Tasks | 长时任务(项目分析) |
| Apps | 可视化(知识图谱) |

---

**详细设计见**: `docs/ARCHITECTURE_CORRECTION.md`
