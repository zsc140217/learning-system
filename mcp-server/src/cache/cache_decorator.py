"""
缓存装饰器
自动为 MCP 工具添加缓存功能和元数据
"""
from functools import wraps
from typing import Callable, Union
from datetime import timedelta
import hashlib
import json
from loguru import logger

from src.protocol.result_types import MCPResult


def cacheable(
    ttl_seconds: int,
    scope: str = "user"
):
    """
    缓存装饰器

    自动添加 Redis 缓存支持，并为 MCPResult 添加 _meta.ttlMs 和 _meta.cacheScope

    Args:
        ttl_seconds: 缓存生存时间（秒）
        scope: 缓存范围 ("user" | "session" | "public")
            - user: 用户级缓存
            - session: 会话级缓存
            - public: 公共缓存（所有用户共享）

    Example:
        @cacheable(ttl_seconds=3600, scope="user")
        async def search_knowledge(query: str) -> MCPResult:
            # 查询知识图谱
            return MCPResult(data={"results": [...]})
    """

    # 验证 scope
    valid_scopes = {"user", "session", "public"}
    if scope not in valid_scopes:
        raise ValueError(f"Invalid scope: {scope}, must be one of {valid_scopes}")

    def decorator(func: Callable) -> Callable:
        # 注册工具的缓存配置
        from .cache_manager import cache_manager
        cache_manager.register_tool(func.__name__, ttl_seconds, scope)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(func.__name__, args, kwargs, scope)

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                # 重建 MCPResult
                return MCPResult(
                    data=cached_result.get("data"),
                    meta=cached_result.get("meta", {}),
                    error=cached_result.get("error")
                )

            # 缓存未命中，执行函数
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
            result = await func(*args, **kwargs)

            # 只处理 MCPResult 类型
            if isinstance(result, MCPResult):
                # 添加缓存元数据
                result.meta["ttlMs"] = ttl_seconds * 1000
                result.meta["cacheScope"] = scope

                # 保存到缓存
                cache_data = {
                    "data": result.data,
                    "meta": result.meta
                }
                await cache_manager.set(
                    cache_key,
                    cache_data,
                    ttl=timedelta(seconds=ttl_seconds)
                )

                logger.debug(
                    f"Cached result for {func.__name__}: "
                    f"ttl={ttl_seconds}s, scope={scope}"
                )

            return result

        return wrapper
    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict, scope: str) -> str:
    """
    生成缓存键

    格式: {func_name}:{scope}:{args_hash}
    """
    # 序列化参数
    args_str = json.dumps({
        "args": args,
        "kwargs": kwargs
    }, sort_keys=True, ensure_ascii=False)

    # 生成哈希
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:16]

    return f"{func_name}:{scope}:{args_hash}"
