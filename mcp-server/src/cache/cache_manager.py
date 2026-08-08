"""
缓存管理器
管理缓存失效和清理，支持 Redis 后端
"""
from typing import List, Optional, Set, Any
from datetime import datetime, timedelta, timezone
import asyncio
from loguru import logger

UTC = timezone.utc


class CacheManager:
    """
    缓存管理器

    负责：
    1. 跟踪哪些工具使用了缓存
    2. 提供缓存失效接口
    3. 自动清理过期缓存标记
    4. 管理 Redis 缓存后端
    5. 提供缓存命中率统计
    """

    def __init__(self, redis_cache=None):
        # Redis 缓存后端（可选）
        self.redis_cache = redis_cache

        # 缓存失效标记：{cache_key: expire_time}
        self._invalidation_marks: dict[str, datetime] = {}

        # 工具缓存配置：{tool_name: (ttl_seconds, scope)}
        self._tool_cache_config: dict[str, tuple[int, str]] = {}

        # 启动自动清理任务
        self._cleanup_task: Optional[asyncio.Task] = None

        # 缓存命中率统计
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_sets = 0

    def register_tool(self, tool_name: str, ttl_seconds: int, scope: str):
        """注册工具的缓存配置"""
        self._tool_cache_config[tool_name] = (ttl_seconds, scope)
        logger.info(f"Registered cache config for {tool_name}: ttl={ttl_seconds}s, scope={scope}")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值（优先使用 Redis）"""
        if self.redis_cache:
            try:
                value = await self.redis_cache.get(key)
                if value is not None:
                    self._cache_hits += 1
                    logger.debug(f"Redis cache hit: {key}")
                    return value
                else:
                    self._cache_misses += 1
                    logger.debug(f"Redis cache miss: {key}")
                    return None
            except Exception as e:
                logger.warning(f"Redis get failed [{key}]: {e}, falling back to memory")
                self._cache_misses += 1
                return None
        else:
            self._cache_misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """设置缓存值（优先使用 Redis）"""
        if self.redis_cache:
            try:
                success = await self.redis_cache.set(key, value, ttl)
                if success:
                    self._cache_sets += 1
                    logger.debug(f"Redis cache set: {key}")
                return success
            except Exception as e:
                logger.warning(f"Redis set failed [{key}]: {e}")
                return False
        else:
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if self.redis_cache:
            try:
                return await self.redis_cache.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed [{key}]: {e}")
                return False
        return False

    def invalidate(self, cache_keys: List[str]):
        """
        标记缓存失效并从 Redis 删除

        Args:
            cache_keys: 要失效的缓存键列表
        """
        now = datetime.now(UTC)
        for key in cache_keys:
            self._invalidation_marks[key] = now
            # 异步删除 Redis 缓存
            if self.redis_cache:
                asyncio.create_task(self.delete(key))
            logger.info(f"Marked cache as invalid: {key}")

    def invalidate_pattern(self, pattern: str):
        """
        按模式失效缓存

        Args:
            pattern: 缓存键模式 (支持简单通配符)
                例如: "search_knowledge:*" 失效所有知识搜索缓存
        """
        if "*" in pattern:
            prefix = pattern.replace("*", "")
            # 查找所有匹配的键
            matched_keys = [key for key in self._invalidation_marks.keys() if key.startswith(prefix)]

            if matched_keys:
                # 更新失效时间
                self.invalidate(matched_keys)
                logger.info(f"Invalidated {len(matched_keys)} caches matching pattern: {pattern}")

            # 立即从 Redis 删除匹配的键（同步执行）
            if self.redis_cache:
                # 创建后台任务但立即执行
                asyncio.create_task(self._delete_pattern_redis(pattern))
                logger.info(f"Scheduled Redis pattern deletion: {pattern}")
        else:
            self.invalidate([pattern])

    async def _delete_pattern_redis(self, pattern: str):
        """从 Redis 删除匹配模式的键"""
        if not self.redis_cache:
            return

        try:
            # 使用 KEYS 命令查找匹配的键（注意：生产环境应使用 SCAN）
            keys = await self.redis_cache.client.keys(pattern)
            if keys:
                for key in keys:
                    await self.redis_cache.delete(key)
                logger.info(f"Deleted {len(keys)} Redis keys matching pattern: {pattern}")
        except Exception as e:
            logger.error(f"Failed to delete Redis pattern [{pattern}]: {e}")

    def is_invalidated(self, cache_key: str) -> bool:
        """检查缓存是否已失效"""
        return cache_key in self._invalidation_marks

    def get_tool_cache_config(self, tool_name: str) -> Optional[tuple[int, str]]:
        """获取工具的缓存配置"""
        return self._tool_cache_config.get(tool_name)

    async def start_cleanup_task(self):
        """启动自动清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started cache cleanup task")

    async def stop_cleanup_task(self):
        """停止自动清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped cache cleanup task")

    async def _cleanup_loop(self):
        """自动清理过期的失效标记"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                await self._cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    async def _cleanup(self):
        """清理过期的失效标记（保留24小时）"""
        now = datetime.now(UTC)
        expire_threshold = now - timedelta(hours=24)

        expired_keys = [
            key for key, marked_time in self._invalidation_marks.items()
            if marked_time < expire_threshold
        ]

        for key in expired_keys:
            del self._invalidation_marks[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache marks")

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        hit_rate = 0.0
        total_requests = self._cache_hits + self._cache_misses
        if total_requests > 0:
            hit_rate = self._cache_hits / total_requests

        return {
            "backend": "redis" if self.redis_cache else "memory",
            "redis_available": self.redis_cache is not None,
            "registered_tools": len(self._tool_cache_config),
            "invalidated_caches": len(self._invalidation_marks),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_sets": self._cache_sets,
            "hit_rate": round(hit_rate, 4),
            "tools": self._tool_cache_config,
            "cache_efficiency": self._calculate_efficiency()
        }

    def _calculate_efficiency(self) -> float:
        """Calculate cache efficiency (lower invalidated ratio is better)"""
        if not self._tool_cache_config:
            return 1.0

        total_registered = len(self._tool_cache_config)
        invalidated = len(self._invalidation_marks)

        # Efficiency = (registered - invalidated) / registered
        if total_registered == 0:
            return 1.0

        return max(0.0, (total_registered - invalidated) / total_registered)


# 全局单例
cache_manager = CacheManager()
