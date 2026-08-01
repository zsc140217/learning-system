"""
Memory Manager Agent
Manages knowledge storage and retrieval
"""
from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent


class MemoryManager(BaseAgent):
    """
    Manages knowledge points and integrates with Memory MCP.

    Subscribes to: knowledge.extracted
    Emits: knowledge.saved
    """

    def __init__(self, agent_id: str, bus):
        super().__init__(agent_id, bus)
        # In-memory knowledge store (will be replaced with Memory MCP SDK)
        self._knowledge_store: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        """Start the manager and subscribe to knowledge events"""
        await super().start()
        await self.subscribe("knowledge.extracted")

    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process knowledge extracted events and save to memory

        Args:
            event: Event containing session_id and knowledge_points
        """
        event_type = event.get("type")

        # Only process knowledge.extracted events
        if event_type != "knowledge.extracted":
            return

        session_id = event.get("session_id")
        knowledge_points = event.get("knowledge_points", [])

        # Save knowledge points
        saved_ids = self._save_knowledge_points(knowledge_points)

        # Emit knowledge saved event
        await self.emit({
            "type": "knowledge.saved",
            "session_id": session_id,
            "saved_count": len(saved_ids),
            "knowledge_ids": saved_ids
        })

    def _save_knowledge_points(
        self,
        knowledge_points: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Save knowledge points to memory store

        Args:
            knowledge_points: List of knowledge point dictionaries

        Returns:
            List of saved knowledge IDs
        """
        saved_ids = []

        for kp in knowledge_points:
            kp_id = kp.get("id")
            if not kp_id:
                continue

            # Store in memory (simple implementation)
            self._knowledge_store[kp_id] = {
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

    def get_knowledge_point(self, kp_id: str) -> Dict[str, Any] | None:
        """
        Retrieve a knowledge point by ID

        Args:
            kp_id: Knowledge point ID

        Returns:
            Knowledge point dictionary or None if not found
        """
        return self._knowledge_store.get(kp_id)

    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """
        Simple search in knowledge store

        Args:
            query: Search query

        Returns:
            List of matching knowledge points
        """
        results = []
        query_lower = query.lower()

        for kp in self._knowledge_store.values():
            title = kp.get("title", "").lower()
            content = kp.get("content", "").lower()

            if query_lower in title or query_lower in content:
                results.append(kp)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory store statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_knowledge_points": len(self._knowledge_store),
            "store_size_kb": len(str(self._knowledge_store)) / 1024
        }
