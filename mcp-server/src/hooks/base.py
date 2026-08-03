"""Base classes for the Hook system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class HookContext:
    """Context passed to hooks containing request/response data."""

    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    timestamp: Optional[float] = None


class Hook(ABC):
    """Abstract base class for all hooks."""

    @abstractmethod
    async def on_request(self, context: HookContext) -> None:
        """Called before processing a request.

        Args:
            context: Hook context with request data
        """
        pass

    @abstractmethod
    async def on_response(self, context: HookContext) -> None:
        """Called after processing a request.

        Args:
            context: Hook context with request and response data
        """
        pass
