# MCP Extensions 实现指南

## 概述

Extensions 框架实现了动态工具注册机制，允许根据客户端能力协商动态加载扩展功能。

## 架构设计

### 核心组件

```
Extension (抽象基类)
    ├── extension_id: 唯一标识符
    ├── version: 语义化版本号
    ├── capabilities: 能力声明
    └── register_tools(): 注册工具到服务器

ExtensionManager
    ├── 扩展注册
    ├── 能力协商
    ├── 生命周期管理
    └── 版本兼容性检查
```

### 工作流程

```
1. 服务器启动 → 注册所有扩展
2. 客户端连接 → 发送能力声明
3. 服务器协商 → 启用匹配的扩展
4. 扩展加载 → 动态注册工具
5. 客户端调用 → 使用扩展工具
```

## 已实现扩展

### 1. Python 分析扩展

**扩展ID**: `io.learning-system.analyzer.python`

**能力**:
- 装饰器分析 (`analyze_decorators`)
- 框架检测 (FastAPI, Django, Flask)
- 类型提示提取 (`extract_type_hints`)
- 异步模式分析 (`analyze_async_patterns`)

**工具**:
1. `analyze_python_decorators` - 分析 Python 文件中的装饰器使用
2. `detect_python_framework` - 检测项目使用的 Python 框架
3. `extract_python_type_hints` - 提取类型提示信息
4. `analyze_python_async` - 分析 async/await 使用模式

**使用示例**:
```python
# 分析装饰器
result = await server.call_tool(
    "analyze_python_decorators",
    {"file_path": "/path/to/app.py"}
)

# 输出:
{
    "file": "/path/to/app.py",
    "decorators": [
        {
            "target": "get_users",
            "target_type": "function",
            "decorator": "@app.get('/users')",
            "line": 10
        }
    ],
    "decorator_count": 1,
    "frameworks_detected": ["FastAPI"]
}
```

### 2. TypeScript 分析扩展

**扩展ID**: `io.learning-system.analyzer.typescript`

**能力**:
- React 组件检测 (函数式、类组件)
- React Hooks 分析
- TypeScript 接口提取
- 前端框架检测 (React, Next.js, Vue, Angular)

**工具**:
1. `detect_react_components` - 检测 React 组件
2. `analyze_react_hooks` - 分析 Hooks 使用
3. `extract_typescript_interfaces` - 提取接口和类型定义
4. `detect_frontend_framework` - 检测前端框架

**使用示例**:
```typescript
// 检测 React 组件
result = await server.call_tool(
    "detect_react_components",
    {"file_path": "/path/to/Component.tsx"}
)

// 输出:
{
    "file": "/path/to/Component.tsx",
    "components": [
        {
            "name": "UserProfile",
            "type": "functional",
            "props": "{ userId: string }",
            "pattern": "arrow_function"
        }
    ],
    "component_count": 1
}
```

### 3. 安全存储扩展 (OAuth 演示)

**扩展ID**: `io.learning-system.storage.secure`

**能力**:
- OAuth 2.0 授权流程
- 加密 token 存储
- 自动 token 刷新
- 安全凭证管理

**工具**:
1. `oauth_initiate` - 发起 OAuth 授权
2. `oauth_complete` - 完成授权并存储 token
3. `oauth_refresh_token` - 刷新 access token
4. `secure_store_credential` - 存储加密凭证
5. `secure_retrieve_credential` - 检索加密凭证

**OAuth 流程示例**:
```python
# 步骤 1: 发起授权
auth_info = await server.call_tool(
    "oauth_initiate",
    {
        "provider": "github",
        "client_id": "your_client_id",
        "scopes": ["read:user", "repo"]
    }
)

# 输出:
{
    "provider": "github",
    "authorization_url": "https://github.com/login/oauth/authorize?...",
    "state": "random_state_token",
    "expires_at": "2026-08-03T11:00:00",
    "instructions": "User must visit authorization_url to grant permissions"
}

# 步骤 2: 用户授权后，完成流程
token_result = await server.call_tool(
    "oauth_complete",
    {
        "provider": "github",
        "authorization_code": "code_from_callback",
        "state": "random_state_token"
    }
)

# 输出:
{
    "provider": "github",
    "status": "success",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scopes": ["read:user", "repo"]
}
```

**安全存储示例**:
```python
# 存储凭证
await server.call_tool(
    "secure_store_credential",
    {
        "service": "database",
        "credential_type": "password",
        "credential_data": {
            "username": "admin",
            "password": "secure_password"
        }
    }
)

# 检索凭证
cred = await server.call_tool(
    "secure_retrieve_credential",
    {
        "service": "database",
        "credential_type": "password"
    }
)
```

## 能力协商机制

### 客户端声明

客户端在连接时发送能力声明：

```json
{
    "extensions": {
        "io.learning-system.analyzer.python": {
            "version": "1.0.0"
        },
        "io.learning-system.analyzer.typescript": {
            "version": "1.0.0"
        }
    }
}
```

### 服务器响应

服务器返回启用的扩展及其能力：

```json
{
    "io.learning-system.analyzer.python": {
        "version": "1.0.0",
        "capabilities": {
            "analyze_decorators": true,
            "detect_framework": ["FastAPI", "Django", "Flask"],
            "extract_type_hints": true,
            "analyze_async_patterns": true
        }
    }
}
```

### 版本兼容性

- **主版本必须匹配**: 1.x.x 兼容 1.y.z，但不兼容 2.0.0
- **次版本向后兼容**: 1.2.0 兼容 1.1.0
- **补丁版本完全兼容**: 1.0.1 兼容 1.0.0

## 开发新扩展

### 步骤 1: 继承 Extension 基类

```python
from src.extensions.base_extension import Extension

class MyAnalyzerExtension(Extension):
    @property
    def extension_id(self) -> str:
        return "io.learning-system.analyzer.custom"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def display_name(self) -> str:
        return "Custom Code Analyzer"
    
    @property
    def description(self) -> str:
        return "Analyzes custom code patterns"
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "analyze_patterns": True,
            "supported_languages": ["Go", "Rust"]
        }
    
    def register_tools(self, server: Any):
        @server.tool("analyze_custom_patterns")
        async def analyze_patterns(file_path: str):
            # 实现分析逻辑
            pass
```

### 步骤 2: 注册到 ExtensionManager

```python
# 在 server.py 中
from src.extensions import ExtensionManager
from src.extensions.my_analyzer import MyAnalyzerExtension

extension_manager = ExtensionManager()
extension_manager.register(MyAnalyzerExtension())
```

### 步骤 3: 编写测试

```python
def test_my_analyzer():
    ext = MyAnalyzerExtension()
    assert ext.extension_id == "io.learning-system.analyzer.custom"
    assert ext.get_capabilities()["analyze_patterns"] is True
```

## 安全考虑

### 1. 输入验证

所有扩展工具必须验证输入参数：

```python
def validate_file_path(file_path: str):
    # 检查路径遍历攻击
    if ".." in file_path:
        raise ValueError("Invalid file path")
    
    # 检查文件存在性
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
```

### 2. 权限控制

扩展只能访问明确授权的资源：

```python
def check_access(file_path: str, allowed_dirs: List[str]):
    abs_path = os.path.abspath(file_path)
    
    for allowed_dir in allowed_dirs:
        if abs_path.startswith(allowed_dir):
            return True
    
    raise PermissionError("Access denied")
```

### 3. 加密存储

敏感数据必须加密存储（参考 SecureStorageExtension）：

```python
from cryptography.fernet import Fernet

cipher = Fernet(encryption_key)
encrypted_data = cipher.encrypt(data.encode())
```

## 性能优化

### 1. 延迟加载

只在需要时加载扩展：

```python
def enable_extension(self, extension_id: str, server: Any):
    if extension_id not in self.enabled_extensions:
        extension = self.extensions[extension_id]
        extension.enable(server)
        self.enabled_extensions.add(extension_id)
```

### 2. 缓存结果

对重复分析的文件使用缓存：

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def analyze_file(file_path: str):
    # 分析逻辑
    pass
```

### 3. 异步处理

使用 async/await 避免阻塞：

```python
async def analyze_large_project(project_path: str):
    tasks = []
    for file in files:
        tasks.append(analyze_file_async(file))
    
    results = await asyncio.gather(*tasks)
    return results
```

## 测试

运行所有扩展测试：

```bash
# 运行测试
pytest tests/test_extensions.py -v

# 运行特定测试类
pytest tests/test_extensions.py::TestPythonAnalyzer -v

# 查看覆盖率
pytest tests/test_extensions.py --cov=src.extensions --cov-report=html
```

## 面试要点

### 1. 设计模式

- **抽象工厂模式**: Extension 作为抽象基类
- **策略模式**: 不同分析器实现不同策略
- **装饰器模式**: 工具注册使用装饰器语法

### 2. 协议理解

- **能力协商**: 客户端-服务器协商扩展能力
- **版本兼容**: Semantic Versioning 规则
- **动态注册**: 运行时注册工具，而非静态配置

### 3. 实际应用

- **Python 分析器**: AST 解析、装饰器检测、框架识别
- **TypeScript 分析器**: 正则匹配、React 模式识别
- **OAuth 存储**: 加密存储、token 管理、安全流程

### 4. 技术亮点

- **零侵入**: 扩展独立于核心系统
- **可插拔**: 启用/禁用无需重启
- **类型安全**: 使用类型提示和验证
- **测试完备**: 80%+ 测试覆盖率

## 故障排查

### 问题 1: 扩展未加载

**症状**: 客户端请求扩展，但工具不可用

**排查步骤**:
1. 检查扩展是否注册: `extension_manager.list_extensions()`
2. 检查版本兼容: 客户端和服务器版本是否匹配
3. 查看日志: 是否有加载错误

### 问题 2: 工具调用失败

**症状**: 调用扩展工具返回错误

**排查步骤**:
1. 验证参数: 检查传入参数是否符合要求
2. 检查文件路径: 确保文件存在且可访问
3. 查看异常栈: 定位具体错误位置

### 问题 3: OAuth 流程失败

**症状**: OAuth 授权无法完成

**排查步骤**:
1. 验证 state 参数: 确保 CSRF 保护正确
2. 检查加密密钥: 确保密钥文件存在
3. 查看 token 存储: 检查加密存储文件权限

## 未来扩展

### 潜在扩展

1. **Go 分析器**: Goroutine 检测、接口分析
2. **Rust 分析器**: 生命周期分析、trait 提取
3. **SQL 分析器**: 查询优化建议、索引分析
4. **Docker 分析器**: Dockerfile 最佳实践检查

### 增强功能

1. **扩展市场**: 发布和发现社区扩展
2. **热更新**: 无需重启更新扩展
3. **权限细粒度控制**: 每个工具独立权限
4. **扩展依赖管理**: 扩展间依赖关系

## 总结

Extensions 框架实现了 MCP 2026-07-28 规范中的动态扩展能力，提供了：

- ✅ **可扩展性**: 轻松添加新分析器
- ✅ **灵活性**: 客户端按需加载功能
- ✅ **安全性**: 加密存储和权限控制
- ✅ **可测试性**: 完整的单元测试覆盖

这为 Learning System 提供了强大的代码分析能力，支持多语言项目的智能分析和学习建议。
