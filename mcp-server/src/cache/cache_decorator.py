"""
缓存装饰器
自动为 MCP 工具添加缓存元数据
"""
from functools import wraps
from typing import Callable, Union
from loguru import logger

from src.protocol.result_types import MCPResult


def cacheable(
    ttl_seconds: int,
    scope: str = "user"
):
    """
    缓存装饰器

    为 MCPResult 自动添加 _meta.ttlMs 和 _meta.cacheScope

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
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # 只处理 MCPResult 类型
            if isinstance(result, MCPResult):
                # 添加缓存元数据
                result.meta["ttlMs"] = ttl_seconds * 1000
                result.meta["cacheScope"] = scope

                logger.debug(
                    f"Added cache metadata to {func.__name__}: "
                    f"ttl={ttl_seconds}s, scope={scope}"
                )

            return result

        return wrapper
    return decorator
