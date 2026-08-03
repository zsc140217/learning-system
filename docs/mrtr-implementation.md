# MRTR 实现文档

## 概述

MRTR (Multi-Round Trip Request) 是 MCP 2026-07-28 协议的核心安全特性，用于危险操作的二次确认机制。

## 实现原理

### 工作流程

```
用户发起操作
    ↓
服务器生成 JWT token
    ↓
返回确认请求 (第一轮)
    ↓
用户确认
    ↓
携带 JWT token 再次请求
    ↓
服务器验证 JWT + Nonce
    ↓
执行操作 (第二轮)
```

### 安全机制

#### 1. JWT 签名验证
- 使用 HS256 算法对 JWT 进行签名
- 防止 token 被篡改
- 密钥通过环境变量 `JWT_SECRET` 配置

#### 2. Nonce 防重放攻击
- 每个 token 包含唯一的 nonce 值
- 已使用的 nonce 记录在内存中
- 自动清理过期的 nonce（10分钟后）

#### 3. Token 过期时间
- 默认 5 分钟有效期
- 超时后需要重新发起请求

#### 4. 参数一致性验证
- 第一轮和第二轮的参数必须完全一致
- 防止中间人攻击修改参数

---

## 文件结构

```
mcp-server/
├── src/
│   └── security/
│       ├── __init__.py           # 模块导出
│       ├── nonce_store.py        # Nonce 存储和管理
│       └── jwt_handler.py        # JWT 生成和验证
tests/
└── test_mrtr.py                  # MRTR 测试套件
```

---

## 核心组件

### 1. NonceStore

**职责**: 管理已使用的 nonce，防止重放攻击

**关键方法**:
```python
class NonceStore:
    def is_used(self, nonce: str) -> bool:
        """检查 nonce 是否已使用"""
        
    def mark_used(self, nonce: str, expiry_minutes: int = 10):
        """标记 nonce 为已使用"""
        
    async def _cleanup_expired(self):
        """清理过期的 nonce"""
```

**特性**:
- 内存存储（不持久化）
- 后台异步清理（默认每60秒）
- 自动过期（默认10分钟）

---

### 2. JWTHandler

**职责**: 生成和验证 JWT token

**关键方法**:
```python
class JWTHandler:
    def generate_request_state(
        self,
        operation: str,
        params: Dict[str, Any],
        expiry_minutes: int = 5
    ) -> str:
        """生成 JWT token（第一轮）"""
        
    def verify_request_state(self, token: str) -> Dict[str, Any]:
        """验证 JWT token（第二轮）"""
        
    def verify_params_match(
        self,
        payload: Dict[str, Any],
        current_params: Dict[str, Any]
    ) -> bool:
        """验证参数一致性"""
```

**JWT Payload 结构**:
```json
{
  "operation": "delete_knowledge",
  "params": {
    "knowledge_ids": ["k-001", "k-002"]
  },
  "exp": 1722691500,
  "iat": 1722691200,
  "nonce": "a1b2c3d4e5f6789"
}
```

---

## 危险操作工具

### 1. delete_knowledge

**用途**: 删除知识节点

**第一轮请求**:
```python
await delete_knowledge(knowledge_ids=["k-001", "k-002"])
```

**第一轮响应**:
```json
{
  "data": {
    "message": "⚠️ 将删除 2 个知识节点，此操作不可逆",
    "knowledge_ids": ["k-001", "k-002"],
    "requires_confirmation": true
  },
  "_meta": {
    "io.modelcontextprotocol/inputRequired": {
      "requestState": "eyJhbGc...",
      "fields": [
        {
          "name": "confirm",
          "type": "boolean",
          "label": "确认删除",
          "required": true
        }
      ]
    }
  }
}
```

**第二轮请求**:
```python
await delete_knowledge(
    knowledge_ids=["k-001", "k-002"],
    request_state="eyJhbGc..."
)
```

**第二轮响应**:
```json
{
  "data": {
    "deleted_count": 2,
    "status": "completed",
    "message": "成功删除 2 个知识节点"
  }
}
```

---

### 2. delete_project

**用途**: 删除项目及其所有关联数据

**参数**:
- `project_id`: 项目ID
- `request_state`: JWT token（第二轮提供）

**流程**: 与 `delete_knowledge` 类似

---

### 3. rebuild_index

**用途**: 重建索引

**参数**:
- `index_type`: 索引类型（all/knowledge/sessions）
- `request_state`: JWT token（第二轮提供）

**流程**: 与 `delete_knowledge` 类似

---

## 安全威胁与防护

### 1. 重放攻击 (Replay Attack)

**威胁**: 攻击者截获 JWT token，多次重复使用

**防护**: Nonce 机制
```python
# 验证时检查 nonce
if nonce_store.is_used(payload["nonce"]):
    raise SecurityError("Nonce already used (replay attack detected)")

# 标记为已使用
nonce_store.mark_used(payload["nonce"])
```

---

### 2. Token 篡改

**威胁**: 攻击者修改 JWT 内容（如修改参数）

**防护**: JWT 签名验证
```python
# JWT 使用密钥签名
token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")

# 验证时会检查签名
payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
# 如果签名不匹配，会抛出 InvalidTokenError
```

---

### 3. 参数替换攻击

**威胁**: 第一轮请求删除 A，第二轮偷偷替换为删除 B

**防护**: 参数一致性验证
```python
# 验证参数必须完全一致
if payload["params"] != current_params:
    raise SecurityError("Parameters mismatch")
```

---

### 4. Token 过期

**威胁**: 长时间未使用的 token 被盗用

**防护**: 5分钟有效期
```python
payload = {
    "exp": datetime.utcnow() + timedelta(minutes=5),  # 5分钟后过期
    # ...
}
```

---

## 测试覆盖

### 测试类别

#### 1. NonceStore 测试
- ✅ Nonce 标记和检查
- ✅ Nonce 自动过期
- ✅ 存储统计信息

#### 2. JWTHandler 测试
- ✅ Token 生成
- ✅ Token 验证成功
- ✅ 重放攻击防护
- ✅ 过期 Token 拒绝
- ✅ 无效 Token 拒绝
- ✅ 篡改 Token 拒绝
- ✅ 参数匹配验证
- ✅ 参数篡改检测

#### 3. MRTR 流程测试
- ✅ 完整的两轮流程
- ✅ 参数替换攻击防护
- ✅ Token 超时处理

### 运行测试

```bash
# 运行所有 MRTR 测试
cd learning-system
python -m pytest tests/test_mrtr.py -v

# 运行特定测试
python -m pytest tests/test_mrtr.py::TestJWTHandler::test_verify_request_state_replay_attack -v

# 查看覆盖率
python -m pytest tests/test_mrtr.py --cov=src.security --cov-report=html
```

---

## 部署配置

### 环境变量

```bash
# .env 文件
JWT_SECRET=your_production_secret_key_here_change_me_123456789
```

⚠️ **重要**: 生产环境必须配置强密钥
- 长度至少 32 字符
- 包含大小写字母、数字、特殊字符
- 定期轮换（建议每90天）

### 启动验证

```bash
# 启动服务器
cd mcp-server
python server.py

# 检查日志
# 应该看到：
# ✅ NonceStore 已启动
# ✅ JWTHandler 已初始化
```

---

## 面试要点

### 1. 为什么选择 JWT？

**回答**:
> "JWT 是无状态的，服务器不需要存储 session。所有信息都编码在 token 中，通过签名保证完整性。这使得系统易于水平扩展，任何服务器都能验证 token，无需共享 session 存储。"

### 2. 如何防止重放攻击？

**回答**:
> "我实现了 Nonce（Number Once）机制。每个 token 包含唯一的 nonce，验证后立即标记为已使用。如果相同的 token 再次出现，系统会拒绝并记录为潜在的重放攻击。Nonce 会在10分钟后自动清理，避免内存无限增长。"

### 3. 5分钟过期时间是如何确定的？

**回答**:
> "这是在安全性和用户体验之间的平衡：
> - 太短（如1分钟）：用户可能来不及确认就过期
> - 太长（如30分钟）：被盗 token 的风险窗口增大
> - 5分钟：足够用户阅读确认信息并做出决定，同时限制了攻击窗口"

### 4. 如果服务器重启，未过期的 token 会怎样？

**回答**:
> "当前实现中，JWT 密钥在启动时生成（如果未配置），所以重启后所有旧 token 都会失效。生产环境应该配置固定的 JWT_SECRET，这样重启不影响未过期的 token。但 nonce 存储在内存中，重启后会丢失，导致已用过的 token 可以再次使用（理论风险）。解决方案是将 nonce 持久化到 Redis 或数据库。"

### 5. 这个实现的局限性是什么？

**回答**:
> "主要局限性：
> 1. Nonce 存储在内存，不支持分布式部署
> 2. 无法撤销已发出的 token（除非等待过期）
> 3. 参数验证是严格相等，不支持部分参数修改
> 
> 改进方向：
> 1. 使用 Redis 存储 nonce
> 2. 实现 token 黑名单机制
> 3. 支持参数白名单模式（允许修改特定字段）"

---

## Phase 1 完成情况

```
┌────────┬─────────────────────────────┬─────────────┐
│  Task  │            内容             │    状态     │
├────────┼─────────────────────────────┼─────────────┤
│ 1.1    │ JWT 基础设施                │ ✅ 已完成   │
│ 1.2    │ 危险操作二次确认            │ ✅ 已完成   │
│ 1.3    │ MRTR 测试                   │ ✅ 已完成   │
│ 1.4    │ 安全文档                    │ ✅ 已完成   │
│ 1.5    │ MCP Memory 知识图谱集成      │ ✅ 已完成   │
│ 1.6    │ 空闲触发系统                 │ ✅ 已完成   │
│ 1.7    │ 端到端测试                   │ ✅ 已完成   │
└────────┴─────────────────────────────┴─────────────┘
```

**Phase 1 完成度**: 100% ✅

---

**文档版本**: v1.0  
**更新日期**: 2026-08-03  
**作者**: Learning System Team
