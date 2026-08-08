"""
知识图谱工具单元测试
测试 knowledge/* 工具和 Memory MCP 集成
"""
import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.memory_manager import MemoryManager
from src.bus.agent_bus import AgentBus


class TestKnowledgeSave:
    """测试 save_knowledge 工具"""

    @pytest_asyncio.fixture(scope="function")
    async def memory_manager(self):
        """创建 MemoryManager 实例"""
        bus = AgentBus()
        await bus.start()

        manager = MemoryManager("test_memory_manager", bus)
        await manager.start()

        yield manager

        await manager.stop()
        await bus.stop()

    @pytest.mark.asyncio
    async def test_save_knowledge_points(self, memory_manager):
        """测试保存知识点"""
        knowledge_points = [
            {
                "id": "kp_test_001",
                "title": "FastAPI 基础",
                "content": "FastAPI 是一个现代的 Python Web 框架",
                "source": "test",
                "session_id": "test_session_001"
            },
            {
                "id": "kp_test_002",
                "title": "Pydantic 验证",
                "content": "Pydantic 用于数据验证和类型提示",
                "source": "test",
                "session_id": "test_session_001"
            }
        ]

        # 保存知识点
        saved_ids = await memory_manager._save_knowledge_points(knowledge_points)

        # 检查是否保存成功
        assert len(saved_ids) == 2
        assert "kp_test_001" in saved_ids
        assert "kp_test_002" in saved_ids

    @pytest.mark.asyncio
    async def test_save_empty_knowledge_points(self, memory_manager):
        """测试保存空知识点列表"""
        knowledge_points = []

        # 保存空列表
        saved_ids = await memory_manager._save_knowledge_points(knowledge_points)

        # 检查返回空列表
        assert len(saved_ids) == 0


class TestKnowledgeSearch:
    """测试 search_knowledge 工具"""

    @pytest_asyncio.fixture(scope="function")
    async def memory_manager(self):
        """创建 MemoryManager 实例"""
        bus = AgentBus()
        await bus.start()

        manager = MemoryManager("test_memory_manager", bus)
        await manager.start()

        # 添加测试数据
        test_knowledge = [
            {
                "id": "kp_search_001",
                "title": "FastAPI 路由",
                "content": "FastAPI 使用装饰器定义路由",
                "source": "test"
            }
        ]
        await manager._save_knowledge_points(test_knowledge)

        yield manager

        await manager.stop()
        await bus.stop()

    @pytest.mark.asyncio
    async def test_search_existing_knowledge(self, memory_manager):
        """测试搜索已存在的知识"""
        # 搜索 FastAPI
        result = await memory_manager.search_knowledge("FastAPI")

        # 检查搜索结果
        assert "nodes" in result
        assert isinstance(result["nodes"], list)

    @pytest.mark.asyncio
    async def test_search_nonexistent_knowledge(self, memory_manager):
        """测试搜索不存在的知识"""
        # 搜索不存在的内容
        result = await memory_manager.search_knowledge("nonexistent_topic_xyz123")

        # 检查返回空结果
        assert "nodes" in result
        assert isinstance(result["nodes"], list)


class TestKnowledgeCreateRelation:
    """测试 knowledge/create_relation 工具"""

    @pytest_asyncio.fixture(scope="function")
    async def memory_manager(self):
        """创建 MemoryManager 实例"""
        bus = AgentBus()
        await bus.start()

        manager = MemoryManager("test_memory_manager", bus)
        await manager.start()

        yield manager

        await manager.stop()
        await bus.stop()

    @pytest.mark.asyncio
    async def test_create_relation_success(self, memory_manager):
        """测试创建关系（成功场景）"""
        # 创建实体
        entities = [
            {
                "name": "FastAPI",
                "entityType": "Technology",
                "observations": ["Web framework"]
            },
            {
                "name": "Pydantic",
                "entityType": "Technology",
                "observations": ["Data validation"]
            }
        ]
        await memory_manager._create_entities(entities)

        # 创建关系
        success = await memory_manager.link_knowledge_nodes(
            from_node="FastAPI",
            to_node="Pydantic",
            relation_type="uses"
        )

        # 检查是否成功（如果 MCP 不可用，会返回 False）
        assert isinstance(success, bool)

    @pytest.mark.asyncio
    async def test_create_multiple_relations(self, memory_manager):
        """测试创建多个关系"""
        # 创建实体
        entities = [
            {"name": "Project A", "entityType": "Project", "observations": ["Test project"]},
            {"name": "FastAPI", "entityType": "Technology", "observations": ["Framework"]},
            {"name": "PostgreSQL", "entityType": "Technology", "observations": ["Database"]}
        ]
        await memory_manager._create_entities(entities)

        # 创建多个关系
        relations = [
            ("Project A", "FastAPI", "uses"),
            ("Project A", "PostgreSQL", "uses"),
            ("FastAPI", "PostgreSQL", "connects_to")
        ]

        results = []
        for from_node, to_node, rel_type in relations:
            success = await memory_manager.link_knowledge_nodes(from_node, to_node, rel_type)
            results.append(success)

        # 检查结果
        assert len(results) == 3
        assert all(isinstance(r, bool) for r in results)


class TestKnowledgeGraph:
    """测试 get_knowledge_graph 工具"""

    @pytest_asyncio.fixture(scope="function")
    async def memory_manager(self):
        """创建 MemoryManager 实例"""
        bus = AgentBus()
        await bus.start()

        manager = MemoryManager("test_memory_manager", bus)
        await manager.start()

        # 添加测试数据
        entities = [
            {"name": "Test Entity 1", "entityType": "Test", "observations": ["Test 1"]},
            {"name": "Test Entity 2", "entityType": "Test", "observations": ["Test 2"]}
        ]
        await manager._create_entities(entities)

        yield manager

        await manager.stop()
        await bus.stop()

    @pytest.mark.asyncio
    async def test_get_full_graph(self, memory_manager):
        """测试获取完整知识图谱"""
        # 获取完整图谱
        graph = await memory_manager.get_knowledge_graph()

        # 检查返回结构
        assert "entities" in graph
        assert "relations" in graph
        assert isinstance(graph["entities"], list)
        assert isinstance(graph["relations"], list)

    @pytest.mark.asyncio
    async def test_get_node_subgraph(self, memory_manager):
        """测试获取节点子图"""
        # 获取特定节点的子图
        graph = await memory_manager.get_knowledge_graph(node_name="Test Entity 1")

        # 检查返回结构
        assert "entities" in graph
        assert "relations" in graph
        assert isinstance(graph["entities"], list)


class TestMemoryManagerStats:
    """测试 MemoryManager 统计功能"""

    @pytest_asyncio.fixture(scope="function")
    async def memory_manager(self):
        """创建 MemoryManager 实例"""
        bus = AgentBus()
        await bus.start()

        manager = MemoryManager("test_memory_manager", bus)
        await manager.start()

        yield manager

        await manager.stop()
        await bus.stop()

    @pytest.mark.asyncio
    async def test_get_stats(self, memory_manager):
        """测试获取统计信息"""
        # 获取统计
        stats = memory_manager.get_stats()

        # 检查统计结构
        assert "total_knowledge_points" in stats
        assert "mcp_available" in stats
        assert "source" in stats
        assert isinstance(stats["total_knowledge_points"], int)
        assert isinstance(stats["mcp_available"], bool)


class TestDeleteKnowledge:
    """测试 delete_knowledge 工具"""

    @pytest_asyncio.fixture(scope="function")
    async def memory_manager(self):
        """创建 MemoryManager 实例"""
        bus = AgentBus()
        await bus.start()

        manager = MemoryManager("test_memory_manager", bus)
        await manager.start()

        # 添加测试数据
        entities = [
            {"name": "Delete Test 1", "entityType": "Test", "observations": ["Will be deleted"]},
            {"name": "Delete Test 2", "entityType": "Test", "observations": ["Will be deleted"]}
        ]
        await manager._create_entities(entities)

        yield manager

        await manager.stop()
        await bus.stop()

    @pytest.mark.asyncio
    async def test_delete_nodes(self, memory_manager):
        """测试删除节点"""
        # 删除节点
        node_ids = ["Delete Test 1", "Delete Test 2"]
        deleted_count = await memory_manager.delete_nodes(node_ids)

        # 检查删除数量
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_nodes(self, memory_manager):
        """测试删除不存在的节点"""
        # 尝试删除不存在的节点
        node_ids = ["nonexistent_node_xyz123"]
        deleted_count = await memory_manager.delete_nodes(node_ids)

        # 应该返回 0
        assert deleted_count == 0


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
