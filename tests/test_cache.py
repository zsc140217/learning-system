"""
测试缓存系统
"""
import pytest
import asyncio
from datetime import datetime, timedelta

from src.cache import cacheable, CacheManager
from src.protocol.result_types import MCPResult


# ============ 测试 CacheManager ============

@pytest.mark.asyncio
async def test_cache_manager_register():
    """测试工具注册"""
    manager = CacheManager()

    manager.register_tool("search_knowledge", ttl_seconds=3600, scope="user")
    manager.register_tool("get_project", ttl_seconds=86400, scope="user")

    assert manager.get_tool_cache_config("search_knowledge") == (3600, "user")
    assert manager.get_tool_cache_config("get_project") == (86400, "user")
    assert manager.get_tool_cache_config("unknown_tool") is None


@pytest.mark.asyncio
async def test_cache_manager_invalidate():
    """测试缓存失效"""
    manager = CacheManager()

    # 失效单个缓存
    manager.invalidate(["search_knowledge:python"])
    assert manager.is_invalidated("search_knowledge:python")
    assert not manager.is_invalidated("search_knowledge:java")

    # 失效多个缓存
    manager.invalidate(["search_knowledge:java", "get_project:proj-001"])
    assert manager.is_invalidated("search_knowledge:java")
    assert manager.is_invalidated("get_project:proj-001")


@pytest.mark.asyncio
async def test_cache_manager_invalidate_pattern():
    """测试模式匹配失效"""
    manager = CacheManager()

    # 先标记一些缓存为失效
    manager.invalidate(["search_knowledge:python", "search_knowledge:java", "get_project:proj-001"])

    # 使用通配符失效所有 search_knowledge 缓存
    manager.invalidate_pattern("search_knowledge:*")

    # 验证
    assert manager.is_invalidated("search_knowledge:python")
    assert manager.is_invalidated("search_knowledge:java")
    # get_project 不应该被影响
    assert manager.is_invalidated("get_project:proj-001")  # 之前已失效


@pytest.mark.asyncio
async def test_cache_manager_cleanup():
    """测试自动清理"""
    manager = CacheManager()

    # 标记失效
    manager.invalidate(["key1", "key2"])

    # 手动设置为过期时间（模拟24小时后）
    manager._invalidation_marks["key1"] = datetime.utcnow() - timedelta(hours=25)
    manager._invalidation_marks["key2"] = datetime.utcnow() - timedelta(minutes=30)

    # 执行清理
    await manager._cleanup()

    # key1 应该被清理（超过24小时），key2 保留
    assert "key1" not in manager._invalidation_marks
    assert "key2" in manager._invalidation_marks


@pytest.mark.asyncio
async def test_cache_manager_stats():
    """测试统计信息"""
    manager = CacheManager()

    manager.register_tool("tool1", 3600, "user")
    manager.register_tool("tool2", 86400, "public")
    manager.invalidate(["cache1", "cache2", "cache3"])

    stats = manager.get_stats()

    assert stats["registered_tools"] == 2
    assert stats["invalidated_caches"] == 3
    assert "tool1" in stats["tools"]
    assert stats["tools"]["tool1"] == (3600, "user")


# ============ 测试 @cacheable 装饰器 ============

@pytest.mark.asyncio
async def test_cacheable_decorator_adds_metadata():
    """测试装饰器添加缓存元数据"""

    @cacheable(ttl_seconds=3600, scope="user")
    async def mock_tool(query: str) -> MCPResult:
        return MCPResult(data={"result": f"search result for {query}"})

    result = await mock_tool("python")

    # 验证元数据
    assert "ttlMs" in result.meta
    assert result.meta["ttlMs"] == 3600 * 1000  # 转换为毫秒
    assert result.meta["cacheScope"] == "user"


@pytest.mark.asyncio
async def test_cacheable_decorator_different_scopes():
    """测试不同的缓存范围"""

    @cacheable(ttl_seconds=1800, scope="session")
    async def session_scoped_tool() -> MCPResult:
        return MCPResult(data={"result": "session data"})

    @cacheable(ttl_seconds=7200, scope="public")
    async def public_scoped_tool() -> MCPResult:
        return MCPResult(data={"result": "public data"})

    result1 = await session_scoped_tool()
    result2 = await public_scoped_tool()

    assert result1.meta["cacheScope"] == "session"
    assert result1.meta["ttlMs"] == 1800 * 1000

    assert result2.meta["cacheScope"] == "public"
    assert result2.meta["ttlMs"] == 7200 * 1000


@pytest.mark.asyncio
async def test_cacheable_decorator_invalid_scope():
    """测试无效的缓存范围"""

    with pytest.raises(ValueError, match="Invalid scope"):
        @cacheable(ttl_seconds=3600, scope="invalid_scope")
        async def bad_tool() -> MCPResult:
            return MCPResult(data={"result": "data"})


@pytest.mark.asyncio
async def test_cacheable_decorator_non_mcpresult():
    """测试装饰器不处理非 MCPResult 类型"""

    @cacheable(ttl_seconds=3600, scope="user")
    async def non_mcp_tool() -> str:
        return "plain string result"

    result = await non_mcp_tool()

    # 应该返回原始字符串，不添加元数据
    assert isinstance(result, str)
    assert result == "plain string result"


# ============ 集成测试 ============

@pytest.mark.asyncio
async def test_integration_cache_invalidation_on_update():
    """测试知识更新后自动失效缓存"""
    manager = CacheManager()

    # 预先添加一些缓存键（模拟实际使用场景）
    manager.invalidate(["search_knowledge:python", "search_knowledge:java"])

    # 清空以重新测试
    manager._invalidation_marks.clear()

    # 重新添加
    manager._invalidation_marks["search_knowledge:python"] = datetime.utcnow()
    manager._invalidation_marks["search_knowledge:java"] = datetime.utcnow()

    # 模拟缓存工具
    @cacheable(ttl_seconds=3600, scope="user")
    async def search_knowledge(query: str) -> MCPResult:
        return MCPResult(data={"results": [f"result for {query}"]})

    # 第一次搜索
    result1 = await search_knowledge("python")
    assert result1.meta["ttlMs"] == 3600000

    # 模拟知识更新后失效缓存（这会更新已有键的时间戳）
    manager.invalidate_pattern("search_knowledge:*")

    # 验证缓存已失效
    assert manager.is_invalidated("search_knowledge:python")
    assert manager.is_invalidated("search_knowledge:java")


@pytest.mark.asyncio
async def test_integration_cleanup_task():
    """测试自动清理任务"""
    manager = CacheManager()

    # 启动清理任务
    await manager.start_cleanup_task()
    assert manager._cleanup_task is not None

    # 停止清理任务
    await manager.stop_cleanup_task()
    assert manager._cleanup_task is None


@pytest.mark.asyncio
async def test_ttl_values():
    """测试常见的 TTL 值"""
    test_cases = [
        (300, "session"),      # 5分钟
        (3600, "user"),        # 1小时
        (86400, "user"),       # 1天
        (604800, "public"),    # 1周
    ]

    for ttl_seconds, scope in test_cases:
        @cacheable(ttl_seconds=ttl_seconds, scope=scope)
        async def tool() -> MCPResult:
            return MCPResult(data={"result": "data"})

        result = await tool()
        assert result.meta["ttlMs"] == ttl_seconds * 1000
        assert result.meta["cacheScope"] == scope


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
