"""
MCP Memory Adapter
封装 MCP Memory 的 5 个核心方法，提供类型安全的知识图谱操作接口
如果 MCP Memory 不可用，自动降级为本地 SQLite 存储
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger

from .local_knowledge_graph import LocalKnowledgeGraph


class MCPMemoryAdapter:
    """
    MCP Memory 适配器

    核心 API:
    - create_entities() - 创建知识节点
    - create_relations() - 建立节点关系
    - search_nodes() - 语义搜索
    - open_nodes() - 获取节点详情
    - read_graph() - 读取完整图谱

    自动降级：
    - 优先使用 MCP Memory 插件（如果可用）
    - 不可用时自动使用本地 SQLite + 向量搜索
    """

    def __init__(self, mcp_tools: Dict[str, Any], local_db_path: Optional[str] = None):
        """
        Args:
            mcp_tools: MCP 工具字典，从 server.py 注入
            local_db_path: 本地数据库路径，默认为 data/knowledge/graph.db
        """
        self._mcp_tools = mcp_tools
        self._available = self._check_availability()

        # 初始化本地存储（作为 fallback）
        if local_db_path is None:
            local_db_path = "data/knowledge/graph.db"

        self._local_storage = LocalKnowledgeGraph(local_db_path)
        logger.info(f"MCPMemoryAdapter initialized - MCP: {self._available}, Local storage: {local_db_path}")

    def _check_availability(self) -> bool:
        """检查 MCP Memory 插件是否可用"""
        required_tools = [
            "mcp__plugin_ecc_memory__create_entities",
            "mcp__plugin_ecc_memory__create_relations",
            "mcp__plugin_ecc_memory__search_nodes",
        ]

        for tool_name in required_tools:
            if tool_name not in self._mcp_tools:
                logger.warning(f"MCP Memory tool not found: {tool_name}")
                return False

        return True

    @property
    def available(self) -> bool:
        """MCP Memory 是否可用"""
        return self._available

    async def create_entities(
        self,
        entities: List[Dict[str, Any]]
    ) -> int:
        """
        创建知识节点

        Args:
            entities: [
                {
                    "name": "FastAPI 依赖注入",
                    "entityType": "Knowledge",
                    "observations": [
                        "使用 Depends() 实现依赖注入",
                        "支持同步和异步依赖",
                        "Source: session_abc123"
                    ]
                }
            ]

        Returns:
            创建成功的节点数量
        """
        # 优先使用 MCP Memory
        if self._available:
            try:
                tool = self._mcp_tools["mcp__plugin_ecc_memory__create_entities"]
                await tool(entities=entities)
                logger.info(f"Created {len(entities)} entities in MCP Memory")
                return len(entities)
            except Exception as e:
                logger.warning(f"MCP Memory failed, falling back to local storage: {e}")

        # Fallback 到本地存储
        count = self._local_storage.create_entities(entities)
        logger.info(f"Created {count} entities in local storage")
        return count

    async def create_relations(
        self,
        relations: List[Dict[str, Any]]
    ) -> int:
        """
        建立节点关系

        Args:
            relations: [
                {
                    "from": "FastAPI 依赖注入",
                    "to": "Python 装饰器",
                    "relationType": "requires"
                }
            ]

        Returns:
            创建成功的关系数量
        """
        # 优先使用 MCP Memory
        if self._available:
            try:
                tool = self._mcp_tools["mcp__plugin_ecc_memory__create_relations"]
                await tool(relations=relations)
                logger.info(f"Created {len(relations)} relations in MCP Memory")
                return len(relations)
            except Exception as e:
                logger.warning(f"MCP Memory failed, falling back to local storage: {e}")

        # Fallback 到本地存储
        count = self._local_storage.create_relations(relations)
        logger.info(f"Created {count} relations in local storage")
        return count

    async def search_nodes(
        self,
        query: str
    ) -> List[Dict[str, Any]]:
        """
        语义搜索节点

        Args:
            query: "如何实现路由"

        Returns:
            匹配的节点列表:
            [
                {
                    "name": "FastAPI 路由系统",
                    "entityType": "Knowledge",
                    "observations": [...],
                    "relations": [...]
                }
            ]
        """
        # 优先使用 MCP Memory
        if self._available:
            try:
                tool = self._mcp_tools["mcp__plugin_ecc_memory__search_nodes"]
                result = await tool(query=query)

                # MCP Memory 返回格式可能需要适配
                nodes = result if isinstance(result, list) else []
                logger.info(f"MCP Memory found {len(nodes)} nodes for query: {query}")
                return nodes
            except Exception as e:
                logger.warning(f"MCP Memory failed, falling back to local storage: {e}")

        # Fallback 到本地存储
        nodes = self._local_storage.search_nodes(query, limit=10)
        logger.info(f"Local search found {len(nodes)} nodes for query: {query}")
        return nodes

    async def open_nodes(
        self,
        names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        获取节点详情（含关系）

        Args:
            names: ["FastAPI 依赖注入", "Python 装饰器"]

        Returns:
            节点详情列表（包含 relations 字段）
        """
        # 优先使用 MCP Memory
        if self._available:
            try:
                tool = self._mcp_tools["mcp__plugin_ecc_memory__open_nodes"]
                result = await tool(names=names)
                nodes = result if isinstance(result, list) else []
                logger.info(f"MCP Memory opened {len(nodes)} nodes")
                return nodes
            except Exception as e:
                logger.warning(f"MCP Memory failed, falling back to local storage: {e}")

        # Fallback 到本地存储
        nodes = self._local_storage.open_nodes(names)
        logger.info(f"Local storage opened {len(nodes)} nodes")
        return nodes

    async def read_graph(self) -> Dict[str, Any]:
        """
        读取完整知识图谱

        Returns:
            {
                "entities": [...],
                "relations": [...]
            }
        """
        # 优先使用 MCP Memory
        if self._available:
            try:
                tool = self._mcp_tools["mcp__plugin_ecc_memory__read_graph"]
                result = await tool()
                logger.info("MCP Memory read complete knowledge graph")
                return result
            except Exception as e:
                logger.warning(f"MCP Memory failed, falling back to local storage: {e}")

        # Fallback 到本地存储
        graph = self._local_storage.read_graph()
        logger.info(f"Local storage read graph: {len(graph.get('entities', []))} entities, {len(graph.get('relations', []))} relations")
        return graph

    async def add_observations(
        self,
        entity_name: str,
        observations: List[str]
    ) -> None:
        """
        向已有节点添加新观察

        Args:
            entity_name: "FastAPI 依赖注入"
            observations: ["新增：支持 yield 依赖"]
        """
        # 优先使用 MCP Memory
        if self._available:
            try:
                tool = self._mcp_tools["mcp__plugin_ecc_memory__add_observations"]
                await tool(observations=[{
                    "entityName": entity_name,
                    "contents": observations
                }])
                logger.info(f"MCP Memory added {len(observations)} observations to {entity_name}")
                return
            except Exception as e:
                logger.warning(f"MCP Memory failed, falling back to local storage: {e}")

        # Fallback 到本地存储：通过更新 entity 实现
        # 先读取现有 entity，添加新 observations
        existing = self._local_storage.open_nodes([entity_name])
        if existing:
            entity = existing[0]
            updated_observations = entity.get("observations", []) + observations
            self._local_storage.create_entities([{
                "name": entity_name,
                "entityType": entity.get("entityType", "Knowledge"),
                "observations": updated_observations
            }])
            logger.info(f"Local storage added {len(observations)} observations to {entity_name}")
        else:
            logger.warning(f"Entity not found: {entity_name}")

    async def delete_entities(
        self,
        entity_names: List[str]
    ) -> int:
        """
        删除知识节点

        Args:
            entity_names: ["knowledge_1722518400_a7b3c9d2", ...]

        Returns:
            删除成功的节点数量
        """
        # 优先使用 MCP Memory
        if self._available:
            try:
                tool = self._mcp_tools["mcp__plugin_ecc_memory__delete_entities"]
                await tool(entityNames=entity_names)
                logger.info(f"MCP Memory deleted {len(entity_names)} entities")
                return len(entity_names)
            except Exception as e:
                logger.warning(f"MCP Memory failed, falling back to local storage: {e}")

        # Fallback 到本地存储
        count = self._local_storage.delete_entities(entity_names)
        logger.info(f"Local storage deleted {count} entities")
        return count
