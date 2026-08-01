# 🧠 Learning System

**AI驱动的学习成长系统** - 基于MCP 2026-07-28协议的Multi-Agent知识管理平台

## 📖 项目概述

Learning System是一个智能学习助手，帮助你：
- 📝 **自动总结会话** - 每次对话结束后提取关键知识
- 🗂️ **管理知识图谱** - 技术、项目、概念的关系网络
- 📊 **追踪项目进展** - 自动分析代码、提取面试亮点
- 🔍 **探索新技术** - 深度调研前沿技术并生成学习路径
- 📅 **生成复习计划** - 间隔重复算法，巩固所学知识

## ✅ 安装状态

### 已完成
- ✅ Memory MCP安装成功 (v0.8.0)
- ✅ 项目结构创建完成
- ✅ Git仓库初始化完成

### 待完成
- ⏳ 配置Memory MCP插件
- ⏳ 编写核心设计文档
- ⏳ 实现Agent基础框架

## 🚀 快速开始

### 1. 配置Memory MCP插件

```bash
# 添加Memory MCP插件到Claude Code
claude plugins add michael-denyer/memory-mcp

# 或手动配置 ~/.claude/settings.json
```

### 2. 验证安装

```bash
# 检查Memory MCP是否可用
python -c "import hot_memory_mcp; print('Memory MCP installed:', hot_memory_mcp.__version__)"
```

### 3. 启动测试

```bash
# 后续会添加启动脚本
python mcp-server/server.py
```

## 📚 文档索引

- [架构设计](docs/architecture-design.md) - 系统架构详解（待编写）
- [ECC Skills集成](docs/ecc-skills-mapping.md) - Skills调用方案（待编写）
- [快速开始](docs/quick-start.md) - 详细使用指南（待编写）

## 🏗️ 项目结构

```
learning-system/
├── mcp-server/              # MCP服务器
│   ├── src/
│   │   ├── agents/         # 4个Agent实现
│   │   ├── bus/            # Agent通信总线
│   │   ├── tools/          # MCP工具实现
│   │   └── utils/          # 工具函数
│   └── server.py           # 入口
├── data/                   # 数据存储
│   ├── sessions/           # 会话历史
│   ├── projects/           # 项目分析
│   └── knowledge/          # 知识快照
├── docs/                   # 设计文档
├── scripts/                # 工具脚本
└── README.md              # 本文件
```

## 🎯 核心组件

### 4个专业Agent

1. **Session Analyzer** (会话分析)
   - 自动提取会话中的知识点
   - 识别涉及的项目和技术
   
2. **Memory Manager** (知识管理)
   - 保存知识到Memory MCP
   - 生成复习计划
   
3. **Project Tracker** (项目追踪)
   - 分析项目架构
   - 提取面试亮点
   
4. **Tech Explorer** (技术探索)
   - 深度调研新技术
   - 生成学习路径

## 📊 技术栈

| 组件 | 技术 |
|-----|------|
| 协议 | MCP 2026-07-28 |
| 后端 | Python 3.12 + FastAPI |
| 知识存储 | Memory MCP + SQLite |
| LLM | Claude API |
| Skills | ECC (281个) |

## 🔗 依赖项目

- **差旅管理系统** - 作为测试项目
  - 路径: `E:/Desktop/langchain-business-trip-management`
  - 用途: Project Tracker的第一个分析目标

## 📝 开发日志

### 2026-08-01
- ✅ 完成项目架构设计
- ✅ 安装Memory MCP (v0.8.0)
- ✅ 创建项目结构
- ⏳ 编写设计文档中...

## 📜 许可证

MIT License

---

**开发状态**: 🟡 设计阶段  
**开发成本**: $36.25 (截至2026-08-01)
