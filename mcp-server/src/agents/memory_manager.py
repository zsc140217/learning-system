"""
Memory Manager Agent
Manages knowledge storage and retrieval using Memory MCP Server
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from .base_agent import BaseAgent
from ..storage.mcp_memory_adapter import MCPMemoryAdapter


class MemoryManager(BaseAgent):
    """
    Manages knowledge points and integrates with Memory MCP.

    Subscribes to: knowledge.extracted, project.analysis_completed
    Emits: knowledge.saved, knowledge.search_completed

    Memory MCP Integration:
    - Uses MCPMemoryAdapter for type-safe knowledge graph operations
    - Supports entity creation, relation creation, and node search
    - Caches search results for 1 hour (per MCP caching strategy)
    """

    def __init__(self, agent_id: str, bus, mcp_tools: Optional[Dict] = None):
        super().__init__(agent_id, bus)
        # MCP Memory Adapter (封装所有 MCP Memory 操作)
        self._mcp_adapter = MCPMemoryAdapter(mcp_tools or {})
        # In-memory fallback store when MCP is unavailable
        self._fallback_store: Dict[str, Dict[str, Any]] = {}
        # Cache for MCP availability check
        self._mcp_available: Optional[bool] = None

    async def start(self) -> None:
        """Start the manager and subscribe to knowledge events"""
        await super().start()
        await self.subscribe("knowledge.extracted")
        await self.subscribe("project.analysis_completed")

        # Check MCP availability on startup
        self._mcp_available = self._mcp_adapter.available
        logger.info(f"MemoryManager started, MCP available: {self._mcp_available}")

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
            knowledge_points: List of knowledge point dictionaries

        Returns:
            List of saved knowledge IDs
        """
        if not self._mcp_available:
            # Fallback to in-memory store
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
                ]
            }
            entities.append(entity)
            saved_ids.append(kp_id)

        # Call Memory MCP create_entities
        if entities:
            await self._create_entities(entities)

        return saved_ids

    async def _create_entities(self, entities: List[Dict[str, Any]]) -> int:
        """
        Create entities in Memory MCP

        Args:
            entities: List of entity dictionaries

        Returns:
            Number of entities created
        """
        if not self._mcp_available:
            # Fallback: store in memory
            for entity in entities:
                entity_name = entity.get("name")
                self._fallback_store[entity_name] = entity
            return len(entities)

        try:
            # Use adapter to create entities
            count = await self._mcp_adapter.create_entities(entities)
            logger.info(f"Created {count} entities via MCP Memory")
            return count
        except Exception as e:
            logger.warning(f"MCP Memory failed, using fallback: {e}")
            # Fallback on error
            for entity in entities:
                entity_name = entity.get("name")
                self._fallback_store[entity_name] = entity
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
        Search knowledge using Memory MCP

        Args:
            query: Search query

        Returns:
            Search results with caching metadata
        """
        if not self._mcp_available:
            # Fallback to in-memory search
            results = self._search_fallback(query)
            return {
                "nodes": results,
                "source": "fallback",
                "_meta": {
                    "ttlMs": 0  # Don't cache fallback results
                }
            }

        try:
            # Use adapter to search nodes
            nodes = await self._mcp_adapter.search_nodes(query)
            return {
                "nodes": nodes,
                "source": "memory_mcp",
                "_meta": {
                    "ttlMs": 3600000,  # Cache for 1 hour
                    "cacheScope": "user"
                }
            }
        except Exception as e:
            logger.warning(f"MCP Memory search failed, using fallback: {e}")
            # Fallback on error
            results = self._search_fallback(query)
            return {
                "nodes": results,
                "source": "fallback_error",
                "error": str(e),
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

        Args:
            from_node: 源节点名称
            to_node: 目标节点名称
            relation_type: 关系类型 (requires/related_to/belongs_to)

        Returns:
            是否成功建立关系
        """
        if not self._mcp_available:
            logger.warning("MCP not available, cannot create relations")
            return False

        try:
            relations = [{
                "from": from_node,
                "to": to_node,
                "relationType": relation_type
            }]

            await self._mcp_adapter.create_relations(relations)
            logger.info(f"Created relation: {from_node} --{relation_type}--> {to_node}")
            return True
        except Exception as e:
            logger.error(f"Failed to create relation: {e}")
            return False

    async def get_knowledge_graph(
        self,
        node_name: str = None
    ) -> Dict[str, Any]:
        """
        获取知识图谱（指定节点的子图或全图）

        Args:
            node_name: 中心节点名称（None = 全图）

        Returns:
            {
                "entities": [...],
                "relations": [...]
            }
        """
        if not self._mcp_available:
            logger.warning("MCP not available, returning fallback data")
            return {
                "entities": list(self._fallback_store.values()),
                "relations": [],
                "source": "fallback"
            }

        try:
            if node_name:
                # 获取特定节点及其关系
                nodes = await self._mcp_adapter.open_nodes([node_name])
                return {
                    "entities": nodes,
                    "relations": self._extract_relations(nodes),
                    "source": "memory_mcp"
                }
            else:
                # 获取完整图谱
                graph = await self._mcp_adapter.read_graph()
                return {
                    **graph,
                    "source": "memory_mcp"
                }
        except Exception as e:
            logger.error(f"Failed to get knowledge graph: {e}")
            return {
                "entities": list(self._fallback_store.values()),
                "relations": [],
                "source": "fallback_error",
                "error": str(e)
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
