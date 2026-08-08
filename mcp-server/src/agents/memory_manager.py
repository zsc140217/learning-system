"""
Memory Manager Agent
Manages knowledge storage and retrieval using PostgreSQL/Local KG
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent
from ..storage.mcp_memory_adapter import MCPMemoryAdapter
from ..storage.postgres_knowledge_graph import PostgresKnowledgeGraph
from ..storage.local_knowledge_graph import LocalKnowledgeGraph


class MemoryManager(BaseAgent):
    """
    Manages knowledge points with multi-tier storage.

    Storage Priority:
    1. PostgresKnowledgeGraph (production)
    2. LocalKnowledgeGraph (SQLite fallback)
    3. MCPMemoryAdapter (MCP integration demo)
    4. In-memory fallback

    Subscribes to: knowledge.extracted, project.analysis_completed
    Emits: knowledge.saved, knowledge.search_completed
    """

    def __init__(
        self,
        agent_id: str,
        bus,
        knowledge_graph: Optional[Union[PostgresKnowledgeGraph, LocalKnowledgeGraph]] = None,
        mcp_tools: Optional[Dict] = None,
        local_db_path: Optional[str] = None
    ):
        super().__init__(agent_id, bus)

        # Primary storage: PostgreSQL or Local KG
        self._knowledge_graph = knowledge_graph

        # Public accessor for graph management tools
        self.kg_storage = knowledge_graph

        # MCP Memory Adapter (for demo/visualization)
        self._mcp_adapter = MCPMemoryAdapter(mcp_tools or {}, local_db_path=local_db_path)

        # In-memory fallback store when all backends unavailable
        self._fallback_store: Dict[str, Dict[str, Any]] = {}

        # Availability flags
        self._kg_available: bool = knowledge_graph is not None
        self._mcp_available: Optional[bool] = None

    async def start(self) -> None:
        """Start the manager and subscribe to knowledge events"""
        await super().start()
        await self.subscribe("knowledge.extracted")
        await self.subscribe("project.analysis_completed")

        # Check MCP availability on startup
        self._mcp_available = self._mcp_adapter.available

        # Log storage backend status
        if self._kg_available:
            kg_type = type(self._knowledge_graph).__name__
            logger.info(f"MemoryManager started with {kg_type} (primary), MCP available: {self._mcp_available}")
        else:
            logger.info(f"MemoryManager started with MCP only, MCP available: {self._mcp_available}")

    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process knowledge events and save to Memory MCP

        Args:
            event: Event containing session_id and knowledge_points or project analysis
        """
        event_type = event.get("type")

        if event_type == "knowledge.extracted":
            await self._handle_knowledge_extracted(event)
        elif event_type == "project.analysis_completed":
            await self._handle_project_analysis(event)

    async def _handle_knowledge_extracted(self, event: Dict[str, Any]) -> None:
        """Handle knowledge.extracted event"""
        session_id = event.get("session_id")
        knowledge_points = event.get("knowledge_points", [])
        relations = event.get("relations", [])

        # Save knowledge points
        saved_ids = await self._save_knowledge_points(knowledge_points)

        # Create relations if MCP is available
        if relations and self._mcp_available:
            try:
                await self._mcp_adapter.create_relations(relations)
                logger.info(f"Created {len(relations)} relations for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to create relations: {e}")

        # Emit knowledge saved event
        await self.emit({
            "type": "knowledge.saved",
            "session_id": session_id,
            "saved_count": len(saved_ids),
            "knowledge_ids": saved_ids,
            "relations_count": len(relations)
        })

    async def _handle_project_analysis(self, event: Dict[str, Any]) -> None:
        """
        Handle project.analysis_completed event
        Save project tech stack and architecture to knowledge graph
        """
        project_id = event.get("project_id")
        analysis = event.get("analysis", {})

        # Extract technologies from tech stack
        tech_stack = analysis.get("tech_stack", {})
        frameworks = tech_stack.get("frameworks", [])
        databases = tech_stack.get("databases", [])

        # Create entities for each technology
        entities = []
        for framework in frameworks:
            entities.append({
                "name": framework.get("name"),
                "entityType": "Technology",
                "observations": [
                    f"Used in project {project_id}",
                    f"Category: Framework",
                    f"Analysis date: {analysis.get('timestamp', 'unknown')}"
                ]
            })

        for database in databases:
            entities.append({
                "name": database.get("name"),
                "entityType": "Technology",
                "observations": [
                    f"Used in project {project_id}",
                    f"Category: Database",
                    f"Analysis date: {analysis.get('timestamp', 'unknown')}"
                ]
            })

        # Save to Memory MCP
        if entities:
            saved_count = await self._create_entities(entities)
            await self.emit({
                "type": "knowledge.saved",
                "project_id": project_id,
                "saved_count": saved_count,
                "source": "project_analysis"
            })

    async def _save_knowledge_points(
        self,
        knowledge_points: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Save knowledge points to Memory MCP as entities

        Args:
            knowledge_points: List of knowledge point dictionaries (may contain graph_id)

        Returns:
            List of saved knowledge IDs
        """
        if not self._kg_available and not self._mcp_available:
            # Fallback to in-memory store only if both backends unavailable
            return self._save_to_fallback(knowledge_points)

        saved_ids = []
        entities = []

        for kp in knowledge_points:
            kp_id = kp.get("id")
            if not kp_id:
                continue

            # Convert knowledge point to MCP entity format
            entity = {
                "name": kp.get("title", "Unknown"),
                "entityType": "Knowledge",
                "observations": [
                    kp.get("content", ""),
                    f"Source: {kp.get('source', 'unknown')}",
                    f"Session: {kp.get('session_id', '')}",
                    f"Timestamp: {kp.get('timestamp', datetime.now().isoformat())}"
                ],
                "graph_id": kp.get("graph_id")  # 传递 graph_id
            }
            entities.append(entity)
            saved_ids.append(kp_id)

        # Call Memory MCP create_entities
        if entities:
            await self._create_entities(entities)

        return saved_ids

    async def _create_entities(self, entities: List[Dict[str, Any]]) -> int:
        """
        Create entities with automatic fallback

        Priority: PostgreSQL/LocalKG -> MCP -> Memory

        Args:
            entities: List of entity dictionaries (may contain graph_id)

        Returns:
            Number of entities created
        """
        # Try knowledge graph first (PostgreSQL or SQLite)
        if self._kg_available:
            try:
                if isinstance(self._knowledge_graph, PostgresKnowledgeGraph):
                    # PostgreSQL async API
                    count = 0
                    for entity in entities:
                        await self._knowledge_graph.create_entity(
                            name=entity.get("name"),
                            entity_type=entity.get("entityType", "Knowledge"),
                            observations=entity.get("observations", []),
                            metadata=entity.get("metadata"),
                            graph_id=entity.get("graph_id")  # 传递 graph_id
                        )
                        count += 1
                    logger.info(f"Created {count} entities in PostgreSQL")
                    return count
                else:
                    # LocalKnowledgeGraph sync API (不支持 graph_id)
                    count = self._knowledge_graph.create_entities(entities)
                    logger.info(f"Created {count} entities in LocalKG")
                    return count
            except Exception as e:
                logger.warning(f"Knowledge graph failed: {e}, trying MCP fallback")

        # Fallback to MCP
        if self._mcp_available:
            try:
                count = await self._mcp_adapter.create_entities(entities)
                logger.info(f"Created {count} entities via MCP Memory")
                return count
            except Exception as e:
                logger.warning(f"MCP Memory failed: {e}, using in-memory fallback")

        # Final fallback: in-memory store
        for entity in entities:
            entity_name = entity.get("name")
            self._fallback_store[entity_name] = entity
        logger.info(f"Created {len(entities)} entities in fallback store")
        return len(entities)

    def _save_to_fallback(self, knowledge_points: List[Dict[str, Any]]) -> List[str]:
        """Save to in-memory fallback store"""
        saved_ids = []

        for kp in knowledge_points:
            kp_id = kp.get("id")
            if not kp_id:
                continue

            self._fallback_store[kp_id] = {
                "id": kp_id,
                "title": kp.get("title", ""),
                "content": kp.get("content", ""),
                "source": kp.get("source", "unknown"),
                "session_id": kp.get("session_id", ""),
                "timestamp": kp.get("timestamp", datetime.now().isoformat()),
                "saved_at": datetime.now().isoformat()
            }

            saved_ids.append(kp_id)

        return saved_ids

    async def search_knowledge(self, query: str) -> Dict[str, Any]:
        """
        Search knowledge with automatic fallback

        Priority: PostgreSQL/LocalKG -> MCP -> Memory

        Args:
            query: Search query

        Returns:
            Search results with caching metadata
        """
        # Try knowledge graph first
        if self._kg_available:
            try:
                if isinstance(self._knowledge_graph, PostgresKnowledgeGraph):
                    # PostgreSQL semantic search
                    results = await self._knowledge_graph.search_entities(query, limit=10)
                    return {
                        "nodes": results,
                        "source": "postgres",
                        "_meta": {
                            "ttlMs": 3600000,  # Cache for 1 hour
                            "cacheScope": "user"
                        }
                    }
                else:
                    # LocalKG vector/keyword search
                    results = self._knowledge_graph.search_nodes(query, limit=10)
                    return {
                        "nodes": results,
                        "source": "local_kg",
                        "_meta": {
                            "ttlMs": 3600000,
                            "cacheScope": "user"
                        }
                    }
            except Exception as e:
                logger.warning(f"Knowledge graph search failed: {e}, trying MCP")

        # Fallback to MCP
        if self._mcp_available:
            try:
                nodes = await self._mcp_adapter.search_nodes(query)
                return {
                    "nodes": nodes,
                    "source": "memory_mcp",
                    "_meta": {
                        "ttlMs": 3600000,
                        "cacheScope": "user"
                    }
                }
            except Exception as e:
                logger.warning(f"MCP Memory search failed: {e}, using fallback")

        # Final fallback: in-memory search
        results = self._search_fallback(query)
        return {
            "nodes": results,
            "source": "fallback",
            "_meta": {"ttlMs": 0}
        }

    def _search_fallback(self, query: str) -> List[Dict[str, Any]]:
        """Search in fallback store"""
        results = []
        query_lower = query.lower()

        for kp in self._fallback_store.values():
            title = kp.get("title", "").lower() if isinstance(kp.get("title"), str) else ""
            content = kp.get("content", "").lower() if isinstance(kp.get("content"), str) else ""
            name = kp.get("name", "").lower() if isinstance(kp.get("name"), str) else ""

            if query_lower in title or query_lower in content or query_lower in name:
                results.append(kp)

        return results

    def get_knowledge_point(self, kp_id: str) -> Dict[str, Any] | None:
        """
        Retrieve a knowledge point by ID

        Args:
            kp_id: Knowledge point ID

        Returns:
            Knowledge point dictionary or None if not found
        """
        return self._fallback_store.get(kp_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory store statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_knowledge_points": len(self._fallback_store),
            "store_size_kb": len(str(self._fallback_store)) / 1024,
            "mcp_available": self._mcp_available,
            "source": "memory_mcp" if self._mcp_available else "fallback"
        }

    async def link_knowledge_nodes(
        self,
        from_node: str,
        to_node: str,
        relation_type: str
    ) -> bool:
        """
        建立知识节点之间的关系

        Priority: PostgreSQL/LocalKG -> MCP -> Fail

        Args:
            from_node: 源节点名称
            to_node: 目标节点名称
            relation_type: 关系类型 (requires/related_to/belongs_to)

        Returns:
            是否成功建立关系
        """
        # Try knowledge graph first
        if self._kg_available:
            try:
                if isinstance(self._knowledge_graph, PostgresKnowledgeGraph):
                    await self._knowledge_graph.create_relation(
                        from_entity=from_node,
                        to_entity=to_node,
                        relation_type=relation_type
                    )
                    logger.info(f"Created relation in PostgreSQL: {from_node} --{relation_type}--> {to_node}")
                    return True
                else:
                    relations = [{
                        "from": from_node,
                        "to": to_node,
                        "relationType": relation_type
                    }]
                    count = self._knowledge_graph.create_relations(relations)
                    logger.info(f"Created {count} relation(s) in LocalKG")
                    return count > 0
            except Exception as e:
                logger.warning(f"Knowledge graph relation creation failed: {e}, trying MCP")

        # Fallback to MCP
        if self._mcp_available:
            try:
                relations = [{
                    "from": from_node,
                    "to": to_node,
                    "relationType": relation_type
                }]
                await self._mcp_adapter.create_relations(relations)
                logger.info(f"Created relation via MCP: {from_node} --{relation_type}--> {to_node}")
                return True
            except Exception as e:
                logger.error(f"MCP relation creation failed: {e}")

        logger.warning("All backends unavailable, cannot create relations")
        return False

    async def get_knowledge_graph(
        self,
        node_name: str = None
    ) -> Dict[str, Any]:
        """
        获取知识图谱（指定节点的子图或全图）

        Priority: PostgreSQL/LocalKG -> MCP -> Memory

        Args:
            node_name: 中心节点名称（None = 全图）

        Returns:
            {
                "entities": [...],
                "relations": [...]
            }
        """
        # Try knowledge graph first
        if self._kg_available:
            try:
                if isinstance(self._knowledge_graph, PostgresKnowledgeGraph):
                    # PostgreSQL API
                    if node_name:
                        entity = await self._knowledge_graph.get_entity(node_name)
                        relations = await self._knowledge_graph.get_relations(node_name)
                        return {
                            "entities": [entity] if entity else [],
                            "relations": relations,
                            "source": "postgres"
                        }
                    else:
                        entities = await self._knowledge_graph.get_all_entities(limit=100)
                        return {
                            "entities": entities,
                            "relations": [],  # TODO: fetch all relations
                            "source": "postgres"
                        }
                else:
                    # LocalKG API
                    if node_name:
                        nodes = self._knowledge_graph.open_nodes([node_name])
                        return {
                            "entities": nodes,
                            "relations": [],
                            "source": "local_kg"
                        }
                    else:
                        graph = self._knowledge_graph.read_graph()
                        return {
                            **graph,
                            "source": "local_kg"
                        }
            except Exception as e:
                logger.warning(f"Knowledge graph read failed: {e}, trying MCP")

        # Fallback to MCP
        if self._mcp_available:
            try:
                if node_name:
                    nodes = await self._mcp_adapter.open_nodes([node_name])
                    return {
                        "entities": nodes,
                        "relations": self._extract_relations(nodes),
                        "source": "memory_mcp"
                    }
                else:
                    graph = await self._mcp_adapter.read_graph()
                    return {
                        **graph,
                        "source": "memory_mcp"
                    }
            except Exception as e:
                logger.warning(f"MCP graph read failed: {e}")

        # Final fallback
        return {
            "entities": list(self._fallback_store.values()),
            "relations": [],
            "source": "fallback"
        }

    def _extract_relations(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从节点数据中提取关系列表"""
        relations = []
        for node in nodes:
            node_relations = node.get("relations", [])
            for rel in node_relations:
                relations.append({
                    "from": node.get("name"),
                    "to": rel.get("to"),
                    "type": rel.get("type")
                })
        return relations

    async def delete_nodes(self, node_ids: List[str]) -> int:
        """
        删除知识节点

        Args:
            node_ids: 要删除的节点ID列表

        Returns:
            成功删除的节点数量
        """
        if not self._mcp_available:
            # Fallback: 从内存中删除
            deleted_count = 0
            for node_id in node_ids:
                if node_id in self._fallback_store:
                    del self._fallback_store[node_id]
                    deleted_count += 1
            logger.info(f"从 fallback store 删除了 {deleted_count} 个节点")
            return deleted_count

        try:
            # 调用 MCP Memory 删除
            await self._mcp_adapter.delete_entities(node_ids)
            logger.info(f"通过 MCP Memory 删除了 {len(node_ids)} 个节点")
            return len(node_ids)
        except Exception as e:
            logger.error(f"删除节点失败: {e}")
            # Fallback 删除
            deleted_count = 0
            for node_id in node_ids:
                if node_id in self._fallback_store:
                    del self._fallback_store[node_id]
                    deleted_count += 1
            return deleted_count
