# ECC 复用映射表

**日期**: 2026-08-02  
**目的**: 对比我们已实现的功能与 ECC 现有组件，制定精确的复用策略  
**原则**: 复用别人的，构筑自己的

---

## 一、核心发现总结

### 1.1 ECC 组件深度分析完成

| 组件 | 状态 | 核心发现 |
|------|------|---------|
| **learn.md** | 已分析 | 简单的模式提取命令，侧重单次会话 |
| **learn-eval.md** | 已分析 | 带质量门槛的学习命令，包含去重检查 |
| **continuous-learning-v2** | 已分析 | 完整的 Instinct 系统（2073 行 Python） |
| **knowledge-ops** | 已分析 | 多层知识管理架构 |
| **ecc-memory-vault MCP** | 已分析 | 跨客户端共享记忆服务器 |

### 1.2 关键架构洞察

#### continuous-learning-v2 核心机制
```
Hook 观察 (100% 可靠)
    ↓
observations.jsonl (记录工具调用)
    ↓
Background Observer Agent (Haiku)
    ↓
Instinct 提取 (原子化模式)
    ↓
Confidence 评分 (0.3-0.9)
    ↓
Project/Global 作用域隔离
    ↓
Evolve -> Skills/Commands/Agents
```

**v2.1 新特性**:
- **项目作用域**: 每个 Git 仓库独立的 instinct 存储
- **自动提升**: 在 2+ 项目中出现则自动提升为全局
- **去中心化存储**: `~/.local/share/ecc-homunculus/` (避免敏感路径)

#### knowledge-ops 六层架构
```
Layer 1: GitHub/Linear (执行真相)
Layer 2: Claude Memory (~/.claude/projects/*/memory/)
Layer 3: MCP Memory (知识图谱)
Layer 4: Knowledge Base Repo (持久文档)
Layer 5: External DB (Supabase/PostgreSQL)
Layer 6: Local Archive (临时笔记)
```

---

## 二、功能对比：我们 vs ECC

### 2.1 会话分析

| 功能维度 | 我们的实现 | ECC 对应组件 | 复用决策 |
|---------|-----------|-------------|---------|
| **会话内容解析** | `SessionReviewer.parse_session()` | `continuous-learning-v2/hooks/observe.sh` | 删除我们的，用 ECC |
| **知识点提取** | `SessionReviewer.extract_knowledge()` | Observer Agent (Haiku) 自动提取 | 删除我们的，用 ECC |
| **掌握度评估** | `SessionReviewer.analyze_mastery()` | ECC 没有 | 保留，这是我们的创新 |
| **观察触发** | 手动调用 | Hook (100% 可靠) | 使用 ECC Hook |

**结论**: 删除 `SessionReviewer` 的前两个方法，保留 `analyze_mastery()`

---

### 2.2 知识存储

| 功能维度 | 我们的实现 | ECC 对应组件 | 复用决策 |
|---------|-----------|-------------|---------|
| **本地文件存储** | 未实现 | `~/.local/share/ecc-homunculus/` | 直接使用 ECC 路径 |
| **MCP 集成** | 未实现 | `ecc-memory-vault` MCP Server | 直接使用 ECC MCP |
| **知识图谱** | 未实现 | MCP Memory Server (`create_entities`) | 使用标准 MCP Memory |
| **作用域隔离** | 未实现 | Project/Global 自动检测 | 使用 ECC 机制 |

**结论**: 完全复用 ECC 存储架构，无需自己实现

---

### 2.3 知识提取

| 功能维度 | 我们的实现 | ECC 对应组件 | 复用决策 |
|---------|-----------|-------------|---------|
| **从代码提取** | `KnowledgeExtractor.extract_from_code()` | ECC 没有特定工具 | 保留，补充功能 |
| **知识图谱节点** | `KnowledgeExtractor.create_node()` | MCP Memory `create_entities()` | 用 MCP，删我们的 |
| **去重检查** | 未实现 | `learn-eval.md` 的 Checklist | 借鉴 ECC 逻辑 |

**结论**: 保留代码提取功能，但改用 MCP Memory 存储

---

### 2.4 难度评估

| 功能维度 | 我们的实现 | ECC 对应组件 | 复用决策 |
|---------|-----------|-------------|---------|
| **5 维度评估** | `DifficultyEstimator` 全部 | ECC 完全没有 | 保留，核心创新 |
| **算法分析** | `_analyze_algorithm_complexity()` | 无 | 保留 |
| **前置知识** | `_detect_prerequisites()` | 无 | 保留 |
| **实战难度** | `_estimate_practice_difficulty()` | 无 | 保留 |

**结论**: 完全保留，这是面向学习场景的独特功能

---

### 2.5 复习调度

| 功能维度 | 我们的实现 | ECC 对应组件 | 复用决策 |
|---------|-----------|-------------|---------|
| **艾宾浩斯曲线** | `ReviewScheduler.calculate_next_review()` | ECC 完全没有 | 保留，核心创新 |
| **复习计划生成** | `ReviewScheduler.generate_schedule()` | 无 | 保留 |
| **学习效果追踪** | `ReviewScheduler.update_performance()` | Confidence 评分机制 | 融合两者 |

**结论**: 保留我们的复习系统，考虑与 Confidence 评分融合

---

### 2.6 CLI 工具

| 功能维度 | 我们的实现 | ECC 对应组件 | 复用决策 |
|---------|-----------|-------------|---------|
| **CLI 接口** | 未实现 | `instinct-cli.py` (2073 行) | 参考 ECC 实现 |
| **项目检测** | 无 | `detect-project.sh` | 直接复用函数 |
| **哈希生成** | 无 | `_project_hash()` | 直接复用 |
| **文件锁机制** | 无 | `instinct-cli.py` 内置 | 参考实现 |

**结论**: 实现 CLI 工具，大量复用 ECC 的工具函数

---

## 三、最终架构设计

### 3.1 三层复用策略

```
learning-system/
├── vendor/ecc/              # Vendor 层：直接复制 ECC 代码
│   ├── instinct_cli.py      # 复制 2073 行，标注来源
│   ├── detect_project.sh    # 项目检测脚本
│   └── observe.sh           # Hook 脚本
│
├── adapters/                # Adapter 层：适配接口
│   ├── ecc_instinct_adapter.py    # 包装 ECC Instinct API
│   ├── ecc_memory_adapter.py      # 包装 MCP Memory API
│   └── storage_adapter.py         # 统一存储接口
│
├── core/                    # Extension 层：我们的创新
│   ├── difficulty_estimator.py    # 5 维度难度评估
│   ├── review_scheduler.py        # 艾宾浩斯复习计划
│   ├── mastery_analyzer.py        # 掌握度分析
│   └── code_extractor.py          # 代码知识提取
│
├── cli/                     # CLI 工具
│   ├── learn_cli.py         # 主 CLI（参考 instinct-cli.py）
│   ├── review_cli.py        # 复习命令
│   └── quiz_cli.py          # 测验命令
│
├── mcp-server/              # MCP Server（直接用 ECC）
│   └── config.json          # 配置指向 ecc-memory-vault
│
└── hooks/                   # Hooks（直接用 ECC）
    └── observe.sh           # 符号链接到 vendor
```

### 3.2 保留 vs 删除 vs 重构

| 文件 | 决策 | 理由 |
|-----|------|------|
| `session_reviewer.py` | 重构 | 删除解析/提取，保留掌握度分析 |
| `knowledge_extractor.py` | 重构 | 保留代码提取，改用 MCP 存储 |
| `difficulty_estimator.py` | 完全保留 | ECC 没有，核心创新 |
| `review_scheduler.py` | 完全保留 | ECC 没有，核心创新 |
| `ecc_adapter.py` | 删除 | 无用的空壳，直接调用 vendor |

---

## 四、复用清单

### 4.1 直接复用（Vendor）

**从 ECC 复制的文件**:
```bash
# 复制核心脚本
cp ~/.claude/ecc/skills/continuous-learning-v2/scripts/instinct-cli.py \
   vendor/ecc/instinct_cli.py

cp ~/.claude/ecc/skills/continuous-learning-v2/scripts/detect-project.sh \
   vendor/ecc/detect_project.sh

cp ~/.claude/ecc/skills/continuous-learning-v2/hooks/observe.sh \
   vendor/ecc/observe.sh
```

**标注来源**:
```python
"""
Vendored from ECC continuous-learning-v2
Source: ~/.claude/ecc/skills/continuous-learning-v2/scripts/instinct-cli.py
Version: 2.1.0
License: MIT (假设)
Modifications: None (保持原样)
"""
```

### 4.2 适配层（Adapter）

**创建的适配器**:
- `ecc_instinct_adapter.py` - 包装 `instinct_cli.py` 的 Python API
- `ecc_memory_adapter.py` - 包装 MCP Memory 工具
- `storage_adapter.py` - 统一的存储接口

### 4.3 扩展层（Extension）

**我们的创新功能**:
- `difficulty_estimator.py` - 5 维度难度评估
- `review_scheduler.py` - 艾宾浩斯复习计划
- `mastery_analyzer.py` - 掌握度分析（从 SessionReviewer 提取）
- `code_extractor.py` - 代码知识提取（从 KnowledgeExtractor 提取）

---

## 五、实施计划

### Phase 1: Vendor 层构建（30 分钟）
1. 创建 `vendor/ecc/` 目录
2. 复制 3 个核心文件
3. 添加来源标注和许可证
4. 验证文件可执行

### Phase 2: Adapter 层实现（1 小时）
1. 实现 `ecc_instinct_adapter.py`
   - 包装 `instinct_cli.py` 的关键函数
   - 提供 Python 友好的 API
2. 实现 `ecc_memory_adapter.py`
   - 包装 MCP Memory 工具
   - 处理知识图谱操作
3. 实现 `storage_adapter.py`
   - 统一存储接口
   - 处理路径和作用域

### Phase 3: Core 层重构（1.5 小时）
1. 重构 `session_reviewer.py` -> `mastery_analyzer.py`
   - 删除 `parse_session()` 和 `extract_knowledge()`
   - 保留 `analyze_mastery()`
2. 重构 `knowledge_extractor.py` -> `code_extractor.py`
   - 保留代码提取逻辑
   - 改用 `ecc_memory_adapter` 存储
3. 保留 `difficulty_estimator.py` (不变)
4. 保留 `review_scheduler.py` (不变)

### Phase 4: CLI 工具实现（2 小时）
1. 实现 `cli/learn_cli.py`
   - 参考 `instinct_cli.py` 的命令结构
   - 集成我们的创新功能
2. 实现 `cli/review_cli.py`
   - 复习计划查看
   - 开始复习会话
3. 实现 `cli/quiz_cli.py`
   - 测验生成
   - 答案验证

### Phase 5: 集成测试（1 小时）
1. 端到端测试
2. Hook 集成验证
3. MCP 连接测试

**总计**: 约 6 小时

---

## 六、面试亮点更新

### 可以说的技术深度

**面试官**: 介绍一下你的 Learning System 项目。

**你**: 这是一个基于 MCP 的面试复习系统，核心设计理念是"复用别人的，构筑自己的"：

1. **深度调研**:
   - 分析了 ECC 的 continuous-learning-v2 (2073 行 Python)
   - 研究了 Instinct 架构：Hook -> Observer -> Confidence -> Evolve
   - 识别了 6 层知识管理架构

2. **三层复用**:
   - **Vendor 层**: 直接复制 ECC 的项目检测、哈希生成、Hook 系统
   - **Adapter 层**: 包装 ECC API 和 MCP Memory，提供统一接口
   - **Extension 层**: 实现 ECC 没有的功能（难度评估、复习调度）

3. **创新点**:
   - **5 维度难度评估**: 算法复杂度、前置知识、抽象层次、实战难度、时间投入
   - **艾宾浩斯复习系统**: 自适应复习间隔，学习效果追踪
   - **掌握度分析**: 基于会话内容评估知识掌握程度

4. **工程实践**:
   - 代码溯源标注（Vendor 文件标注来源和版本）
   - 接口隔离（Adapter 层解耦）
   - 测试驱动开发

---

## 七、下次会话启动命令

```bash
继续 Learning System 项目。

任务: 实施 Phase 1（Vendor 层构建）

参考文档: docs/ecc-reuse-mapping.md

重点工作:
1. 创建 vendor/ecc/ 并复制文件
2. 添加来源标注

项目路径: E:\Desktop\learning-system
当前分支: master
```

---

**状态**: 复用策略已制定，准备实施
