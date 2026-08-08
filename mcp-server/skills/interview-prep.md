---
name: interview-prep
description: 为技术面试准备项目介绍、技术亮点和 STAR 话术
trigger: 用户需要准备面试、生成项目介绍
tools: project/detect_framework, project/scan_structure, project/analyze_dependencies, project/extract_patterns, knowledge/search
output: 面试准备材料包（项目介绍、技术亮点、面试问题、STAR话术）
---

# Interview Prep Skill

基于项目分析结果，生成完整的面试准备材料。

**参考来源**: 基于 codebase-onboarding + 面试准备最佳实践  
**适用场景**: 准备技术面试、项目答辩

---

## 工作流程

### Phase 1: 项目全面分析

复用 codebase-onboarding 的工具调用，获取技术栈和架构信息。

### Phase 2: 生成项目介绍

**30秒版模板**:
```
"我实现了一个<项目类型>，核心是<核心技术点>。
<技术栈>。解决了<核心问题>。"
```

**2分钟版包含**: 项目背景 → 技术选型 → 核心实现 → 技术亮点 → 成果数据

### Phase 3: 提取技术亮点

按类别分组:
- 架构设计
- 协议实现
- 技术深度
- 工程质量
- 创新点

### Phase 4: 生成常见面试问题

4个维度:
- 技术选型类
- 实现细节类
- 挑战与解决类
- 优化与改进类

### Phase 5: 生成 STAR 话术

STAR 模板:
- Situation: 项目背景和问题
- Task: 你的职责和目标
- Action: 具体做了什么
- Result: 量化的成果

---

## 输出格式

```json
{
  "project_introduction": {
    "short": "30秒版",
    "detailed": "2分钟版"
  },
  "technical_highlights": [],
  "interview_questions": [],
  "star_stories": []
}
```
