---
name: summarize-knowledge
description: 从对话中总结知识点并添加到知识图谱
trigger: 用户点击"总结"按钮或输入"/summarize"
version: 1.0.0
---

# Summarize Knowledge Skill

## 任务说明

当用户输入 `/summarize` 或提到"总结"时，你需要：

1. **如果用户提供了文件路径**：
   - 使用 `read_file(file_path)` 读取文件内容
   - 基于文件内容提取知识点
   
2. **如果是总结对话**：
   - 回顾对话历史中的关键内容
   - 提取重要的技术概念、方法、工具

3. **提取知识点**：
   - 每个知识点包含：
     - **标题**：简短明确（20字以内）
     - **内容**：详细说明（100-300字）
     - **标签**：相关技术标签（如 ["Python", "FastAPI", "Web框架"]）
     - **类型**：concept（概念）/technology（技术）/method（方法）/tool（工具）
   - 至少提取 3 个知识点

4. **呈现格式**：
   使用清晰的 Markdown 格式列出所有知识点，方便用户确认

## 示例

**用户输入**：
```
/summarize 根据E:\Desktop\learning-system\docs\plan.md，讲解规划内容
```

**你的操作**：
1. 调用 `read_file("E:\\Desktop\\learning-system\\docs\\plan.md")` 读取文件
2. 分析文件内容，识别关键规划点
3. 提取知识点并格式化输出

**输出格式**：
```markdown
# 知识点总结

## 1. FastAPI 路由系统
**内容**：FastAPI 使用装饰器语法定义路由...
**标签**：["Python", "FastAPI", "Web框架"]
**类型**：technology

## 2. MCP 协议集成
**内容**：MCP（Model Context Protocol）是一个...
**标签**：["MCP", "协议", "AI集成"]
**类型**：concept

...
```

---

## 重要提示

- **直接使用工具**：当看到文件路径时，立即调用 `read_file`，不要输出工具调用的 XML 标记
- **保持简洁**：专注于提取核心知识点，避免冗长描述
- **用户确认**：提取完成后，等待用户确认是否保存到知识图谱
