"""JSONL-based observation storage."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class ObservationStore:
    """Manages reading and writing observations to JSONL file."""

    def __init__(self, file_path: str = "mcp-server/data/observations.jsonl"):
        self.file_path = Path(file_path)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create data directory if it doesn't exist."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    async def append(self, observation: Dict[str, Any]) -> None:
        """Append an observation to the JSONL file.

        Args:
            observation: Observation data to store
        """
        # Add timestamp if not present
        if "timestamp" not in observation:
            observation["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Append to file
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(observation, ensure_ascii=False) + "\n")

    async def read_all(self) -> List[Dict[str, Any]]:
        """Read all observations from the JSONL file.

        Returns:
            List of observation dictionaries
        """
        if not self.file_path.exists():
            return []

        observations = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    observations.append(json.loads(line))

        return observations

    async def read_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Read the most recent observations.

        Args:
            limit: Maximum number of observations to return

        Returns:
            List of recent observation dictionaries
        """
        all_observations = await self.read_all()
        return all_observations[-limit:] if all_observations else []

    async def clear(self) -> None:
        """Clear all observations (useful for testing)."""
        if self.file_path.exists():
            os.remove(self.file_path)
