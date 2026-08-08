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

        # DeepSeek API - 优先从配置文件读取
        if not deepseek_api_key:
            try:
                from config import settings
                deepseek_api_key = settings.deepseek_api_key
            except ImportError:
                deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

        self.deepseek_api_key = deepseek_api_key
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
        metadata: Optional[Dict] = None,
        graph_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        创建实体

        Args:
            name: 实体名称
            entity_type: 实体类型
            observations: 观察列表
            metadata: 元数据
            graph_id: 所属图谱ID（可选，如果不指定则使用默认图谱）

        Returns:
            创建的实体
        """
        async with self.pool.acquire() as conn:
            try:
                # 插入实体
                row = await conn.fetchrow("""
                    INSERT INTO entities (name, entity_type, observations, metadata, graph_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (name) DO UPDATE
                    SET observations = EXCLUDED.observations,
                        metadata = EXCLUDED.metadata,
                        graph_id = EXCLUDED.graph_id,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id, name, entity_type, observations, metadata, graph_id, created_at, updated_at
                """, name, entity_type, observations, json.dumps(metadata or {}), graph_id)

                entity = dict(row)

                # 生成并存储 embedding
                await self._generate_and_store_embedding(entity['id'], name, observations)

                # 更新图谱节点计数
                if graph_id:
                    await self.update_graph_node_count(graph_id)

                logger.info(f"Created entity: {name} (type: {entity_type}, graph_id: {graph_id})")
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

    # ========== 知识图谱管理方法 ==========

    async def create_graph(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        创建新图谱

        Args:
            name: 图谱名称
            description: 图谱描述

        Returns:
            创建的图谱信息 {id, name, description, created_at, node_count}
        """
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow("""
                    INSERT INTO knowledge_graphs (name, description, node_count)
                    VALUES ($1, $2, 0)
                    RETURNING id, name, description, created_at, updated_at, node_count
                """, name, description)

                graph = dict(row)
                logger.info(f"Created knowledge graph: {name} (id: {graph['id']})")
                return graph

            except Exception as e:
                logger.error(f"Failed to create knowledge graph {name}: {e}")
                raise

    async def list_graphs(self) -> List[Dict[str, Any]]:
        """
        列出所有图谱

        Returns:
            图谱列表 [{id, name, description, node_count, created_at}, ...]
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, description, node_count, created_at, updated_at
                FROM knowledge_graphs
                ORDER BY created_at DESC
            """)

            graphs = [dict(row) for row in rows]
            logger.debug(f"Listed {len(graphs)} knowledge graphs")
            return graphs

    async def get_graph(self, graph_id: int) -> Optional[Dict[str, Any]]:
        """
        获取图谱信息

        Args:
            graph_id: 图谱ID

        Returns:
            图谱信息或 None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, name, description, node_count, created_at, updated_at
                FROM knowledge_graphs
                WHERE id = $1
            """, graph_id)

            if row:
                return dict(row)
            return None

    async def delete_graph(self, graph_id: int) -> bool:
        """
        删除图谱（CASCADE 自动删除节点和关系）

        Args:
            graph_id: 图谱ID

        Returns:
            是否删除成功
        """
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute("""
                    DELETE FROM knowledge_graphs WHERE id = $1
                """, graph_id)

                # result 格式: "DELETE N" 其中 N 是删除的行数
                deleted_count = int(result.split()[-1])
                success = deleted_count > 0

                if success:
                    logger.info(f"Deleted knowledge graph {graph_id}")
                else:
                    logger.warning(f"Knowledge graph {graph_id} not found")

                return success

            except Exception as e:
                logger.error(f"Failed to delete knowledge graph {graph_id}: {e}")
                raise

    async def merge_graphs(self, source_ids: List[int], target_name: str, target_description: str = "") -> Dict[str, Any]:
        """
        合并多个图谱到新图谱

        步骤：
        1. 创建新图谱
        2. 更新所有源图谱的节点，设置 graph_id = 新图谱ID
        3. 更新新图谱的节点计数
        4. 删除源图谱

        Args:
            source_ids: 源图谱ID列表
            target_name: 目标图谱名称
            target_description: 目标图谱描述

        Returns:
            新图谱信息
        """
        async with self.pool.acquire() as conn:
            try:
                async with conn.transaction():
                    # 1. 创建新图谱
                    new_graph = await conn.fetchrow("""
                        INSERT INTO knowledge_graphs (name, description, node_count)
                        VALUES ($1, $2, 0)
                        RETURNING id, name, description, created_at, updated_at, node_count
                    """, target_name, target_description)

                    new_graph_id = new_graph['id']

                    # 2. 迁移节点
                    await conn.execute("""
                        UPDATE entities
                        SET graph_id = $1
                        WHERE graph_id = ANY($2::int[])
                    """, new_graph_id, source_ids)

                    # 3. 更新节点计数
                    updated_graph = await conn.fetchrow("""
                        UPDATE knowledge_graphs
                        SET node_count = (SELECT COUNT(*) FROM entities WHERE graph_id = $1)
                        WHERE id = $1
                        RETURNING id, name, description, created_at, updated_at, node_count
                    """, new_graph_id)

                    # 4. 删除源图谱
                    await conn.execute("""
                        DELETE FROM knowledge_graphs WHERE id = ANY($1::int[])
                    """, source_ids)

                    logger.info(f"Merged graphs {source_ids} into new graph {new_graph_id} ({target_name})")
                    return dict(updated_graph)

            except Exception as e:
                logger.error(f"Failed to merge graphs {source_ids}: {e}")
                raise

    async def get_graph_data(self, graph_id: int) -> Dict[str, Any]:
        """
        获取指定图谱的所有节点和边，用于可视化

        Args:
            graph_id: 图谱ID

        Returns:
            {nodes: [...], edges: [...]}
        """
        async with self.pool.acquire() as conn:
            # 获取节点
            entity_rows = await conn.fetch("""
                SELECT id, name, entity_type, observations, metadata
                FROM entities
                WHERE graph_id = $1
            """, graph_id)

            nodes = []
            for row in entity_rows:
                nodes.append({
                    "id": row['name'],  # 使用 name 作为节点 ID
                    "label": row['name'],
                    "type": row['entity_type'],
                    "observations": row['observations'],
                    "metadata": row['metadata']
                })

            # 获取边
            relation_rows = await conn.fetch("""
                SELECT r.from_entity, r.to_entity, r.relation_type, r.metadata
                FROM relations r
                JOIN entities e1 ON r.from_entity = e1.name
                WHERE e1.graph_id = $1
            """, graph_id)

            edges = []
            for row in relation_rows:
                edges.append({
                    "source": row['from_entity'],
                    "target": row['to_entity'],
                    "type": row['relation_type'],
                    "metadata": row['metadata']
                })

            logger.debug(f"Retrieved graph data: {len(nodes)} nodes, {len(edges)} edges")
            return {
                "nodes": nodes,
                "edges": edges
            }

    async def update_graph_node_count(self, graph_id: int):
        """
        更新图谱的节点计数（在添加/删除节点后调用）

        Args:
            graph_id: 图谱ID
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE knowledge_graphs
                SET node_count = (SELECT COUNT(*) FROM entities WHERE graph_id = $1),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """, graph_id)
