"""
Memory Manager Agent
Manages knowledge storage and retrieval using Memory MCP Server
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_agent import BaseAgent


class MemoryManager(BaseAgent):
    """
    Manages knowledge points and integrates with Memory MCP.

    Subscribes to: knowledge.extracted, project.analysis_completed
    Emits: knowledge.saved, knowledge.search_completed

    Memory MCP Integration:
    - Uses mcp__plugin_ecc_memory tools for knowledge graph operations
    - Supports entity creation, relation creation, and node search
    - Caches search results for 1 hour (per MCP caching strategy)
    """

    def __init__(self, agent_id: str, bus, mcp_tools: Optional[Dict] = None):
        super().__init__(agent_id, bus)
        # MCP tools for memory operations (injected from server)
        self._mcp_tools = mcp_tools or {}
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
        self._mcp_available = await self._check_mcp_availability()

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

        # Save knowledge points
        saved_ids = await self._save_knowledge_points(knowledge_points)

        # Emit knowledge saved event
        await self.emit({
            "type": "knowledge.saved",
            "session_id": session_id,
            "saved_count": len(saved_ids),
            "knowledge_ids": saved_ids
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
            return 0

        try:
            # Call mcp__plugin_ecc_memory__create_entities
            create_entities_tool = self._mcp_tools.get("mcp__plugin_ecc_memory__create_entities")
            if create_entities_tool:
                result = await create_entities_tool(entities=entities)
                return len(entities)
            else:
                # Fallback: store in memory
                for entity in entities:
                    entity_name = entity.get("name")
                    self._fallback_store[entity_name] = entity
                return len(entities)
        except Exception as e:
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
            # Call mcp__plugin_ecc_memory__search_nodes
            search_nodes_tool = self._mcp_tools.get("mcp__plugin_ecc_memory__search_nodes")
            if search_nodes_tool:
                result = await search_nodes_tool(query=query)
                return {
                    "nodes": result,
                    "source": "memory_mcp",
                    "_meta": {
                        "ttlMs": 3600000,  # Cache for 1 hour
                        "cacheScope": "user"
                    }
                }
            else:
                # Fallback
                results = self._search_fallback(query)
                return {
                    "nodes": results,
                    "source": "fallback",
                    "_meta": {"ttlMs": 0}
                }
        except Exception as e:
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

    async def _check_mcp_availability(self) -> bool:
        """
        Check if Memory MCP tools are available

        Returns:
            True if MCP is available, False otherwise
        """
        required_tools = [
            "mcp__plugin_ecc_memory__create_entities",
            "mcp__plugin_ecc_memory__search_nodes"
        ]

        for tool in required_tools:
            if tool not in self._mcp_tools:
                return False

        return True

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
