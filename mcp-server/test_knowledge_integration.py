"""
测试知识图谱集成
验证本地存储和 save_knowledge 工具是否正常工作
"""
import asyncio
import json
import sys
from pathlib import Path
from loguru import logger

# 设置 UTF-8 输出（Windows）
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from config import settings
from src.storage.local_knowledge_graph import LocalKnowledgeGraph
from src.agents.memory_manager import MemoryManager
from src.bus.agent_bus import bus


async def test_local_storage():
    """测试本地知识图谱存储"""
    print("\n=== Test 1: Local Knowledge Graph Storage ===")

    db_path = Path(settings.data_dir) / "knowledge" / "test_graph.db"
    kg = LocalKnowledgeGraph(db_path)

    # 1. 创建实体
    print("\n1. Creating entities...")
    entities = [
        {
            "name": "FastAPI",
            "entityType": "Technology",
            "observations": [
                "Modern web framework for Python",
                "Uses dependency injection",
                "Supports async/await"
            ]
        },
        {
            "name": "Pydantic",
            "entityType": "Technology",
            "observations": [
                "Data validation library",
                "Used by FastAPI for request validation"
            ]
        }
    ]

    count = kg.create_entities(entities)
    print(f"[OK] Created {count} entities")

    # 2. 创建关系
    print("\n2. Creating relations...")
    relations = [
        {
            "from": "FastAPI",
            "to": "Pydantic",
            "relationType": "uses"
        }
    ]

    count = kg.create_relations(relations)
    print(f"[OK] Created {count} relations")

    # 3. 读取图谱
    print("\n3. Reading graph...")
    graph = kg.read_graph()
    print(f"[OK] Graph has {len(graph['entities'])} entities and {len(graph['relations'])} relations")

    # 4. 搜索节点
    print("\n4. Searching nodes...")
    results = kg.search_nodes("dependency injection", limit=5)
    print(f"[OK] Found {len(results)} nodes matching 'dependency injection'")
    for node in results:
        print(f"  - {node['name']} (score: {node.get('score', 'N/A')})")

    # 5. 打开节点
    print("\n5. Opening nodes...")
    nodes = kg.open_nodes(["FastAPI"])
    print(f"[OK] Opened {len(nodes)} nodes")
    for node in nodes:
        print(f"  - {node['name']}: {len(node.get('observations', []))} observations")

    print("\n[OK] Local storage test PASSED")

    # 清理测试数据库
    if db_path.exists():
        db_path.unlink()
        print(f"[OK] Cleaned up test database: {db_path}")


async def test_memory_manager():
    """测试 MemoryManager 集成"""
    print("\n=== Test 2: MemoryManager Integration ===")

    # 启动事件总线
    await bus.start()

    # 初始化 MemoryManager（带本地数据库路径）
    db_path = str(Path(settings.data_dir) / "knowledge" / "test_manager.db")
    manager = MemoryManager("test_manager", bus, local_db_path=db_path)
    await manager.start()

    print(f"\n1. MemoryManager initialized with local_db_path: {db_path}")
    print(f"   MCP available: {manager._mcp_available}")

    # 测试保存知识点
    print("\n2. Saving knowledge points...")
    knowledge_points = [
        {
            "id": "kp_001",
            "title": "FastAPI Routing",
            "content": "FastAPI uses decorators like @app.get() for routing",
            "source": "test",
            "session_id": "test_session"
        },
        {
            "id": "kp_002",
            "title": "FastAPI Dependencies",
            "content": "Use Depends() for dependency injection in FastAPI",
            "source": "test",
            "session_id": "test_session"
        }
    ]

    saved_ids = await manager._save_knowledge_points(knowledge_points)
    print(f"[OK] Saved {len(saved_ids)} knowledge points: {saved_ids}")

    # 测试搜索
    print("\n3. Searching knowledge...")
    result = await manager.search_knowledge("routing")
    print(f"[OK] Found {len(result['nodes'])} nodes")
    print(f"   Source: {result['source']}")

    # 测试获取图谱
    print("\n4. Getting knowledge graph...")
    graph = await manager.get_knowledge_graph()
    print(f"[OK] Graph has {len(graph['entities'])} entities")
    print(f"   Source: {graph['source']}")

    # 获取统计信息
    print("\n5. Getting stats...")
    stats = manager.get_stats()
    print(f"[OK] Total knowledge points: {stats['total_knowledge_points']}")
    print(f"     MCP available: {stats['mcp_available']}")
    print(f"     Source: {stats['source']}")

    print("\n[OK] MemoryManager test PASSED")

    # 清理
    await manager.stop()
    await bus.stop()

    # 清理测试数据库
    test_db = Path(db_path)
    if test_db.exists():
        test_db.unlink()
        print(f"[OK] Cleaned up test database: {test_db}")


async def main():
    """运行所有测试"""
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="WARNING")

    print("=" * 60)
    print("Knowledge Graph Integration Tests")
    print("=" * 60)

    try:
        # 测试 1: 本地存储
        await test_local_storage()

        # 测试 2: MemoryManager 集成
        await test_memory_manager()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
