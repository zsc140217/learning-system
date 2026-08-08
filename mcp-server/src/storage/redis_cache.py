"""
Redis 缓存层 - 提升查询性能
支持知识点缓存、搜索结果缓存、图谱缓存
"""
import json
import redis.asyncio as aioredis
from typing import Any, Optional, List, Dict
from datetime import timedelta
from loguru import logger


class RedisCache:
    """Redis 缓存管理器"""

    def __init__(self, redis_client: aioredis.Redis):
        """
        Args:
            redis_client: aioredis.Redis 实例
        """
        self.client = redis_client
        self.default_ttl = timedelta(hours=1)

    @classmethod
    async def create(cls, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        创建 Redis 缓存实例

        Args:
            host: Redis 主机
            port: Redis 端口
            db: 数据库编号
            password: 密码（可选）

        Returns:
            RedisCache 实例
        """
        client = await aioredis.from_url(
            f"redis://{host}:{port}/{db}",
            password=password,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Redis 连接成功: {host}:{port}/{db}")
        return cls(client)

    async def close(self):
        """关闭 Redis 连接"""
        await self.client.close()
        logger.info("Redis 连接已关闭")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET 失败 [{key}]: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """设置缓存值"""
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            ttl = ttl or self.default_ttl
            await self.client.setex(key, int(ttl.total_seconds()), serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET 失败 [{key}]: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 失败 [{key}]: {e}")
            return False

    async def cache_knowledge(self, knowledge_id: str, knowledge_data: Dict[str, Any], ttl: Optional[timedelta] = None) -> bool:
        """缓存单个知识点"""
        key = f"knowledge:{knowledge_id}"
        return await self.set(key, knowledge_data, ttl)

    async def get_cached_knowledge(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的知识点"""
        key = f"knowledge:{knowledge_id}"
        return await self.get(key)

    async def cache_search_result(self, query: str, results: List[Dict[str, Any]], ttl: Optional[timedelta] = None) -> bool:
        """缓存搜索结果"""
        key = f"search:{query}"
        ttl = ttl or timedelta(minutes=10)
        return await self.set(key, results, ttl)

    async def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的搜索结果"""
        key = f"search:{query}"
        return await self.get(key)

    async def health_check(self) -> bool:
        """Redis 健康检查"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 健康检查失败: {e}")
            return False
