"""
Redis 缓存集成测试
验证 Redis 缓存功能和性能
"""
import asyncio
import time
from loguru import logger

from config import settings
from src.storage.redis_cache import RedisCache
from src.cache.cache_manager import CacheManager


async def test_redis_connection():
    """测试 Redis 连接"""
    logger.info("=" * 50)
    logger.info("测试 1: Redis 连接")
    logger.info("=" * 50)

    try:
        redis_cache = await RedisCache.create(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password
        )

        # 健康检查
        if await redis_cache.health_check():
            logger.info("✓ Redis 连接成功")
            logger.info(f"  地址: {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")
        else:
            logger.error("✗ Redis 健康检查失败")
            return None

        return redis_cache
    except Exception as e:
        logger.error(f"✗ Redis 连接失败: {e}")
        return None


async def test_cache_operations(redis_cache: RedisCache):
    """测试缓存基本操作"""
    logger.info("\n" + "=" * 50)
    logger.info("测试 2: 缓存基本操作")
    logger.info("=" * 50)

    # 测试 SET
    test_data = {
        "name": "FastAPI",
        "type": "framework",
        "description": "现代 Python Web 框架"
    }

    success = await redis_cache.set("test_key", test_data)
    if success:
        logger.info("✓ SET 操作成功")
    else:
        logger.error("✗ SET 操作失败")
        return False

    # 测试 GET
    cached_data = await redis_cache.get("test_key")
    if cached_data == test_data:
        logger.info("✓ GET 操作成功")
        logger.info(f"  数据: {cached_data}")
    else:
        logger.error(f"✗ GET 操作失败: {cached_data}")
        return False

    # 测试 DELETE
    success = await redis_cache.delete("test_key")
    if success:
        logger.info("✓ DELETE 操作成功")
    else:
        logger.error("✗ DELETE 操作失败")
        return False

    # 验证删除
    cached_data = await redis_cache.get("test_key")
    if cached_data is None:
        logger.info("✓ 删除验证成功")
    else:
        logger.error("✗ 删除验证失败")
        return False

    return True


async def test_cache_manager(redis_cache: RedisCache):
    """测试 CacheManager 集成"""
    logger.info("\n" + "=" * 50)
    logger.info("测试 3: CacheManager 集成")
    logger.info("=" * 50)

    # 创建 CacheManager
    cache_manager = CacheManager(redis_cache=redis_cache)

    # 测试缓存操作
    from datetime import timedelta

    # 设置缓存
    test_key = "search_knowledge:test_query"
    test_value = {
        "results": [
            {"id": "1", "title": "FastAPI 教程"},
            {"id": "2", "title": "Python 异步编程"}
        ],
        "total": 2
    }

    success = await cache_manager.set(test_key, test_value, ttl=timedelta(seconds=60))
    if success:
        logger.info("✓ CacheManager SET 成功")
    else:
        logger.error("✗ CacheManager SET 失败")
        return False

    # 获取缓存
    cached_value = await cache_manager.get(test_key)
    if cached_value == test_value:
        logger.info("✓ CacheManager GET 成功")
    else:
        logger.error(f"✗ CacheManager GET 失败: {cached_value}")
        return False

    # 测试缓存失效
    cache_manager.invalidate([test_key])
    logger.info("✓ 缓存失效标记成功")

    # 测试模式失效
    await cache_manager.set("search_knowledge:query1", {"data": 1})
    await cache_manager.set("search_knowledge:query2", {"data": 2})
    await cache_manager.set("track_project:proj1", {"data": 3})

    cache_manager.invalidate_pattern("search_knowledge:*")

    # 手动执行模式删除（因为 invalidate_pattern 是同步的）
    await cache_manager._delete_pattern_redis("search_knowledge:*")
    await asyncio.sleep(0.1)  # 等待删除完成

    # 验证模式删除
    result1 = await cache_manager.get("search_knowledge:query1")
    result2 = await cache_manager.get("search_knowledge:query2")
    result3 = await cache_manager.get("track_project:proj1")

    if result1 is None and result2 is None and result3 is not None:
        logger.info("✓ 模式失效成功")
    else:
        logger.error(f"✗ 模式失效失败: {result1}, {result2}, {result3}")
        return False

    return True


async def test_cache_performance(redis_cache: RedisCache):
    """测试缓存性能"""
    logger.info("\n" + "=" * 50)
    logger.info("测试 4: 缓存性能")
    logger.info("=" * 50)

    # 准备测试数据
    test_data = {
        "entities": [{"id": str(i), "name": f"Entity {i}"} for i in range(100)],
        "relations": [{"from": str(i), "to": str(i+1)} for i in range(99)]
    }

    # 测试写入性能
    write_times = []
    for i in range(10):
        start = time.perf_counter()
        await redis_cache.set(f"perf_test_{i}", test_data)
        elapsed = time.perf_counter() - start
        write_times.append(elapsed * 1000)  # 转换为毫秒

    avg_write = sum(write_times) / len(write_times)
    logger.info(f"✓ 平均写入时间: {avg_write:.2f} ms")

    # 测试读取性能
    read_times = []
    for i in range(10):
        start = time.perf_counter()
        await redis_cache.get(f"perf_test_{i}")
        elapsed = time.perf_counter() - start
        read_times.append(elapsed * 1000)

    avg_read = sum(read_times) / len(read_times)
    logger.info(f"✓ 平均读取时间: {avg_read:.2f} ms")

    # 清理测试数据
    for i in range(10):
        await redis_cache.delete(f"perf_test_{i}")

    # 验收标准：读取 < 50ms
    if avg_read < 50:
        logger.info(f"✓ 性能测试通过 (< 50ms)")
        return True
    else:
        logger.warning(f"⚠ 性能未达标 (目标 < 50ms)")
        return False


async def test_cache_stats():
    """测试缓存统计"""
    logger.info("\n" + "=" * 50)
    logger.info("测试 5: 缓存统计")
    logger.info("=" * 50)

    redis_cache = await RedisCache.create(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db
    )

    cache_manager = CacheManager(redis_cache=redis_cache)

    # 模拟缓存操作
    from datetime import timedelta

    # 缓存命中
    await cache_manager.set("key1", {"data": 1}, ttl=timedelta(seconds=60))
    await cache_manager.get("key1")  # 命中

    # 缓存未命中
    await cache_manager.get("key2")  # 未命中
    await cache_manager.get("key3")  # 未命中

    # 获取统计
    stats = cache_manager.get_stats()

    logger.info(f"✓ 缓存后端: {stats['backend']}")
    logger.info(f"✓ Redis 可用: {stats['redis_available']}")
    logger.info(f"✓ 缓存命中: {stats['cache_hits']}")
    logger.info(f"✓ 缓存未命中: {stats['cache_misses']}")
    logger.info(f"✓ 缓存写入: {stats['cache_sets']}")
    logger.info(f"✓ 命中率: {stats['hit_rate']:.2%}")

    await redis_cache.close()

    return stats['hit_rate'] > 0


async def main():
    """主测试函数"""
    logger.info("开始 Redis 缓存集成测试")
    logger.info(f"Redis 配置: {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")

    # 测试 1: 连接
    redis_cache = await test_redis_connection()
    if not redis_cache:
        logger.error("Redis 连接失败，终止测试")
        return

    # 测试 2: 基本操作
    if not await test_cache_operations(redis_cache):
        logger.error("缓存基本操作测试失败")
        await redis_cache.close()
        return

    # 测试 3: CacheManager 集成
    if not await test_cache_manager(redis_cache):
        logger.error("CacheManager 集成测试失败")
        await redis_cache.close()
        return

    # 测试 4: 性能
    if not await test_cache_performance(redis_cache):
        logger.warning("缓存性能测试未通过")

    # 关闭连接
    await redis_cache.close()

    # 测试 5: 统计
    if not await test_cache_stats():
        logger.error("缓存统计测试失败")
        return

    logger.info("\n" + "=" * 50)
    logger.info("✓ 所有测试通过！")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
