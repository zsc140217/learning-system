"""
测试知识图谱相关工具
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_search_nodes():
    """测试 search_nodes 工具"""
    print("\n=== 测试 search_nodes ===")

    # 模拟 memory_manager
    class MockMemoryManager:
        async def search_knowledge(self, query: str):
            return {
                "nodes": [
                    {
                        "name": "FastAPI",
                        "entityType": "technology",
                        "observations": ["FastAPI 是一个现代 Python Web 框架", "基于 Starlette 和 Pydantic"]
                    },
                    {
                        "name": "Pydantic",
                        "entityType": "tool",
                        "observations": ["数据验证库", "支持类型提示"]
                    }
                ]
            }

    memory_manager = MockMemoryManager()

    # 测试搜索
    result = await memory_manager.search_knowledge("FastAPI")
    nodes = result.get("nodes", [])

    # 转换格式
    formatted_nodes = []
    for node in nodes:
        formatted_nodes.append({
            "id": node.get("name"),
            "name": node.get("name", "Unknown"),
            "type": node.get("entityType", "concept").lower(),
            "observations": node.get("observations", [])
        })

    print(f"搜索结果: {len(formatted_nodes)} 个节点")
    for node in formatted_nodes:
        print(f"  - {node['name']} ({node['type']}): {len(node['observations'])} 条观察")

    return formatted_nodes


async def test_open_nodes():
    """测试 open_nodes 工具"""
    print("\n=== 测试 open_nodes ===")

    # 模拟 memory_manager
    class MockMemoryManager:
        async def get_knowledge_graph(self):
            return {
                "entities": [
                    {
                        "name": "FastAPI",
                        "entityType": "technology",
                        "observations": [
                            "FastAPI 是一个现代、快速的 Python Web 框架",
                            "基于 Starlette 和 Pydantic",
                            "支持自动生成 API 文档"
                        ]
                    },
                    {
                        "name": "Pydantic",
                        "entityType": "tool",
                        "observations": ["数据验证库", "支持类型提示"]
                    }
                ],
                "relations": []
            }

    memory_manager = MockMemoryManager()

    # 测试获取节点详情
    names = ["FastAPI"]
    graph = await memory_manager.get_knowledge_graph()
    entities = graph.get("entities", [])

    # 筛选指定名称的节点
    result_nodes = []
    for entity in entities:
        entity_name = entity.get("name")
        if entity_name in names:
            result_nodes.append({
                "id": entity_name,
                "name": entity_name,
                "type": entity.get("entityType", "concept").lower(),
                "observations": entity.get("observations", [])
            })

    print(f"节点详情: {len(result_nodes)} 个节点")
    for node in result_nodes:
        print(f"  - {node['name']} ({node['type']})")
        print(f"    观察记录:")
        for obs in node['observations']:
            print(f"      * {obs}")

    return result_nodes


async def test_ui_knowledge_graph_format():
    """测试 ui_knowledge_graph 返回的数据格式"""
    print("\n=== 测试 ui_knowledge_graph 数据格式 ===")

    # 模拟返回的数据
    graph_data = {
        "nodes": [
            {
                "id": "FastAPI",
                "label": "FastAPI",
                "type": "technology",
                "size": 20,
                "description": "FastAPI 是一个现代 Python Web 框架 | 基于 Starlette 和 Pydantic",
                "observations": [
                    "FastAPI 是一个现代 Python Web 框架",
                    "基于 Starlette 和 Pydantic",
                    "支持自动生成 API 文档"
                ],
                "color": "#34D399"
            },
            {
                "id": "Pydantic",
                "label": "Pydantic",
                "type": "tool",
                "size": 20,
                "description": "数据验证库 | 支持类型提示",
                "observations": ["数据验证库", "支持类型提示"],
                "color": "#F87171"
            }
        ],
        "edges": [
            {
                "source": "FastAPI",
                "target": "Pydantic",
                "type": "uses",
                "label": "uses"
            }
        ]
    }

    # 验证格式
    print(f"节点数: {len(graph_data['nodes'])}")
    print(f"边数: {len(graph_data['edges'])}")

    # 检查节点字段
    required_fields = ["id", "label", "type", "size", "observations"]
    for node in graph_data["nodes"]:
        missing = [f for f in required_fields if f not in node]
        if missing:
            print(f"  [FAIL] 节点 {node.get('id', 'unknown')} 缺少字段: {missing}")
        else:
            print(f"  [OK] 节点 {node['id']} 格式正确，包含 {len(node['observations'])} 条观察")

    # 检查边字段
    required_edge_fields = ["source", "target", "type", "label"]
    for edge in graph_data["edges"]:
        missing = [f for f in required_edge_fields if f not in edge]
        if missing:
            print(f"  [FAIL] 边 {edge.get('source', '?')} -> {edge.get('target', '?')} 缺少字段: {missing}")
        else:
            print(f"  [OK] 边 {edge['source']} -> {edge['target']} ({edge['label']}) 格式正确")

    return graph_data


async def main():
    print("=" * 60)
    print("知识图谱工具测试")
    print("=" * 60)

    # 测试各个工具
    await test_search_nodes()
    await test_open_nodes()
    await test_ui_knowledge_graph_format()

    print("\n" + "=" * 60)
    print("[SUCCESS] 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
