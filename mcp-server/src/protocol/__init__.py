"""
MCP Protocol Core Layer
Implements JSON-RPC 2.0 with _meta field support
"""

from .mcp_protocol import MCPServer, JSONRPCRequest, JSONRPCResponse
from .result_types import (
    MCPResult,
    InputRequiredResult,
    TaskHandleResult,
    UITemplateResult,
    MCPError
)
from .transport import StdioTransport, SSETransport

__all__ = [
    "MCPServer",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "MCPResult",
    "InputRequiredResult",
    "TaskHandleResult",
    "UITemplateResult",
    "MCPError",
    "StdioTransport",
    "SSETransport",
]
