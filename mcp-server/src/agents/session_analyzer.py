"""
Session Analyzer Agent
Analyzes learning session transcripts and extracts knowledge points
"""
from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent
from ..utils.id_generator import generate_knowledge_id


class SessionAnalyzer(BaseAgent):
    """
    Analyzes completed learning sessions and extracts knowledge points.

    Subscribes to: session.completed
    Emits: knowledge.extracted
    """

    async def start(self) -> None:
        """Start the analyzer and subscribe to session events"""
        await super().start()
        await self.subscribe("session.completed")

    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process session completed events and extract knowledge

        Args:
            event: Event containing session_id and transcript
        """
        event_type = event.get("type")

        # Only process session.completed events
        if event_type != "session.completed":
            return

        session_id = event.get("session_id")
        transcript = event.get("transcript", [])

        # Extract knowledge points from transcript
        knowledge_points = self._extract_knowledge_points(session_id, transcript)

        # Emit knowledge extracted event
        await self.emit({
            "type": "knowledge.extracted",
            "session_id": session_id,
            "knowledge_points": knowledge_points
        })

    def _extract_knowledge_points(
        self,
        session_id: str,
        transcript: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Extract knowledge points from session transcript

        Args:
            session_id: Session identifier
            transcript: List of messages with role and content

        Returns:
            List of knowledge point dictionaries
        """
        if not transcript:
            return []

        knowledge_points = []

        # Simple extraction: look for assistant responses with technical content
        for message in transcript:
            if message.get("role") == "assistant":
                content = message.get("content", "").strip()

                # Skip empty or very short responses
                if len(content) < 20:
                    continue

                # Extract as knowledge point
                knowledge_point = {
                    "id": generate_knowledge_id(),
                    "title": self._generate_title(content),
                    "content": content,
                    "source": "session",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                knowledge_points.append(knowledge_point)

        return knowledge_points

    def _generate_title(self, content: str) -> str:
        """
        Generate a title from content (first sentence or first N chars)

        Args:
            content: Full content text

        Returns:
            Generated title
        """
        # Take first sentence or first 50 characters
        first_sentence = content.split('.')[0].strip()

        if len(first_sentence) > 50:
            return first_sentence[:47] + "..."

        return first_sentence
