"""
缓存管理器
管理缓存失效和清理
"""
from typing import List, Optional, Set
from datetime import datetime, timedelta
import asyncio
from loguru import logger


class CacheManager:
    """
    缓存管理器

    负责：
    1. 跟踪哪些工具使用了缓存
    2. 提供缓存失效接口
    3. 自动清理过期缓存标记
    """

    def __init__(self):
        # 缓存失效标记：{cache_key: expire_time}
        self._invalidation_marks: dict[str, datetime] = {}

        # 工具缓存配置：{tool_name: (ttl_seconds, scope)}
        self._tool_cache_config: dict[str, tuple[int, str]] = {}

        # 启动自动清理任务
        self._cleanup_task: Optional[asyncio.Task] = None

    def register_tool(self, tool_name: str, ttl_seconds: int, scope: str):
        """注册工具的缓存配置"""
        self._tool_cache_config[tool_name] = (ttl_seconds, scope)
        logger.info(f"Registered cache config for {tool_name}: ttl={ttl_seconds}s, scope={scope}")

    def invalidate(self, cache_keys: List[str]):
        """
        标记缓存失效

        Args:
            cache_keys: 要失效的缓存键列表
        """
        now = datetime.utcnow()
        for key in cache_keys:
            self._invalidation_marks[key] = now
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
            else:
                logger.info(f"No caches found matching pattern: {pattern}")
        else:
            self.invalidate([pattern])

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
        now = datetime.utcnow()
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
        return {
            "registered_tools": len(self._tool_cache_config),
            "invalidated_caches": len(self._invalidation_marks),
            "tools": self._tool_cache_config
        }


# 全局单例
cache_manager = CacheManager()
