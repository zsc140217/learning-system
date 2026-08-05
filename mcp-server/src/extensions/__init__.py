"""
MCP Extensions Framework

Dynamic tool registration based on client capabilities.
"""

from .base_extension import Extension
from .extension_manager import ExtensionManager

__all__ = ["Extension", "ExtensionManager"]
