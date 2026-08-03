"""Session capture hook for recording MCP interactions."""

import time
from typing import Dict, Any

from .base import Hook, HookContext
from ..storage import ObservationStore


class SessionCaptureHook(Hook):
    """Captures all MCP requests and responses to observations.jsonl."""

    def __init__(self, store: ObservationStore):
        self.store = store

    async def on_request(self, context: HookContext) -> None:
        """Record timestamp when request arrives."""
        context.timestamp = time.time()

    async def on_response(self, context: HookContext) -> None:
        """Record the complete request-response pair."""
        duration = time.time() - context.timestamp if context.timestamp else 0

        observation = {
            "type": "mcp_interaction",
            "request": {
                "method": context.request.get("method"),
                "params": context.request.get("params", {})
            },
            "response": self._sanitize_response(context.response),
            "error": str(context.error) if context.error else None,
            "duration_ms": int(duration * 1000)
        }

        await self.store.append(observation)

    def _sanitize_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize response for storage (remove large payloads)."""
        if not response:
            return {}

        sanitized = {
            "success": "error" not in response
        }

        # Include result metadata but truncate large data
        if "result" in response:
            result = response["result"]
            if isinstance(result, dict):
                # Keep small results, summarize large ones
                if len(str(result)) < 1000:
                    sanitized["result"] = result
                else:
                    sanitized["result"] = {
                        "_summary": "Large response truncated",
                        "_size": len(str(result))
                    }

        return sanitized
