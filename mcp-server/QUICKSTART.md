# Learning System - 快速启动指南

## 项目状态

✅ **Phase 4.2 完成** - Memory MCP Server 集成测试通过  
✅ **Windows 中文乱码修复** - UTF-8 日志配置完成  
✅ **依赖管理** - requirements.txt 已生成  
✅ **一键安装** - install.bat 脚本已创建  

---

## 快速安装（Windows）

### 方法 1：一键安装（推荐）

双击运行 `install.bat`，脚本会自动：
- 检查 Python 版本
- 创建虚拟环境
- 安装所有依赖
- 配置项目目录

### 方法 2：手动安装

```cmd
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
venv\Scripts\activate.bat

# 3. 升级 pip
python -m pip install --upgrade pip

# 4. 安装依赖
pip install -r requirements.txt

# 5. 设置终端编码为 UTF-8
chcp 65001
```

---

## 配置

### 1. API 密钥配置

编辑 `config/config.yaml`：

```yaml
llm:
  provider: deepseek
  
  deepseek:
    api_key: sk-your-api-key-here  # 替换为你的 DeepSeek API Key
    model: deepseek-chat
    base_url: https://api.deepseek.com
    temperature: 0.7
    max_tokens: 1000
```

### 2. Memory MCP 配置

```yaml
mcp:
  memory:
    enabled: true
    url: http://localhost:3000
    timeout: 10
```

---

## 验证安装

### 1. 测试日志配置（修复中文乱码）

```cmd
python -c "import sys; sys.path.insert(0, 'mcp-server'); from src.utils.logging import setup_logging; from loguru import logger; setup_logging(); logger.info('中文测试成功')"
```

**预期输出：**
```
2026-08-02 22:49:37.188 | INFO     | Logging configured: level=INFO, encoding=UTF-8
2026-08-02 22:49:37.188 | INFO     | 中文测试成功
```

### 2. 测试 Memory MCP 集成

```cmd
python test_memory_integration.py
```

**预期输出：**
```
============================================================
All Tests Passed!
============================================================

Memory MCP integration is ready.
```

### 3. 测试 DeepSeek LLM Provider

```cmd
python test_deepseek.py
```

---

## 项目结构

```
learning-system/
├── mcp-server/              # MCP 服务器代码
│   ├── src/
│   │   ├── agents/          # Multi-Agent 系统
│   │   │   ├── base_agent.py
│   │   │   ├── memory_manager.py
│   │   │   ├── interview_agent.py
│   │   │   └── project_agent.py
│   │   ├── bus/             # 事件总线
│   │   │   └── agent_bus.py
│   │   ├── llm/             # LLM Provider 抽象层
│   │   │   ├── base_provider.py
│   │   │   ├── deepseek_provider.py
│   │   │   ├── openai_provider.py
│   │   │   └── factory.py
│   │   └── utils/           # 工具类
│   │       ├── logging.py   # UTF-8 日志配置
│   │       └── id_generator.py
│   ├── config.py            # 配置管理
│   └── server.py            # MCP 服务器入口
│
├── config/                  # 配置文件
│   └── config.yaml
│
├── tests/                   # 单元测试
├── test_*.py               # 集成测试
├── requirements.txt         # Python 依赖
├── install.bat             # Windows 安装脚本
└── QUICKSTART.md           # 本文件
```

---

## 核心功能

### 1. Multi-Agent 系统

- **AgentBus** - 事件驱动的 Agent 通信总线
- **MemoryManager** - 知识图谱管理
- **InterviewAgent** - 面试问题生成
- **ProjectAgent** - 项目分析

### 2. LLM Provider 抽象层

支持多种 LLM Provider：
- DeepSeek（OpenAI-compatible）
- OpenAI
- Anthropic

**使用示例：**

```python
from src.llm import LLMProviderFactory

# 创建 DeepSeek Provider
provider = LLMProviderFactory.create('deepseek', {
    'api_key': 'sk-xxx',
    'model': 'deepseek-chat'
})

# 调用 LLM
response = await provider.chat([
    {'role': 'user', 'content': '你好'}
])
```

### 3. Memory MCP Integration

- **知识图谱存储** - 使用 Memory MCP Server
- **Fallback 模式** - MCP 不可用时自动降级
- **事件驱动保存** - 自动监听知识提取事件

**知识图谱结构：**

```
[Project] learning-system
    ├── uses ──────────> [Technology] FastAPI
    ├── implements ────> [Technology] MCP Protocol
    └── integrates ───> [LLM Provider] DeepSeek
```

---

## 常见问题

### Q1: 日志仍然显示乱码？

**解决方案：**

```python
# 在任何使用 loguru 的文件开头导入
from src.utils.logging import setup_logging
setup_logging(level='INFO')
```

### Q2: ModuleNotFoundError: No module named 'src'

**解决方案：**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))
```

### Q3: DeepSeek API 调用失败

**检查：**
1. API Key 是否正确配置在 `config/config.yaml`
2. 网络连接是否正常
3. API 配额是否充足

---

## 下一步

### Phase 4.3 - 生产环境优化（待完成）

- [ ] LLM 调用日志增强（token、成本、时间）
- [ ] 请求速率限制（60 req/min）
- [ ] LLM 响应缓存
- [ ] 错误重试策略（指数退避）

### Phase 5 - End-to-End 集成测试（待完成）

- [ ] 完整工作流测试
- [ ] ProjectAgent + Memory 集成
- [ ] Windows 终端优化

### Phase 6 - 知识图谱可视化（待完成）

- [ ] D3.js/Cytoscape.js 可视化
- [ ] MCP App 界面
- [ ] 交互式图谱浏览

---

## 面试准备要点

### 1. 架构设计亮点

**事件驱动架构（EDA）**
- 解耦 Agent 之间的依赖
- 支持动态扩展订阅者
- 异步处理提高性能

**MCP 协议集成**
- 标准化工具调用接口
- 支持多个 MCP Server 组合
- Fallback 模式保证可用性

**LLM Provider 抽象层**
- 工厂模式创建 Provider
- 统一接口屏蔽差异
- 轻松切换 LLM 提供商

### 2. 技术栈选择理由

- **FastMCP** - MCP 2026-07-28 标准实现
- **Loguru** - 结构化日志 + UTF-8 支持
- **Pydantic** - 类型安全的配置管理
- **DeepSeek** - 成本效益最优的 LLM

### 3. 问题解决能力

- **Windows 编码问题** - sys.stderr.reconfigure(encoding='utf-8')
- **MCP 可用性** - Fallback 模式优雅降级
- **异步并发** - asyncio + 事件总线

---

## 联系信息

项目仓库：E:\Desktop\learning-system  
最新提交：9d373d2 - Phase 4.2 完成  
当前分支：master  

---

**生成时间：** 2026-08-02 22:50  
**文档版本：** 1.0
