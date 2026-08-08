"""
数据库集成测试
验证 PostgreSQL + Redis + Memory MCP 三层存储架构
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.storage.postgres_repository import PostgresKnowledgeRepository
from src.storage.redis_cache import RedisCache


async def test_postgres_connection():
    """测试 PostgreSQL 连接"""
    print("\n========== 测试 PostgreSQL 连接 ==========")

    try:
        repo = await PostgresKnowledgeRepository.create(
            database_url="postgresql://learning_user:learning_pass_2026@localhost:5432/learning_system"
        )

        is_healthy = await repo.health_check()
        print(f"✅ PostgreSQL 健康检查: {'通过' if is_healthy else '失败'}")

        stats = await repo.get_statistics()
        print(f"📊 数据库统计:")
        print(f"   - 知识点数量: {stats['total_knowledge']}")
        print(f"   - 分类数量: {stats['categories']}")
        print(f"   - 关系数量: {stats['total_relations']}")

        await repo.close()
        return True

    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {e}")
        return False


async def test_redis_connection():
    """测试 Redis 连接"""
    print("\n========== 测试 Redis 连接 ==========")

    try:
        cache = await RedisCache.create(host="localhost", port=6379)

        is_healthy = await cache.health_check()
        print(f"✅ Redis 健康检查: {'通过' if is_healthy else '失败'}")

        test_key = "test:connection"
        test_value = {"message": "Redis is working"}

        await cache.set(test_key, test_value)
        cached_value = await cache.get(test_key)

        if cached_value == test_value:
            print(f"✅ Redis 读写测试: 通过")
        else:
            print(f"❌ Redis 读写测试: 失败")

        await cache.delete(test_key)
        await cache.close()
        return True

    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


async def test_knowledge_crud():
    """测试知识点 CRUD 操作"""
    print("\n========== 测试知识点 CRUD ==========")

    try:
        repo = await PostgresKnowledgeRepository.create(
            database_url="postgresql://learning_user:learning_pass_2026@localhost:5432/learning_system"
        )

        test_knowledge = [
            {
                "id": "test_crud_001",
                "title": "PostgreSQL 测试",
                "content": "测试 CRUD 操作",
                "category": "Test",
                "tags": ["test", "database"],
                "difficulty": 0.3,
                "confidence": 0.8,
                "source": "test_script",
                "session_id": "test_session"
            }
        ]

        saved_ids = await repo.save_knowledge_points(test_knowledge)
        print(f"✅ 创建知识点: {len(saved_ids)} 个")

        knowledge = await repo.get_knowledge_by_id("test_crud_001")
        if knowledge:
            print(f"✅ 读取知识点: {knowledge['title']}")

        results = await repo.search_knowledge("PostgreSQL", limit=5)
        print(f"✅ 搜索知识点: 找到 {len(results)} 个结果")

        deleted_count = await repo.delete_knowledge_points(["test_crud_001"])
        print(f"✅ 删除知识点: {deleted_count} 个")

        await repo.close()
        return True

    except Exception as e:
        print(f"❌ CRUD 测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 数据库集成测试套件")
    print("=" * 60)

    results = {}
    results["postgres"] = await test_postgres_connection()
    results["redis"] = await test_redis_connection()

    if results["postgres"]:
        results["crud"] = await test_knowledge_crud()

    print("\n" + "=" * 60)
    print("📋 测试结果汇总")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "✅ 通过" if passed_flag else "❌ 失败"
        print(f"{test_name:20s} : {status}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！数据库集成配置成功！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查配置")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
