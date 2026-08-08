"""测试直接保存实体到 PostgreSQL"""
import asyncio
from src.storage.postgres_knowledge_graph import PostgresKnowledgeGraph
from config import settings

async def test():
    # 初始化 PostgreSQL
    pg = PostgresKnowledgeGraph(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        deepseek_api_key=settings.deepseek_api_key
    )

    await pg.connect()
    print("[OK] PostgreSQL connected")

    # 尝试创建实体
    try:
        entity = await pg.create_entity(
            name="测试知识点-直接调用",
            entity_type="Knowledge",
            observations=["这是一个测试内容"],
            metadata=None,
            graph_id=4  # 使用图谱 ID 4
        )
        print(f"[OK] Entity created: {entity}")
    except Exception as e:
        print(f"[ERROR] Failed to create entity: {e}")
        import traceback
        traceback.print_exc()

    # 验证数据库
    import asyncpg
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password
    )

    count = await conn.fetchval('SELECT COUNT(*) FROM entities')
    print(f"\n[INFO] Total entities in database: {count}")

    if count > 0:
        entities = await conn.fetch('SELECT id, name, graph_id FROM entities ORDER BY created_at DESC LIMIT 5')
        print("\n最近的实体:")
        for e in entities:
            print(f"  ID {e['id']}: {e['name']} (graph_id: {e['graph_id']})")

    await conn.close()
    await pg.close()

if __name__ == "__main__":
    asyncio.run(test())
