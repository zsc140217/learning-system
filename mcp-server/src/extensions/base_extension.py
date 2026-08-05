"""
Base Extension Abstract Class

This module defines the abstract base class for all MCP extensions.
Extensions allow dynamic tool registration based on client capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class Extension(ABC):
    """
    Abstract base class for MCP extensions.

    Extensions follow the capability negotiation pattern:
    1. Client declares supported extensions
    2. Server matches and loads compatible extensions
    3. Extension registers its tools dynamically
    """

    def __init__(self):
        self._enabled = False
        self._server = None

    @property
    @abstractmethod
    def extension_id(self) -> str:
        """
        Unique extension identifier (reverse domain notation).

        Example: "io.learning-system.analyzer.python"
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Extension version following semantic versioning.

        Example: "1.0.0"
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable extension name.

        Example: "Python Code Analyzer"
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Brief description of extension functionality.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Return extension capabilities for negotiation.

        Returns:
            Dictionary describing extension features and capabilities

        Example:
            {
                "analyze_decorators": True,
                "detect_framework": ["FastAPI", "Django", "Flask"],
                "extract_type_hints": True,
                "supported_python_versions": ["3.8", "3.9", "3.10", "3.11"]
            }
        """
        pass

    @abstractmethod
    def register_tools(self, server: Any):
        """
        Register extension tools with the MCP server.

        Args:
            server: MCP server instance to register tools with

        Example:
            @server.tool("analyze_python_decorators")
            async def analyze_decorators(file_path: str):
                # Tool implementation
                pass
        """
        pass

    def on_enable(self) -> None:
        """
        Hook called when extension is enabled.
        Override for initialization logic.
        """
        logger.info(f"Extension enabled: {self.extension_id} v{self.version}")

    def on_disable(self) -> None:
        """
        Hook called when extension is disabled.
        Override for cleanup logic.
        """
        logger.info(f"Extension disabled: {self.extension_id}")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate extension-specific configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        return True

    @property
    def is_enabled(self) -> bool:
        """Check if extension is currently enabled."""
        return self._enabled

    def enable(self, server: Any) -> None:
        """
        Enable the extension and register its tools.

        Args:
            server: MCP server instance
        """
        if self._enabled:
            logger.warning(f"Extension already enabled: {self.extension_id}")
            return

        self._server = server
        self._enabled = True
        self.register_tools(server)
        self.on_enable()

    def disable(self) -> None:
        """Disable the extension and cleanup."""
        if not self._enabled:
            logger.warning(f"Extension already disabled: {self.extension_id}")
            return

        self._enabled = False
        self._server = None
        self.on_disable()

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return extension metadata for discovery.

        Returns:
            Dictionary with extension information
        """
        return {
            "id": self.extension_id,
            "version": self.version,
            "name": self.display_name,
            "description": self.description,
            "capabilities": self.get_capabilities(),
            "enabled": self.is_enabled
        }
