---
name: tech-deep-dive
description: 深度调研技术主题，生成学习路径和实战项目建议
trigger: 用户想深入学习某个技术
tools: resource/web_search, resource/query_docs, knowledge/search, knowledge/save
output: 技术调研报告（概念、学习路径、实战项目、资源推荐）
---

# Tech Deep Dive Skill

深度调研一个技术主题，整合多源信息，生成结构化的学习材料。

**参考来源**: ECC deep-research skill  
**适用场景**: 学习新技术、技术选型、面试准备

---

## 工作流程

### Phase 1: 多源搜索（并行）

1. **Web 搜索**: resource/web_search
2. **文档查询**: resource/query_docs  
3. **知识库搜索**: knowledge/search

### Phase 2: 内容质量评估

评分维度:
- 权威性（官方文档 > 个人博客）
- 时效性（最近 6 个月优先）
- 完整性（有代码示例 > 纯文字）
- 深度（原理解释 > 使用教程）

### Phase 3: 知识提取

提取内容:
- 核心概念定义
- 使用场景
- 代码示例
- 最佳实践
- 常见陷阱

### Phase 4: 生成学习路径

分层设计:
- 基础层: 基本概念、快速上手
- 核心层: 深入原理、常用场景
- 进阶层: 性能优化、架构设计

### Phase 5: 推荐实战项目

项目类型:
- 入门级: 改造现有工具
- 进阶级: 从零实现系统
- 挑战级: 解决实际问题

### Phase 6: 保存到知识图谱

调用 knowledge/save 保存学习成果

---

## 改进点

相比 ECC deep-research:
- ✅ 增加学习路径生成
- ✅ 推荐实战项目
- ✅ 自动保存到知识图谱
- ✅ 资源质量评分机制
