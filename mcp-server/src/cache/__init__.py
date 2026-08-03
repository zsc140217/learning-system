"""
缓存模块
提供装饰器和缓存管理功能
"""
from .cache_decorator import cacheable
from .cache_manager import CacheManager, cache_manager

__all__ = ["cacheable", "CacheManager", "cache_manager"]
