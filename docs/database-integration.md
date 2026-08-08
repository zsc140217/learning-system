# 生产级数据库集成方案

> 面试要点：三层存储架构、PostgreSQL+pgvector、Redis缓存、MCP协议集成

## 1. 架构概览

### 1.1 存储层架构

```
Application Layer (MemoryManager Agent)
          |
  Repository Factory
          |
    +-----+-----+
    |     |     |
 Postgres Redis MCP
 Primary  Cache Demo
```

### 1.2 存储优先级

1. **PostgreSQL (生产推荐)** - 持久化存储、支持复杂查询、pgvector扩展支持向量搜索
2. **Redis (缓存层)** - 热数据缓存、搜索结果缓存、TTL自动过期
3. **Memory MCP (演示用)** - MCP协议集成演示、知识图谱可视化、降级方案

## 2. 技术选型理由

### 2.1 为什么用 PostgreSQL？

**面试回答要点：**
- ACID事务保证数据一致性
- pgvector扩展支持向量搜索（语义搜索找相似知识点）
- HNSW索引：百万级向量毫秒级查询
- 递归查询（WITH RECURSIVE）适合知识图谱
- asyncpg：高性能异步驱动

### 2.2 为什么用 Redis？

**面试回答要点：**
- 内存存储，读写 < 1ms
- 减少数据库压力
- 支持持久化（AOF）
- 主从复制、Sentinel高可用

### 2.3 为什么集成 Memory MCP？

**面试回答要点：**
- 展示 2026 MCP 新特性
- 知识图谱可视化
- 降级方案展示系统容错设计

## 3. 数据库设计

### 3.1 核心表结构

#### knowledge_points (知识点表)

```sql
CREATE TABLE knowledge_points (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    tags TEXT[],
    difficulty FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.5,
    source VARCHAR(100),
    session_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    embedding vector(768),

    CONSTRAINT check_difficulty CHECK (difficulty BETWEEN 0 AND 1),
    CONSTRAINT check_confidence CHECK (confidence BETWEEN 0 AND 1)
);
```

**设计要点：**
- embedding: 768维向量（OpenAI text-embedding-3-small标准维度）
- tags: PostgreSQL数组类型，支持GIN索引
- difficulty/confidence: 约束确保值在[0,1]区间

#### knowledge_relations (关系表)

```sql
CREATE TABLE knowledge_relations (
    id SERIAL PRIMARY KEY,
    from_node VARCHAR(50) NOT NULL,
    to_node VARCHAR(50) NOT NULL,
    relation_type VARCHAR(50) NOT NULL,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (from_node) REFERENCES knowledge_points(id) ON DELETE CASCADE,
    FOREIGN KEY (to_node) REFERENCES knowledge_points(id) ON DELETE CASCADE,
    UNIQUE(from_node, to_node, relation_type)
);
```

### 3.2 索引策略

```sql
-- 向量搜索索引（HNSW算法）
CREATE INDEX idx_knowledge_embedding ON knowledge_points
USING hnsw (embedding vector_cosine_ops);

-- 标签GIN索引（支持数组查询）
CREATE INDEX idx_knowledge_tags ON knowledge_points USING GIN(tags);

-- 常规查询索引
CREATE INDEX idx_knowledge_session ON knowledge_points(session_id);
CREATE INDEX idx_knowledge_category ON knowledge_points(category);
```

**面试要点：**
- HNSW: Hierarchical Navigable Small World，向量搜索最快算法
- GIN: Generalized Inverted Index，适合数组/JSONB查询

## 4. 代码实现

### 4.1 PostgreSQL Repository

```python
class PostgresKnowledgeRepository:
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool

    @classmethod
    async def create(cls, database_url: str, min_size: int = 10, max_size: int = 20):
        pool = await asyncpg.create_pool(
            database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60
        )
        return cls(pool)

    async def save_knowledge_points(self, knowledge_points: List[Dict]) -> List[str]:
        saved_ids = []
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for kp in knowledge_points:
                    await conn.execute("""
                        INSERT INTO knowledge_points (...)
                        VALUES (...)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            updated_at = NOW()
                    """, ...)
                    saved_ids.append(kp["id"])
        return saved_ids
```

**设计要点：**
- 连接池复用：避免频繁创建连接
- 事务保证：批量操作原子性
- UPSERT: ON CONFLICT DO UPDATE 幂等操作

### 4.2 Redis Cache

```python
class RedisCache:
    async def cache_knowledge(self, knowledge_id: str, data: Dict, ttl: timedelta = None) -> bool:
        key = f"knowledge:{knowledge_id}"
        return await self.set(key, data, ttl or timedelta(hours=1))

    async def cache_search_result(self, query: str, results: List, ttl: timedelta = None) -> bool:
        key = f"search:{query}"
        return await self.set(key, results, ttl or timedelta(minutes=10))
```

**缓存策略：**
- 知识点：1小时（变化不频繁）
- 搜索结果：10分钟（可能有新内容）
- 图谱：30分钟（计算成本高）

## 5. 部署和运维

### 5.1 Docker Compose 部署

```bash
# 启动数据库
cd mcp-server
docker compose up -d

# 查看状态
docker compose ps
```

### 5.2 备份和恢复

```bash
# 备份
docker exec -t learning-system-db pg_dump -U learning_user learning_system > backup.sql

# 恢复
cat backup.sql | docker exec -i learning-system-db psql -U learning_user -d learning_system
```

## 6. 性能优化

### 6.1 连接池配置

```python
postgres_config = {
    "pool_min_size": 10,   # 保持热连接
    "pool_max_size": 20,   # 限制并发
    "command_timeout": 60  # 防止慢查询
}
```

### 6.2 缓存命中率优化

```python
async def warmup_cache(self, knowledge_points: List[Dict]) -> int:
    warmed_count = 0
    for kp in knowledge_points:
        success = await self.cache_knowledge(kp["id"], kp)
        if success:
            warmed_count += 1
    return warmed_count
```

## 7. 面试准备要点

### 7.1 架构设计问题

**Q: 为什么选择三层存储架构？**

A: 
- PostgreSQL主存储：持久化、事务、复杂查询
- Redis缓存层：性能优化、减少数据库压力
- Memory MCP：MCP协议演示、降级方案

### 7.2 技术细节问题

**Q: pgvector是什么？如何使用？**

A:
- PostgreSQL向量扩展，支持向量搜索
- 存储embedding（如768维）
- HNSW索引：近似最近邻搜索
- 用于语义搜索：找相似知识点

**Q: 如何保证缓存一致性？**

A:
- 写穿透：写数据库同时更新缓存
- TTL过期：设置合理过期时间
- 主动失效：更新/删除时清除缓存

### 7.3 系统设计问题

**Q: 如何处理故障降级？**

```python
async def save_knowledge(self, data):
    # 1. 尝试PostgreSQL
    if self.postgres_repo:
        try:
            return await self.postgres_repo.save(data)
        except Exception:
            logger.error("PostgreSQL失败，尝试MCP")
    
    # 2. 回退到Memory MCP
    if self.mcp_adapter.available:
        try:
            return await self.mcp_adapter.save(data)
        except Exception:
            logger.error("MCP失败，使用fallback")
    
    # 3. 最终回退到内存
    return self._save_to_memory(data)
```

## 8. 项目亮点总结

1. **三层存储架构** - PostgreSQL + Redis + Memory MCP
2. **向量搜索支持** - pgvector扩展 + HNSW索引
3. **MCP协议集成** - 2026新特性演示
4. **生产级设计** - 连接池、事务、健康检查
5. **完善的测试** - 单元测试、集成测试

---

文档版本: 1.0  
最后更新: 2026-08-05
