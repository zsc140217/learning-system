"""
MCP Memory Integration Tests
测试知识图谱的创建、关系和搜索
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

import pytest
from src.storage.mcp_memory_adapter import MCPMemoryAdapter
from src.agents.memory_manager import MemoryManager
from src.bus.agent_bus import AgentBus


@pytest.mark.asyncio
async def test_mcp_memory_adapter_availability():
    """测试 Adapter 可用性检查"""
    async def mock_create_entities(**kwargs):
        return None

    async def mock_create_relations(**kwargs):
        return None

    async def mock_search_nodes(**kwargs):
        return []

    mcp_tools = {
        "mcp__plugin_ecc_memory__create_entities": mock_create_entities,
        "mcp__plugin_ecc_memory__create_relations": mock_create_relations,
        "mcp__plugin_ecc_memory__search_nodes": mock_search_nodes,
    }

    adapter = MCPMemoryAdapter(mcp_tools)
    assert adapter.available is True


@pytest.mark.asyncio
async def test_mcp_memory_adapter_unavailable():
    """测试 Adapter 不可用时的 fallback"""
    mcp_tools = {}
    adapter = MCPMemoryAdapter(mcp_tools)
    assert adapter.available is False


@pytest.mark.asyncio
async def test_create_knowledge_entities():
    """测试创建知识节点"""
    async def mock_create_entities(**kwargs):
        return None

    async def mock_create_relations(**kwargs):
        return None

    async def mock_search_nodes(**kwargs):
        return []

    mcp_tools = {
        "mcp__plugin_ecc_memory__create_entities": mock_create_entities,
        "mcp__plugin_ecc_memory__create_relations": mock_create_relations,
        "mcp__plugin_ecc_memory__search_nodes": mock_search_nodes,
    }

    adapter = MCPMemoryAdapter(mcp_tools)

    entities = [{
        "name": "FastAPI 依赖注入",
        "entityType": "Knowledge",
        "observations": ["测试观察"]
    }]

    count = await adapter.create_entities(entities)
    assert count == 1


@pytest.mark.asyncio
async def test_create_knowledge_relations():
    """测试建立知识关系"""
    async def mock_create_entities(**kwargs):
        return None

    async def mock_create_relations(**kwargs):
        return None

    async def mock_search_nodes(**kwargs):
        return []

    mcp_tools = {
        "mcp__plugin_ecc_memory__create_entities": mock_create_entities,
        "mcp__plugin_ecc_memory__create_relations": mock_create_relations,
        "mcp__plugin_ecc_memory__search_nodes": mock_search_nodes,
    }

    adapter = MCPMemoryAdapter(mcp_tools)

    relations = [{
        "from": "FastAPI 依赖注入",
        "to": "Python 装饰器",
        "relationType": "requires"
    }]

    count = await adapter.create_relations(relations)
    assert count == 1


@pytest.mark.asyncio
async def test_search_knowledge_nodes():
    """测试语义搜索"""
    mock_results = [
        {"name": "FastAPI 路由", "entityType": "Knowledge"}
    ]

    async def mock_create_entities(**kwargs):
        return None

    async def mock_create_relations(**kwargs):
        return None

    async def mock_search_nodes(**kwargs):
        return mock_results

    mcp_tools = {
        "mcp__plugin_ecc_memory__create_entities": mock_create_entities,
        "mcp__plugin_ecc_memory__create_relations": mock_create_relations,
        "mcp__plugin_ecc_memory__search_nodes": mock_search_nodes,
    }

    adapter = MCPMemoryAdapter(mcp_tools)

    results = await adapter.search_nodes("如何实现路由")
    assert len(results) == 1
    assert results[0]["name"] == "FastAPI 路由"


@pytest.mark.asyncio
async def test_memory_manager_creates_relations():
    """测试 MemoryManager 创建关系"""
    bus = AgentBus()

    async def mock_create_entities(**kwargs):
        return None

    async def mock_create_relations(**kwargs):
        return None

    async def mock_search_nodes(**kwargs):
        return []

    mcp_tools = {
        "mcp__plugin_ecc_memory__create_entities": mock_create_entities,
        "mcp__plugin_ecc_memory__create_relations": mock_create_relations,
        "mcp__plugin_ecc_memory__search_nodes": mock_search_nodes,
    }

    manager = MemoryManager("test_memory", bus, mcp_tools)
    await manager.start()

    result = await manager.link_knowledge_nodes(
        "FastAPI 路由",
        "FastAPI 依赖注入",
        "related_to"
    )

    assert result is True

    await manager.stop()


@pytest.mark.asyncio
async def test_session_analyzer_infers_relations():
    """测试 SessionAnalyzer 推断关系"""
    from src.agents.session_analyzer import SessionAnalyzer

    bus = AgentBus()
    analyzer = SessionAnalyzer("test_analyzer", bus)

    knowledge_points = [
        {"id": "kp1", "title": "FastAPI 路由", "content": "..."},
        {"id": "kp2", "title": "FastAPI 依赖注入", "content": "..."}
    ]

    relations = analyzer._infer_relations(knowledge_points)

    assert len(relations) == 1
    assert relations[0]["from"] == "FastAPI 路由"
    assert relations[0]["to"] == "FastAPI 依赖注入"
    assert relations[0]["relationType"] == "related_to"


@pytest.mark.asyncio
async def test_multiple_knowledge_points_relations():
    """测试多个知识点之间的关系推断"""
    from src.agents.session_analyzer import SessionAnalyzer

    bus = AgentBus()
    analyzer = SessionAnalyzer("test_analyzer", bus)

    knowledge_points = [
        {"id": "kp1", "title": "FastAPI 路由", "content": "..."},
        {"id": "kp2", "title": "FastAPI 依赖注入", "content": "..."},
        {"id": "kp3", "title": "FastAPI 中间件", "content": "..."}
    ]

    relations = analyzer._infer_relations(knowledge_points)

    assert len(relations) == 3
    assert relations[0]["from"] == "FastAPI 路由"
    assert relations[0]["to"] == "FastAPI 依赖注入"
    assert relations[1]["from"] == "FastAPI 路由"
    assert relations[1]["to"] == "FastAPI 中间件"
    assert relations[2]["from"] == "FastAPI 依赖注入"
    assert relations[2]["to"] == "FastAPI 中间件"


@pytest.mark.asyncio
async def test_open_nodes():
    """测试获取节点详情"""
    mock_nodes = [
        {
            "name": "FastAPI 路由",
            "entityType": "Knowledge",
            "observations": ["路由装饰器的使用"]
        }
    ]

    async def mock_create_entities(**kwargs):
        return None

    async def mock_create_relations(**kwargs):
        return None

    async def mock_search_nodes(**kwargs):
        return []

    async def mock_open_nodes(**kwargs):
        return mock_nodes

    mcp_tools = {
        "mcp__plugin_ecc_memory__create_entities": mock_create_entities,
        "mcp__plugin_ecc_memory__create_relations": mock_create_relations,
        "mcp__plugin_ecc_memory__search_nodes": mock_search_nodes,
        "mcp__plugin_ecc_memory__open_nodes": mock_open_nodes,
    }

    adapter = MCPMemoryAdapter(mcp_tools)

    nodes = await adapter.open_nodes(["FastAPI 路由"])
    assert len(nodes) == 1
    assert nodes[0]["name"] == "FastAPI 路由"


@pytest.mark.asyncio
async def test_read_graph():
    """测试读取完整图谱"""
    mock_graph = {
        "entities": [
            {"name": "FastAPI 路由", "entityType": "Knowledge"}
        ],
        "relations": [
            {"from": "FastAPI 路由", "to": "FastAPI 依赖注入", "relationType": "related_to"}
        ]
    }

    async def mock_create_entities(**kwargs):
        return None

    async def mock_create_relations(**kwargs):
        return None

    async def mock_search_nodes(**kwargs):
        return []

    async def mock_read_graph(**kwargs):
        return mock_graph

    mcp_tools = {
        "mcp__plugin_ecc_memory__create_entities": mock_create_entities,
        "mcp__plugin_ecc_memory__create_relations": mock_create_relations,
        "mcp__plugin_ecc_memory__search_nodes": mock_search_nodes,
        "mcp__plugin_ecc_memory__read_graph": mock_read_graph,
    }

    adapter = MCPMemoryAdapter(mcp_tools)

    graph = await adapter.read_graph()
    assert "entities" in graph
    assert "relations" in graph
    assert len(graph["entities"]) == 1
    assert len(graph["relations"]) == 1
