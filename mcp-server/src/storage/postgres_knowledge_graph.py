"""
PostgreSQL Knowledge Graph Storage
使用 PostgreSQL + pgvector 实现知识图谱存储
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg
import httpx
from loguru import logger


class PostgresKnowledgeGraph:
    """
    PostgreSQL 知识图谱存储

    特性:
    - 使用 PostgreSQL 持久化存储
    - pgvector 扩展支持向量搜索
    - DeepSeek API 生成 embeddings
    - 支持实体和关系的 CRUD
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "learning_system",
        user: str = "admin",
        password: str = "password",
        deepseek_api_key: Optional[str] = None
    ):
        """
        Args:
            host: PostgreSQL 主机
            port: PostgreSQL 端口
            database: 数据库名
            user: 用户名
            password: 密码
            deepseek_api_key: DeepSeek API Key（用于生成 embeddings）
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

        # DeepSeek API
        self.deepseek_api_key = deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url = "https://api.deepseek.com"
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # 连接池
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """建立数据库连接池"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10
            )
            logger.info(f"PostgreSQL connection pool created: {self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")
        await self.http_client.aclose()

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        observations: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建实体

        Args:
            name: 实体名称
            entity_type: 实体类型
            observations: 观察列表
            metadata: 元数据

        Returns:
            创建的实体
        """
        async with self.pool.acquire() as conn:
            try:
                # 插入实体
                row = await conn.fetchrow("""
                    INSERT INTO entities (name, entity_type, observations, metadata)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (name) DO UPDATE
                    SET observations = EXCLUDED.observations,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id, name, entity_type, observations, metadata, created_at, updated_at
                """, name, entity_type, observations, json.dumps(metadata or {}))

                entity = dict(row)

                # 生成并存储 embedding
                await self._generate_and_store_embedding(entity['id'], name, observations)

                logger.info(f"Created entity: {name} (type: {entity_type})")
                return entity

            except Exception as e:
                logger.error(f"Failed to create entity {name}: {e}")
                raise

    async def get_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取实体

        Args:
            name: 实体名称

        Returns:
            实体信息或 None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, name, entity_type, observations, metadata, created_at, updated_at
                FROM entities
                WHERE name = $1
            """, name)

            if row:
                return dict(row)
            return None

    async def add_observations(self, name: str, new_observations: List[str]) -> Dict[str, Any]:
        """
        添加观察到现有实体

        Args:
            name: 实体名称
            new_observations: 新观察列表

        Returns:
            更新后的实体
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE entities
                SET observations = array_cat(observations, $2::text[]),
                    updated_at = CURRENT_TIMESTAMP
                WHERE name = $1
                RETURNING id, name, entity_type, observations, metadata, created_at, updated_at
            """, name, new_observations)

            if row:
                entity = dict(row)
                # 更新 embedding
                await self._generate_and_store_embedding(entity['id'], name, entity['observations'])
                logger.info(f"Added {len(new_observations)} observations to {name}")
                return entity
            else:
                raise ValueError(f"Entity '{name}' not found")

    async def create_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建关系

        Args:
            from_entity: 源实体
            to_entity: 目标实体
            relation_type: 关系类型
            metadata: 元数据

        Returns:
            创建的关系
        """
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow("""
                    INSERT INTO relations (from_entity, to_entity, relation_type, metadata)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (from_entity, to_entity, relation_type) DO UPDATE
                    SET metadata = EXCLUDED.metadata
                    RETURNING id, from_entity, to_entity, relation_type, metadata, created_at
                """, from_entity, to_entity, relation_type, json.dumps(metadata or {}))

                logger.info(f"Created relation: {from_entity} --[{relation_type}]--> {to_entity}")
                return dict(row)

            except Exception as e:
                logger.error(f"Failed to create relation: {e}")
                raise

    async def search_entities(
        self,
        query: str,
        limit: int = 10,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        语义搜索实体

        Args:
            query: 查询文本
            limit: 返回结果数量
            entity_type: 过滤实体类型

        Returns:
            匹配的实体列表（按相似度排序）
        """
        # 生成查询向量
        query_embedding = await self._generate_embedding(query)
        if not query_embedding:
            logger.warning("Failed to generate query embedding, falling back to text search")
            return await self._text_search(query, limit, entity_type)

        async with self.pool.acquire() as conn:
            # 向量搜索
            if entity_type:
                rows = await conn.fetch("""
                    SELECT e.id, e.name, e.entity_type, e.observations, e.metadata,
                           1 - (emb.embedding <=> $1::vector) as similarity
                    FROM entities e
                    JOIN entity_embeddings emb ON e.id = emb.entity_id
                    WHERE e.entity_type = $2
                    ORDER BY emb.embedding <=> $1::vector
                    LIMIT $3
                """, query_embedding, entity_type, limit)
            else:
                rows = await conn.fetch("""
                    SELECT e.id, e.name, e.entity_type, e.observations, e.metadata,
                           1 - (emb.embedding <=> $1::vector) as similarity
                    FROM entities e
                    JOIN entity_embeddings emb ON e.id = emb.entity_id
                    ORDER BY emb.embedding <=> $1::vector
                    LIMIT $2
                """, query_embedding, limit)

            return [dict(row) for row in rows]

    async def _text_search(
        self,
        query: str,
        limit: int = 10,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        文本搜索（fallback）

        使用 LIKE 进行简单的文本匹配
        """
        async with self.pool.acquire() as conn:
            query_pattern = f"%{query}%"

            if entity_type:
                rows = await conn.fetch("""
                    SELECT id, name, entity_type, observations, metadata
                    FROM entities
                    WHERE entity_type = $1 AND (name ILIKE $2 OR $2 = ANY(observations))
                    LIMIT $3
                """, entity_type, query_pattern, limit)
            else:
                rows = await conn.fetch("""
                    SELECT id, name, entity_type, observations, metadata
                    FROM entities
                    WHERE name ILIKE $1 OR $1 = ANY(observations)
                    LIMIT $2
                """, query_pattern, limit)

            return [dict(row) for row in rows]

    async def get_relations(
        self,
        entity_name: str,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        获取实体的关系

        Args:
            entity_name: 实体名称
            direction: 方向 ("outgoing", "incoming", "both")

        Returns:
            关系列表
        """
        async with self.pool.acquire() as conn:
            if direction == "outgoing":
                rows = await conn.fetch("""
                    SELECT id, from_entity, to_entity, relation_type, metadata, created_at
                    FROM relations
                    WHERE from_entity = $1
                """, entity_name)
            elif direction == "incoming":
                rows = await conn.fetch("""
                    SELECT id, from_entity, to_entity, relation_type, metadata, created_at
                    FROM relations
                    WHERE to_entity = $1
                """, entity_name)
            else:  # both
                rows = await conn.fetch("""
                    SELECT id, from_entity, to_entity, relation_type, metadata, created_at
                    FROM relations
                    WHERE from_entity = $1 OR to_entity = $1
                """, entity_name)

            return [dict(row) for row in rows]

    async def get_all_entities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有实体"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, entity_type, observations, metadata, created_at, updated_at
                FROM entities
                ORDER BY updated_at DESC
                LIMIT $1
            """, limit)

            return [dict(row) for row in rows]

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        使用 DeepSeek API 生成文本向量

        Args:
            text: 输入文本

        Returns:
            1536 维向量或 None
        """
        if not self.deepseek_api_key:
            logger.warning("DeepSeek API key not configured")
            return None

        try:
            response = await self.http_client.post(
                f"{self.deepseek_base_url}/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "input": text
                }
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def _generate_and_store_embedding(
        self,
        entity_id: int,
        name: str,
        observations: List[str]
    ):
        """
        生成并存储实体的 embedding

        Args:
            entity_id: 实体 ID
            name: 实体名称
            observations: 观察列表
        """
        # 合并名称和观察作为嵌入文本
        text = f"{name}. " + " ".join(observations)
        embedding = await self._generate_embedding(text)

        if not embedding:
            logger.warning(f"Skipping embedding storage for entity {entity_id}")
            return

        async with self.pool.acquire() as conn:
            # 删除旧的 embedding
            await conn.execute("""
                DELETE FROM entity_embeddings WHERE entity_id = $1
            """, entity_id)

            # 插入新的 embedding
            await conn.execute("""
                INSERT INTO entity_embeddings (entity_id, embedding)
                VALUES ($1, $2::vector)
            """, entity_id, embedding)

            logger.debug(f"Stored embedding for entity {entity_id}")
