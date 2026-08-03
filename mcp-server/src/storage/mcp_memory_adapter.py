"""
MCP Memory Adapter
封装 MCP Memory 的 5 个核心方法，提供类型安全的知识图谱操作接口
"""
from typing import Dict, Any, List, Optional
from loguru import logger


class MCPMemoryAdapter:
    """
    MCP Memory 适配器

    核心 API:
    - create_entities() - 创建知识节点
    - create_relations() - 建立节点关系
    - search_nodes() - 语义搜索
    - open_nodes() - 获取节点详情
    - read_graph() - 读取完整图谱
    """

    def __init__(self, mcp_tools: Dict[str, Any]):
        """
        Args:
            mcp_tools: MCP 工具字典，从 server.py 注入
        """
        self._mcp_tools = mcp_tools
        self._available = self._check_availability()

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
        if not self._available:
            raise RuntimeError("MCP Memory not available")

        try:
            tool = self._mcp_tools["mcp__plugin_ecc_memory__create_entities"]
            await tool(entities=entities)
            logger.info(f"Created {len(entities)} entities in MCP Memory")
            return len(entities)
        except Exception as e:
            logger.error(f"Failed to create entities: {e}")
            raise

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
        if not self._available:
            raise RuntimeError("MCP Memory not available")

        try:
            tool = self._mcp_tools["mcp__plugin_ecc_memory__create_relations"]
            await tool(relations=relations)
            logger.info(f"Created {len(relations)} relations in MCP Memory")
            return len(relations)
        except Exception as e:
            logger.error(f"Failed to create relations: {e}")
            raise

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
        if not self._available:
            raise RuntimeError("MCP Memory not available")

        try:
            tool = self._mcp_tools["mcp__plugin_ecc_memory__search_nodes"]
            result = await tool(query=query)

            # MCP Memory 返回格式可能需要适配
            nodes = result if isinstance(result, list) else []
            logger.info(f"Found {len(nodes)} nodes for query: {query}")
            return nodes
        except Exception as e:
            logger.error(f"Failed to search nodes: {e}")
            raise

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
        if not self._available:
            raise RuntimeError("MCP Memory not available")

        try:
            tool = self._mcp_tools["mcp__plugin_ecc_memory__open_nodes"]
            result = await tool(names=names)
            nodes = result if isinstance(result, list) else []
            logger.info(f"Opened {len(nodes)} nodes")
            return nodes
        except Exception as e:
            logger.error(f"Failed to open nodes: {e}")
            raise

    async def read_graph(self) -> Dict[str, Any]:
        """
        读取完整知识图谱

        Returns:
            {
                "entities": [...],
                "relations": [...]
            }
        """
        if not self._available:
            raise RuntimeError("MCP Memory not available")

        try:
            tool = self._mcp_tools["mcp__plugin_ecc_memory__read_graph"]
            result = await tool()
            logger.info("Read complete knowledge graph")
            return result
        except Exception as e:
            logger.error(f"Failed to read graph: {e}")
            raise

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
        if not self._available:
            raise RuntimeError("MCP Memory not available")

        try:
            tool = self._mcp_tools["mcp__plugin_ecc_memory__add_observations"]
            await tool(observations=[{
                "entityName": entity_name,
                "contents": observations
            }])
            logger.info(f"Added {len(observations)} observations to {entity_name}")
        except Exception as e:
            logger.error(f"Failed to add observations: {e}")
            raise
