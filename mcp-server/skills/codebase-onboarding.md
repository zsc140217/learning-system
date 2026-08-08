---
name: codebase-onboarding
description: 快速理解陌生代码库的架构、技术栈和设计模式
trigger: 用户请求分析项目或准备面试
tools: project_analyze_status, project/detect_framework, project/scan_structure, project/analyze_dependencies, project/extract_patterns
output: 结构化的项目分析报告
---

# Codebase Onboarding Skill

快速理解一个陌生项目的架构和技术栈，生成学习路径和面试要点。

**参考来源**: ECC codebase-onboarding skill  
**适用场景**: 准备项目面试、学习新代码库、技术栈分析

---

## 工作流程

### Phase 0: 一键分析（推荐）

**目标**: 使用整合工具快速生成完整的项目分析报告

**步骤**:

1. **调用综合分析工具**
   ```
   调用工具: project_analyze_status
   输入: {
     "project_path": "<用户提供的路径>",
     "depth": 3,
     "output_format": "json"
   }
   
   预期输出:
   {
     "project_name": "learning-system",
     "summary": {
       "tech_stack": ["Python - FastAPI"],
       "complexity": "中等",
       "completion_percentage": 80,
       "framework_confidence": 0.95,
       "total_dependencies": 25,
       "has_tests": true,
       "has_documentation": true
     },
     "todos": [
       {
         "priority": "high",
         "category": "测试",
         "task": "添加测试框架和单元测试",
         "reason": "项目缺少测试目录"
       }
     ],
     "learning_suggestions": [
       {
         "level": "基础",
         "topic": "Python 和 FastAPI 基础",
         "resources": ["官方文档: FastAPI", "Python 最佳实践"],
         "estimated_time": "1-2周"
       }
     ],
     "analysis_phases": {
       "framework_detection": {...},
       "structure_scan": {...},
       "dependencies_analysis": {...},
       "pattern_extraction": {...}
     }
   }
   ```

**处理逻辑**:
- 这个工具整合了 Phase 1-4 的所有分析步骤
- 一次调用即可获得完整的项目分析报告
- 如果需要更细粒度的控制，可以使用下面的 Phase 1-4

**输出**: 完整的项目分析报告（包含摘要、待办、学习建议）

---

### Phase 1: 快速侦查（30秒）

**目标**: 不读代码，快速识别项目类型

**步骤**:

1. **检测框架**
   ```
   调用工具: project/detect_framework
   输入: {"project_path": "<用户提供的路径>"}
   
   预期输出:
   {
     "framework": "FastAPI",
     "confidence": 0.9,
     "language": "Python",
     "version": "3.10+",
     "entry_points": ["server.py", "main.py"]
   }
   ```

2. **扫描目录结构**
   ```
   调用工具: project/scan_structure
   输入: {"project_path": "<路径>", "depth": 2}
   
   预期输出:
   {
     "directories": ["src/", "tests/", "docs/", "client/"],
     "key_files": ["server.py", "requirements.txt", "CLAUDE.md"],
     "config_files": ["pyproject.toml", "pytest.ini"]
   }
   ```

**处理逻辑**:
- 如果 confidence < 0.7，告知用户"项目类型不明确，建议手动确认"
- 识别出 entry_points 后，记录下来供后续分析使用

**输出**: 项目快照
```json
{
  "language": "Python",
  "framework": "FastAPI",
  "confidence": 0.9,
  "structure": {
    "backend": "mcp-server/",
    "frontend": "client/",
    "docs": "docs/"
  }
}
```

---

### Phase 2: 依赖分析（1分钟）

**目标**: 理解核心技术栈和第三方依赖

**步骤**:

1. **分析依赖**
   ```
   调用工具: project/analyze_dependencies
   输入: {"project_path": "<路径>"}
   
   预期输出:
   {
     "dependencies": [
       {"name": "fastapi", "version": "0.100.0", "type": "core"},
       {"name": "pydantic", "version": "2.0.0", "type": "core"},
       {"name": "pytest", "version": "7.0.0", "type": "dev"}
     ],
     "total_count": 15
   }
   ```

**处理逻辑**:
- 按类型分组: core (核心依赖), dev (开发依赖), optional (可选依赖)
- 识别关键技术: Web框架、数据库、测试框架、异步库
- 评估技术栈复杂度: dependencies < 10 → 简单, 10-30 → 中等, > 30 → 复杂

**输出**: 技术栈清单
```json
{
  "core_stack": [
    {"name": "FastAPI", "role": "Web框架", "version": "0.100.0"},
    {"name": "Pydantic", "role": "数据验证", "version": "2.0.0"}
  ],
  "dev_tools": [
    {"name": "pytest", "role": "测试框架"}
  ],
  "complexity": "中等"
}
```

---

### Phase 3: 代码模式识别（2分钟）

**目标**: 提取设计模式和编码习惯

**步骤**:

1. **提取代码模式**
   ```
   调用工具: project/extract_patterns
   输入: {
     "project_path": "<路径>",
     "focus": ["decorators", "async", "inheritance"]
   }
   
   预期输出:
   {
     "patterns": [
       {
         "type": "decorator",
         "usage": "@server.tool",
         "count": 8,
         "files": ["server.py"]
       },
       {
         "type": "async",
         "usage": "async/await",
         "count": 15,
         "files": ["server.py", "mcp_client.py"]
       }
     ],
     "conventions": {
       "naming": "snake_case",
       "async_usage": "high",
       "type_hints": "partial"
     }
   }
   ```

**处理逻辑**:
- 识别设计模式: Decorator, Strategy, Repository, Factory
- 分析编码风格: 命名约定、异步使用率、类型注解覆盖率
- 评估代码质量: 模式使用 → 高质量, 混乱模式 → 需重构

**输出**: 设计模式清单
```json
{
  "patterns": [
    {
      "name": "Decorator Pattern",
      "location": "server.py:@server.tool",
      "purpose": "MCP 工具注册"
    },
    {
      "name": "Strategy Pattern",
      "location": "src/extensions/",
      "purpose": "语言分析器插件系统"
    }
  ],
  "conventions": {
    "naming": "snake_case (文件和函数)",
    "async": "高频使用 async/await",
    "types": "部分类型注解 (约60%)"
  }
}
```

---

### Phase 4: 生成学习材料（综合）

**目标**: 为面试准备材料

**步骤**:

1. **合并前 3 个阶段的结果**
2. **生成学习路径**
3. **提取面试亮点**

**输出格式**:
```json
{
  "project_overview": {
    "name": "learning-system",
    "purpose": "AI-First 学习系统，基于 MCP 协议管理项目经验和知识图谱",
    "tech_stack": ["Python 3.10+", "FastAPI", "MCP Protocol", "React", "TypeScript"]
  },
  "learning_path": [
    {
      "step": 1,
      "topic": "MCP 协议基础",
      "resources": ["server.py", "docs/mcp-features-mapping.md"]
    }
  ],
  "interview_highlights": [
    {
      "category": "架构设计",
      "highlight": "实现了 AI-First 架构",
      "impact": "工作流可配置，支持动态组合"
    }
  ]
}
```

---

## 使用示例

```
用户: "帮我分析 learning-system 项目，准备面试"

系统执行:
1. Phase 1: 检测到 FastAPI + MCP
2. Phase 2: 识别核心技术栈
3. Phase 3: 提取 Decorator、Strategy 等模式
4. Phase 4: 生成学习路径和面试亮点
```
