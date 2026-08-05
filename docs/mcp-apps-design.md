# MCP Apps UI 设计方案

## 文档概述

**项目**：Learning System - MCP 2026 完整实现  
**阶段**：Phase 4 - MCP Apps（交互式 UI）  
**作者**：Claude Code  
**日期**：2026-08-03  
**版本**：v1.0

---

## 1. 设计理念

### 1.1 核心概念

**MCP Apps** 是 MCP 2026-07-28 协议引入的交互式 UI 扩展，核心理念是：

> **数据与展示分离**：服务器返回结构化的 UI 描述（JSON），客户端负责渲染和交互。

**优势**：
- **解耦**：服务器专注业务逻辑，客户端自由选择渲染技术
- **标准化**：遵循 MCP 协议，易于跨平台集成
- **灵活性**：同一数据可以适配不同客户端（Web、Desktop、Mobile）

### 1.2 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Server                              │
├─────────────────────────────────────────────────────────────┤
│  用户调用 Tool                                                │
│    ↓                                                          │
│  生成 UITemplateResult                                        │
│    ↓                                                          │
│  返回 JSON-RPC 响应：                                         │
│  {                                                            │
│    "jsonrpc": "2.0",                                          │
│    "id": 1,                                                   │
│    "result": { ... },                                         │
│    "_meta": {                                                 │
│      "io.modelcontextprotocol/uiTemplate": {                 │
│        "templateId": "com.learning-system.session-summary",  │
│        "data": { ... },                                       │
│        "actions": [ ... ]                                     │
│      }                                                        │
│    }                                                          │
│  }                                                            │
└─────────────────────────────────────────────────────────────┘
                           ↓ 网络传输
┌─────────────────────────────────────────────────────────────┐
│              MCP Client (Claude Desktop / Web App)           │
├─────────────────────────────────────────────────────────────┤
│  1. 接收 JSON 响应                                            │
│  2. 解析 _meta.uiTemplate                                     │
│  3. 渲染 UI 组件（基于 templateId）                           │
│  4. 用户交互（点击、输入、选择）                              │
│  5. 触发 action 回调 → 调用服务器 Tool                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 实现策略对比

#### 方案A：纯 JSON 描述（推荐）

**描述**：服务器返回 JSON 格式的 UI 组件树，客户端根据组件类型渲染

**示例**：
```json
{
  "templateId": "com.learning-system.session-summary",
  "components": [
    {"type": "header", "title": "学习总结"},
    {"type": "stats-grid", "items": [...]},
    {"type": "chart", "chartType": "bar", "data": {...}}
  ]
}
```

**优点**：
- ✅ 客户端无关，任何 MCP 客户端都能渲染
- ✅ 服务器不需要管理 HTML 模板
- ✅ 易于测试和调试（纯数据）
- ✅ 安全性高（无 XSS 风险）

**缺点**：
- ❌ 客户端需要实现完整的 UI 组件库
- ❌ 复杂交互需要定义标准协议
- ❌ 自定义样式受限

#### 方案B：HTML 模板 + JSON 数据

**描述**：服务器提供 HTML 模板文件路径 + JSON 数据，客户端渲染 HTML

**示例**：
```json
{
  "templateId": "com.learning-system.session-summary",
  "templatePath": "/templates/session_summary.html",
  "data": {
    "session_id": "sess-001",
    "knowledge_points": [...]
  }
}
```

**优点**：
- ✅ 服务器可以精确控制 UI 细节
- ✅ 复杂交互更容易实现（JavaScript）
- ✅ 丰富的样式自定义

**缺点**：
- ❌ 客户端需要支持 HTML 渲染（iframe/webview）
- ❌ 安全性问题（XSS、CSP）
- ❌ 跨平台兼容性差

#### 方案C：混合方案（本项目采用）✅

**策略**：
- **简单界面**（统计、列表、表单）→ 使用纯 JSON 描述
- **复杂界面**（知识图谱、图表）→ 提供 HTML 模板路径 + JSON 数据

**优势**：
- 兼顾灵活性和安全性
- 适配不同客户端能力
- 渐进式增强（客户端不支持 HTML 时降级到 JSON）

---

## 2. 四个 UI 界面设计

### 2.1 会话总结报告 (Session Summary)

#### 使用场景
**触发时机**：学习会话结束后（30分钟无活动，自动触发）

**用户需求**：
- 查看本次学习的知识点列表
- 了解学习时长和掌握程度
- 快速生成复习计划

#### UI 组件设计（纯 JSON）

```json
{
  "templateId": "com.learning-system.session-summary",
  "version": "1.0.0",
  "layout": "card",
  "theme": "auto",
  
  "sections": [
    {
      "type": "header",
      "title": "学习会话总结",
      "subtitle": "2026-08-03 10:00 - 12:30",
      "icon": "book-open"
    },
    
    {
      "type": "stats-grid",
      "columns": 4,
      "items": [
        {
          "label": "学习时长",
          "value": "2.5小时",
          "icon": "clock",
          "color": "blue"
        },
        {
          "label": "知识点数",
          "value": "8个",
          "icon": "lightbulb",
          "color": "yellow"
        },
        {
          "label": "平均难度",
          "value": "0.65",
          "icon": "trending-up",
          "color": "orange"
        },
        {
          "label": "总体掌握",
          "value": "78%",
          "icon": "check-circle",
          "color": "green"
        }
      ]
    },
    
    {
      "type": "knowledge-list",
      "title": "本次学习的知识点",
      "items": [
        {
          "id": "k-001",
          "title": "FastAPI 依赖注入",
          "difficulty": 0.7,
          "mastery": 0.8,
          "tags": ["Python", "FastAPI", "后端"]
        }
      ]
    }
  ]
}
```

#### 数据模型

```python
from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class KnowledgePoint:
    id: str
    title: str
    difficulty: float  # 0.0 - 1.0
    mastery: float     # 0.0 - 1.0
    tags: List[str]

@dataclass
class SessionSummaryData:
    session_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    knowledge_points: List[KnowledgePoint]
```

---

### 2.2 知识图谱可视化 (Knowledge Graph)

#### 使用场景
**触发时机**：用户主动查看知识关系、发现学习路径

**用户需求**：
- 可视化知识节点和关系
- 点击节点查看详情
- 过滤和搜索节点

#### UI 组件设计（HTML + JSON）

**为什么用 HTML？**
- 图谱渲染需要复杂的交互逻辑（缩放、拖拽、力导向布局）
- D3.js / Cytoscape.js 等库需要完整的 DOM 环境
- 纯 JSON 描述成本过高

```json
{
  "templateId": "com.learning-system.knowledge-graph",
  "version": "1.0.0",
  "layout": "fullscreen",
  "templatePath": "/templates/knowledge_graph.html",
  
  "data": {
    "nodes": [
      {
        "id": "k-001",
        "label": "FastAPI",
        "type": "technology",
        "mastery": 0.8,
        "metadata": {
          "created_at": "2026-07-28",
          "last_reviewed": "2026-08-03"
        }
      },
      {
        "id": "k-002",
        "label": "依赖注入",
        "type": "concept",
        "mastery": 0.75,
        "metadata": {}
      }
    ],
    
    "edges": [
      {
        "source": "k-002",
        "target": "k-001",
        "relation": "used_in",
        "label": "应用于"
      }
    ],
    
    "config": {
      "layout": "force",
      "physics": {
        "enabled": true,
        "gravity": 0.3,
        "repulsion": 100
      },
      "style": {
        "nodeColor": {
          "technology": "#4CAF50",
          "concept": "#2196F3",
          "project": "#FF9800"
        },
        "edgeColor": "#999999"
      }
    }
  },
  
  "actions": {
    "node_click": {
      "toolName": "view_knowledge_detail",
      "params": {"knowledge_id": "{node.id}"}
    },
    "node_double_click": {
      "toolName": "expand_knowledge_graph",
      "params": {"knowledge_id": "{node.id}"}
    }
  }
}
```

#### 数据模型

```python
@dataclass
class GraphNode:
    id: str
    label: str
    type: str  # technology, concept, project
    mastery: float
    metadata: dict

@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str  # prerequisite_of, related_to, used_in
    weight: float = 1.0

@dataclass
class KnowledgeGraphData:
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    config: dict
```

#### HTML 模板示例

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Knowledge Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; overflow: hidden; }
        #graph { width: 100vw; height: 100vh; }
        .node { cursor: pointer; }
        .node:hover { opacity: 0.8; }
    </style>
</head>
<body>
    <div id="graph"></div>
    <script>
        // MCP Client 会注入数据到 window.__MCP_DATA__
        const data = window.__MCP_DATA__;
        
        // D3.js 力导向图渲染
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.edges).id(d => d.id))
            .force("charge", d3.forceManyBody().strength(-100))
            .force("center", d3.forceCenter(width / 2, height / 2));
        
        // 绘制边
        const link = svg.append("g")
            .selectAll("line")
            .data(data.edges)
            .enter().append("line")
            .attr("stroke", "#999")
            .attr("stroke-width", 2);
        
        // 绘制节点
        const node = svg.append("g")
            .selectAll("circle")
            .data(data.nodes)
            .enter().append("circle")
            .attr("r", 20)
            .attr("fill", d => data.config.style.nodeColor[d.type])
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended))
            .on("click", (event, d) => {
                // 调用 MCP Tool
                window.__MCP_CALL_TOOL__("view_knowledge_detail", {
                    knowledge_id: d.id
                });
            });
        
        // 节点标签
        const label = svg.append("g")
            .selectAll("text")
            .data(data.nodes)
            .enter().append("text")
            .text(d => d.label)
            .attr("font-size", 12)
            .attr("dx", 25);
        
        simulation.on("tick", () => {
            link.attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node.attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            label.attr("x", d => d.x)
                 .attr("y", d => d.y);
        });
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    </script>
</body>
</html>
```

---

### 2.3 项目分析配置界面 (Project Config)

#### 使用场景
**触发时机**：用户启动项目分析前，选择分析策略

**用户需求**：
- 选择分析深度（快速/标准/深度）
- 选择分析维度（架构/技术栈/亮点）
- 查看预计耗时

#### UI 组件设计（纯 JSON - Wizard 风格）

```json
{
  "templateId": "com.learning-system.project-config",
  "version": "1.0.0",
  "layout": "wizard",
  
  "steps": [
    {
      "id": "step1",
      "title": "选择分析策略",
      "type": "radio-group",
      "field": "strategy",
      "required": true,
      
      "options": [
        {
          "value": "quick",
          "label": "快速分析",
          "description": "5-10 秒，基础代码结构",
          "icon": "zap",
          "eta_seconds": 10
        },
        {
          "value": "standard",
          "label": "标准分析",
          "description": "1-2 分钟，架构 + 技术栈",
          "icon": "layers",
          "recommended": true,
          "eta_seconds": 90
        },
        {
          "value": "deep",
          "label": "深度分析",
          "description": "5-10 分钟，完整分析 + 亮点提取",
          "icon": "search",
          "eta_seconds": 600
        }
      ]
    },
    
    {
      "id": "step2",
      "title": "选择分析维度",
      "type": "checkbox-group",
      "field": "dimensions",
      
      "options": [
        {"value": "architecture", "label": "架构模式", "checked": true},
        {"value": "tech_stack", "label": "技术栈", "checked": true},
        {"value": "code_quality", "label": "代码质量", "checked": false},
        {"value": "security", "label": "安全性", "checked": false},
        {"value": "highlights", "label": "项目亮点", "checked": true},
        {"value": "interview_prep", "label": "面试准备", "checked": true}
      ]
    },
    
    {
      "id": "step3",
      "title": "确认配置",
      "type": "summary",
      
      "fields": [
        {"label": "项目路径", "value": "{project_path}"},
        {"label": "分析策略", "value": "{strategy}"},
        {"label": "分析维度", "value": "{dimensions}"},
        {"label": "预计时间", "value": "{eta}"}
      ]
    }
  ],
  
  "actions": {
    "submit": {
      "label": "开始分析",
      "toolName": "start_project_analysis",
      "params": {
        "project_path": "{project_path}",
        "strategy": "{strategy}",
        "dimensions": "{dimensions}"
      }
    },
    "cancel": {
      "label": "取消",
      "action": "close"
    }
  }
}
```

#### 数据模型

```python
@dataclass
class ProjectAnalysisConfig:
    project_path: str
    strategy: str  # quick, standard, deep
    dimensions: List[str]
    estimated_seconds: int
```

---

### 2.4 复习进度仪表盘 (Review Dashboard)

#### 使用场景
**触发时机**：每日启动时自动展示

**用户需求**：
- 查看今日复习任务
- 了解知识掌握度分布
- 查看学习趋势

#### UI 组件设计（纯 JSON - Dashboard 风格）

```json
{
  "templateId": "com.learning-system.review-dashboard",
  "version": "1.0.0",
  "layout": "dashboard",
  
  "widgets": [
    {
      "id": "today-tasks",
      "type": "card",
      "title": "今日复习任务",
      "priority": "high",
      "span": 2,
      
      "content": {
        "type": "task-list",
        "items": [
          {
            "id": "k-001",
            "knowledge": "FastAPI 依赖注入",
            "due": "今天",
            "priority": "high",
            "action": {
              "label": "开始复习",
              "toolName": "start_review",
              "params": {"knowledge_id": "k-001"}
            }
          }
        ]
      }
    },
    
    {
      "id": "mastery-distribution",
      "type": "card",
      "title": "掌握度分布",
      "span": 1,
      
      "content": {
        "type": "donut-chart",
        "data": {
          "labels": ["已掌握", "熟悉", "学习中", "待复习"],
          "values": [12, 18, 15, 5],
          "colors": ["#4CAF50", "#8BC34A", "#FFC107", "#FF5722"]
        }
      }
    },
    
    {
      "id": "learning-curve",
      "type": "card",
      "title": "学习曲线 (最近7天)",
      "span": 2,
      
      "content": {
        "type": "line-chart",
        "data": {
          "labels": ["07-28", "07-29", "07-30", "07-31", "08-01", "08-02", "08-03"],
          "datasets": [
            {
              "label": "新增知识点",
              "values": [3, 5, 2, 4, 6, 3, 8],
              "color": "#2196F3"
            },
            {
              "label": "复习次数",
              "values": [1, 2, 3, 1, 2, 4, 2],
              "color": "#FF9800"
            }
          ]
        }
      }
    }
  ],
  
  "quick_actions": [
    {
      "label": "开始复习",
      "style": "primary",
      "toolName": "start_review_session"
    },
    {
      "label": "查看知识图谱",
      "style": "secondary",
      "toolName": "show_knowledge_graph"
    }
  ]
}
```

#### 数据模型

```python
@dataclass
class ReviewTask:
    knowledge_id: str
    title: str
    due_date: str
    priority: str

@dataclass
class ReviewDashboardData:
    today_tasks: List[ReviewTask]
    mastery_distribution: dict
    learning_curve: dict
    weekly_summary: dict
```

---

## 3. 技术实现方案

### 3.1 服务器端架构

#### 目录结构

```
mcp-server/
├── src/
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── template_manager.py      # UI 模板管理器
│   │   ├── components.py            # 标准 UI 组件定义
│   │   └── validators.py            # UI 数据验证
│   ├── tools/
│   │   ├── ui_session_summary.py    # 会话总结 UI Tool
│   │   ├── ui_knowledge_graph.py    # 知识图谱 UI Tool
│   │   ├── ui_project_config.py     # 项目配置 UI Tool
│   │   └── ui_review_dashboard.py   # 复习仪表盘 UI Tool
│   └── protocol/
│       └── result_types.py          # UITemplateResult 已实现
├── templates/
│   └── knowledge_graph.html         # 知识图谱 HTML 模板
└── tests/
    └── test_ui_templates.py         # UI 测试
```

#### 核心类设计

**TemplateManager**：管理所有 UI 模板

```python
class TemplateManager:
    def __init__(self):
        self.templates = {}
        self.validators = {}
    
    def register_template(
        self, 
        template_id: str, 
        validator: Callable = None
    ):
        """注册 UI 模板"""
        self.templates[template_id] = {
            "validator": validator
        }
    
    def validate_data(
        self, 
        template_id: str, 
        data: dict
    ) -> bool:
        """验证 UI 数据"""
        validator = self.validators.get(template_id)
        if validator:
            return validator(data)
        return True
    
    def render_template(
        self, 
        template_id: str, 
        data: dict
    ) -> UITemplateResult:
        """渲染 UI 模板"""
        if not self.validate_data(template_id, data):
            raise ValueError(f"Invalid data for template {template_id}")
        
        return UITemplateResult(
            template_id=template_id,
            template_path=self._get_template_path(template_id),
            template_data=data
        )
```

**UIComponent**：标准 UI 组件定义

```python
from enum import Enum
from typing import Any, Dict, List, Optional

class ComponentType(Enum):
    HEADER = "header"
    STATS_GRID = "stats-grid"
    KNOWLEDGE_LIST = "knowledge-list"
    CHART = "chart"
    ACTION_BAR = "action-bar"
    CARD = "card"
    TASK_LIST = "task-list"

@dataclass
class UIComponent:
    type: ComponentType
    props: Dict[str, Any]
    children: List['UIComponent'] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为 JSON"""
        result = {
            "type": self.type.value,
            **self.props
        }
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result

# 组件工厂函数
def create_header(title: str, subtitle: str = None, icon: str = None) -> UIComponent:
    return UIComponent(
        type=ComponentType.HEADER,
        props={"title": title, "subtitle": subtitle, "icon": icon}
    )

def create_stats_grid(items: List[dict], columns: int = 4) -> UIComponent:
    return UIComponent(
        type=ComponentType.STATS_GRID,
        props={"items": items, "columns": columns}
    )

def create_chart(
    chart_type: str, 
    title: str, 
    data: dict, 
    config: dict = None
) -> UIComponent:
    return UIComponent(
        type=ComponentType.CHART,
        props={
            "chartType": chart_type,
            "title": title,
            "data": data,
            "config": config or {}
        }
    )
```

### 3.2 Tool 实现示例

#### 会话总结 UI Tool

```python
@mcp_tool("ui/session_summary")
async def generate_session_summary_ui(session_id: str) -> UITemplateResult:
    """
    生成会话总结 UI
    
    Args:
        session_id: 会话ID
        
    Returns:
        UITemplateResult: 包含会话总结的 UI 模板
    """
    # 1. 获取会话数据
    session = await session_analyzer.get_session(session_id)
    
    if not session:
        raise MCPError(f"Session not found: {session_id}")
    
    # 2. 构建 UI 组件
    components = []
    
    # Header
    components.append(create_header(
        title="学习会话总结",
        subtitle=f"{session.start_time.strftime('%Y-%m-%d %H:%M')} - "
                 f"{session.end_time.strftime('%H:%M')}",
        icon="book-open"
    ))
    
    # Stats Grid
    duration_hours = round(session.duration_minutes / 60, 1)
    components.append(create_stats_grid([
        {
            "label": "学习时长",
            "value": f"{duration_hours}小时",
            "icon": "clock",
            "color": "blue"
        },
        {
            "label": "知识点数",
            "value": f"{len(session.knowledge_points)}个",
            "icon": "lightbulb",
            "color": "yellow"
        },
        {
            "label": "平均难度",
            "value": f"{session.avg_difficulty:.2f}",
            "icon": "trending-up",
            "color": "orange"
        },
        {
            "label": "总体掌握",
            "value": f"{int(session.avg_mastery * 100)}%",
            "icon": "check-circle",
            "color": "green"
        }
    ]))
    
    # Knowledge List
    knowledge_items = [
        {
            "id": kp.id,
            "title": kp.title,
            "difficulty": kp.difficulty,
            "mastery": kp.mastery,
            "tags": kp.tags,
            "action": {
                "label": "查看详情",
                "toolName": "view_knowledge_detail",
                "params": {"knowledge_id": kp.id}
            }
        }
        for kp in session.knowledge_points
    ]
    
    components.append(UIComponent(
        type=ComponentType.KNOWLEDGE_LIST,
        props={
            "title": "本次学习的知识点",
            "items": knowledge_items
        }
    ))
    
    # Chart
    mastery_distribution = calculate_mastery_distribution(session.knowledge_points)
    components.append(create_chart(
        chart_type="bar",
        title="掌握度分布",
        data={
            "labels": ["0.0-0.3", "0.3-0.5", "0.5-0.7", "0.7-0.9", "0.9-1.0"],
            "values": list(mastery_distribution.values()),
            "colors": ["#FF5722", "#FF9800", "#FFC107", "#8BC34A", "#4CAF50"]
        },
        config={"height": 200, "showLegend": False}
    ))
    
    # 3. 构建完整 UI 数据
    ui_data = {
        "session_id": session_id,
        "sections": [comp.to_dict() for comp in components]
    }
    
    # 4. 返回 UITemplateResult
    return UITemplateResult(
        template_id="com.learning-system.session-summary",
        template_path="",  # 纯 JSON，不需要 HTML
        template_data=ui_data
    )

def calculate_mastery_distribution(knowledge_points: List[KnowledgePoint]) -> dict:
    """计算掌握度分布"""
    distribution = {
        "0.0-0.3": 0,
        "0.3-0.5": 0,
        "0.5-0.7": 0,
        "0.7-0.9": 0,
        "0.9-1.0": 0
    }
    
    for kp in knowledge_points:
        if kp.mastery < 0.3:
            distribution["0.0-0.3"] += 1
        elif kp.mastery < 0.5:
            distribution["0.3-0.5"] += 1
        elif kp.mastery < 0.7:
            distribution["0.5-0.7"] += 1
        elif kp.mastery < 0.9:
            distribution["0.7-0.9"] += 1
        else:
            distribution["0.9-1.0"] += 1
    
    return distribution
```

#### 知识图谱 UI Tool

```python
@mcp_tool("ui/knowledge_graph")
async def generate_knowledge_graph_ui(
    knowledge_ids: List[str] = None,
    depth: int = 2
) -> UITemplateResult:
    """
    生成知识图谱 UI
    
    Args:
        knowledge_ids: 起始知识节点ID列表（为空则显示全部）
        depth: 展开深度（1-3）
        
    Returns:
        UITemplateResult: 包含知识图谱的 UI 模板
    """
    # 1. 获取图谱数据
    if knowledge_ids:
        graph_data = await memory_manager.get_subgraph(knowledge_ids, depth)
    else:
        graph_data = await memory_manager.get_full_graph()
    
    # 2. 转换为 UI 格式
    nodes = [
        {
            "id": node.id,
            "label": node.title,
            "type": node.type,
            "mastery": node.mastery,
            "metadata": {
                "created_at": node.created_at.isoformat(),
                "last_reviewed": node.last_reviewed.isoformat() if node.last_reviewed else None
            }
        }
        for node in graph_data.nodes
    ]
    
    edges = [
        {
            "source": edge.source_id,
            "target": edge.target_id,
            "relation": edge.relation_type,
            "label": RELATION_LABELS.get(edge.relation_type, edge.relation_type)
        }
        for edge in graph_data.edges
    ]
    
    # 3. 配置图谱渲染
    config = {
        "layout": "force",
        "physics": {
            "enabled": True,
            "gravity": 0.3,
            "repulsion": 100
        },
        "style": {
            "nodeColor": {
                "technology": "#4CAF50",
                "concept": "#2196F3",
                "project": "#FF9800"
            },
            "edgeColor": "#999999"
        }
    }
    
    # 4. 定义交互动作
    actions = {
        "node_click": {
            "toolName": "view_knowledge_detail",
            "params": {"knowledge_id": "{node.id}"}
        },
        "node_double_click": {
            "toolName": "expand_knowledge_graph",
            "params": {"knowledge_id": "{node.id}", "depth": 1}
        }
    }
    
    # 5. 构建 UI 数据
    ui_data = {
        "nodes": nodes,
        "edges": edges,
        "config": config
    }
    
    # 6. 返回 UITemplateResult（使用 HTML 模板）
    return UITemplateResult(
        template_id="com.learning-system.knowledge-graph",
        template_path="/templates/knowledge_graph.html",
        template_data=ui_data
    )

# 关系类型标签映射
RELATION_LABELS = {
    "prerequisite_of": "前置知识",
    "related_to": "相关",
    "used_in": "应用于",
    "part_of": "属于"
}
```

### 3.3 客户端交互协议

#### Tool 回调机制

当用户在 UI 中点击按钮时，客户端需要调用服务器的 Tool：

```javascript
// 客户端代码示例（伪代码）
function handleButtonClick(action) {
    const toolName = action.toolName;
    const params = resolveParams(action.params);
    
    // 调用 MCP Tool
    mcpClient.callTool(toolName, params)
        .then(result => {
            // 处理结果
            if (result._meta?.["io.modelcontextprotocol/uiTemplate"]) {
                // 渲染新的 UI
                renderUI(result._meta["io.modelcontextprotocol/uiTemplate"]);
            } else {
                // 显示结果
                showResult(result.result);
            }
        })
        .catch(error => {
            showError(error.message);
        });
}

function resolveParams(params) {
    // 解析参数中的占位符（如 {node.id}）
    // 替换为实际值
    return params;
}
```

#### 数据注入机制

对于 HTML 模板，客户端需要注入数据：

```javascript
// 客户端渲染 HTML 模板
function renderHTMLTemplate(templatePath, data) {
    // 1. 加载 HTML 模板
    const html = loadTemplate(templatePath);
    
    // 2. 创建 iframe 或 webview
    const iframe = document.createElement('iframe');
    iframe.sandbox = 'allow-scripts';  // 安全沙箱
    
    // 3. 注入数据
    iframe.onload = () => {
        iframe.contentWindow.__MCP_DATA__ = data;
        
        // 注入 Tool 调用函数
        iframe.contentWindow.__MCP_CALL_TOOL__ = (toolName, params) => {
            return mcpClient.callTool(toolName, params);
        };
    };
    
    // 4. 设置 HTML 内容
    iframe.srcdoc = html;
    
    // 5. 添加到 DOM
    document.body.appendChild(iframe);
}
```

---

## 4. 实施计划

### 4.1 任务拆解（Phase 4）

#### Task 4.1：UI 模板系统基础（1天）

**目标**：搭建 UI 模板管理框架

**交付物**：
- `src/ui/__init__.py`
- `src/ui/template_manager.py` - TemplateManager 类
- `src/ui/components.py` - 标准组件定义
- `src/ui/validators.py` - 数据验证器

**验收标准**：
```python
# 测试代码
template_mgr = TemplateManager()
template_mgr.register_template("test-template")

ui_result = template_mgr.render_template(
    template_id="test-template",
    data={"title": "Test"}
)

assert ui_result.template_id == "test-template"
assert ui_result.to_jsonrpc(1)["_meta"] is not None
```

#### Task 4.2：实现会话总结 UI（1天）

**目标**：实现第一个 UI 界面（纯 JSON）

**交付物**：
- `src/tools/ui_session_summary.py`
- 集成到 `server.py`

**验收标准**：
```bash
# 调用 Tool
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ui/session_summary","arguments":{"session_id":"sess-001"}}}' | python server.py

# 返回包含 _meta.uiTemplate
```

#### Task 4.3：实现知识图谱 UI（1.5天）

**目标**：实现复杂交互界面（HTML + JSON）

**交付物**：
- `templates/knowledge_graph.html` - D3.js 图谱
- `src/tools/ui_knowledge_graph.py`

**验收标准**：
- HTML 模板能独立渲染（手动测试）
- Tool 返回正确的 templatePath 和 data

#### Task 4.4：实现项目配置 UI（0.5天）

**目标**：实现 Wizard 风格界面

**交付物**：
- `src/tools/ui_project_config.py`

**验收标准**：
- 返回多步骤表单结构
- 支持默认值和验证规则

#### Task 4.5：实现复习仪表盘 UI（1天）

**目标**：实现 Dashboard 风格界面

**交付物**：
- `src/tools/ui_review_dashboard.py`

**验收标准**：
- 包含多个 widget（任务列表、图表、统计）
- 支持快速操作按钮

#### Task 4.6：测试和文档（1天）

**目标**：编写测试和使用文档

**交付物**：
- `tests/test_ui_templates.py` - 单元测试
- `tests/test_ui_integration.py` - 集成测试
- `docs/mcp-apps-usage.md` - 使用指南

**验收标准**：
- 测试覆盖率 >80%
- 文档包含完整示例

### 4.2 时间估算

| 任务 | 预计时间 | 备注 |
|------|---------|------|
| Task 4.1 | 1天 | 基础框架 |
| Task 4.2 | 1天 | 第一个界面（模板） |
| Task 4.3 | 1.5天 | HTML + D3.js |
| Task 4.4 | 0.5天 | 复用框架 |
| Task 4.5 | 1天 | Dashboard 组件 |
| Task 4.6 | 1天 | 测试文档 |
| **总计** | **6天** | 实际可能 5-7 天 |

### 4.3 技术风险

#### 风险1：客户端不支持 HTML 渲染

**影响**：知识图谱无法展示

**缓解方案**：
- 提供纯 JSON 降级方案（简化版图谱）
- 使用 ASCII Art 或文本树形结构

#### 风险2：D3.js 复杂度高

**影响**：开发时间延长

**缓解方案**：
- 使用现成的 D3.js 力导向图模板
- 先实现基础版本，后续迭代优化

#### 风险3：数据量过大导致渲染慢

**影响**：用户体验差

**缓解方案**：
- 限制节点数量（最多100个）
- 支持分页加载
- 添加虚拟化渲染

---

## 5. 面试要点

### 5.1 为什么用 MCP Apps？

**问题**：为什么不直接用传统 Web UI？

**回答要点**：
1. **解耦架构**：服务器专注业务逻辑，UI 由客户端负责
2. **跨平台复用**：同一数据可以适配 Web、Desktop、Mobile
3. **标准协议**：遵循 MCP 标准，易于集成和扩展
4. **渐进增强**：客户端能力不足时可降级到纯文本

**深入问题**：如果客户端不支持复杂渲染怎么办？

**回答**：
- 提供多级降级方案
- 纯 JSON → 简化 JSON → 纯文本
- 示例：知识图谱 → 文本树 → 节点列表

### 5.2 UI 组件标准化

**问题**：如何保证不同客户端渲染一致？

**回答要点**：
1. **定义标准组件库**：Button、Card、Chart 等
2. **约定渲染规范**：颜色、间距、字体
3. **提供参考实现**：Web 端示例代码
4. **版本控制**：templateId 包含版本号

**深入问题**：如果需要自定义样式怎么办？

**回答**：
- 支持 theme 字段（light/dark/custom）
- 允许传递 style 对象（受限的 CSS）
- 客户端可以覆盖默认样式

### 5.3 安全性考虑

**问题**：HTML 模板有 XSS 风险吗？

**回答要点**：
1. **沙箱隔离**：iframe sandbox 模式
2. **CSP 策略**：限制脚本来源
3. **输入验证**：服务器端验证所有数据
4. **模板审查**：HTML 模板经过人工审核

**深入问题**：如果用户注入恶意代码？

**回答**：
- 所有用户输入都经过转义（HTML entities）
- JSON 数据不包含可执行代码
- 客户端渲染时进行二次验证

### 5.4 性能优化

**问题**：大量数据如何优化渲染？

**回答要点**：
1. **分页加载**：限制单次返回的节点数
2. **虚拟化渲染**：只渲染可见区域
3. **数据压缩**：使用简洁的 JSON 结构
4. **缓存机制**：添加 ttlMs 元数据

**深入问题**：知识图谱有1000个节点怎么办？

**回答**：
- 按需加载：先显示核心节点，点击展开
- 聚合显示：相似节点合并为一个
- 搜索过滤：支持按标签、类型过滤

### 5.5 与其他系统对比

**问题**：MCP Apps 与 GraphQL、REST API 有什么区别？

**回答**：

| 维度 | MCP Apps | GraphQL | REST API |
|------|----------|---------|----------|
| **目的** | UI 交互 | 数据查询 | 资源操作 |
| **返回** | UI 描述 + 数据 | 纯数据 | 纯数据 |
| **客户端** | 渲染 UI | 构建 UI | 构建 UI |
| **标准** | MCP 协议 | GraphQL 规范 | HTTP 约定 |
| **优势** | 服务器控制 UI | 按需查询 | 简单通用 |

**MCP Apps 的独特价值**：
- 服务器可以**推送 UI**（不仅是数据）
- 支持**多轮交互**（通过 MRTR）
- 集成**任务进度**（通过 taskHandle）

---

## 6. 扩展方向

### 6.1 未来可实现的 UI

1. **面试准备助手**
   - 项目亮点提炼
   - 面试问答生成
   - STAR 方法指导

2. **学习路径规划器**
   - 技能树可视化
   - 前置知识检测
   - 学习时间估算

3. **代码审查报告**
   - 代码质量评分
   - 安全漏洞检测
   - 重构建议

4. **多人协作面板**
   - 团队学习进度
   - 知识共享看板
   - 学习打卡排行榜

### 6.2 客户端生态

**Claude Desktop**：
- 原生渲染 MCP Apps
- 支持 Markdown + 嵌入式组件

**Web 客户端**：
- 完整的 HTML 支持
- 丰富的交互动画

**命令行客户端**：
- 纯文本降级
- ASCII Art 图表

**移动端客户端**：
- 适配触控操作
- 响应式布局

---

## 7. 总结

### 7.1 设计亮点

1. **数据与展示分离**：服务器返回 JSON，客户端自由渲染
2. **混合实现策略**：简单界面用 JSON，复杂界面用 HTML
3. **标准化组件库**：统一的 UI 组件定义
4. **渐进式增强**：支持多级降级方案
5. **安全性优先**：沙箱隔离 + 输入验证

### 7.2 技术价值

1. **遵循 MCP 标准**：展示对协议的深入理解
2. **前后端分离**：展示架构设计能力
3. **数据可视化**：D3.js 图谱渲染
4. **用户体验**：交互式 UI 提升易用性

### 7.3 面试准备

**核心话术**：
> "我实现了 MCP Apps 交互式 UI 扩展，采用数据与展示分离的设计理念。服务器返回结构化的 JSON 描述，客户端负责渲染和交互。实现了 4 个界面：会话总结、知识图谱、项目配置、复习仪表盘。其中知识图谱使用 D3.js 力导向布局，支持节点拖拽和交互。通过混合实现策略，兼顾了灵活性和安全性。"

**技术关键词**：
- MCP Apps
- UITemplateResult
- 数据与展示分离
- D3.js 力导向图
- 组件化设计
- 渐进式增强
- 沙箱安全

### 7.4 下一步

完成 Phase 4 后，继续 Phase 5：Extensions 框架（动态工具注册）

---

**文档版本**：v1.0  
**最后更新**：2026-08-03  
**作者**：Claude Code

