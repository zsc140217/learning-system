"""
MCP Protocol Core
JSON-RPC 2.0 implementation with _meta field support
"""

from typing import Any, Dict, Callable, Optional
from dataclasses import dataclass

from .result_types import MCPResult, MCPError


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 Request"""
    jsonrpc: str
    method: str
    params: Dict[str, Any]
    id: Optional[int | str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONRPCRequest":
        """Parse JSON-RPC request from dict"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data["method"],
            params=data.get("params", {}),
            id=data.get("id")
        )


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 Response"""
    jsonrpc: str
    id: Optional[int | str]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        response = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }

        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result

        if self.meta:
            response["_meta"] = self.meta

        return response


class MCPServer:
    """
    MCP Server with JSON-RPC 2.0 support

    Usage:
        server = MCPServer("Learning System")

        @server.tool("analyze_session")
        async def analyze_session(session_data: str) -> MCPResult:
            return MCPResult(data={"status": "ok"})

        await server.handle_request(request_json)
    """

    def __init__(self, name: str):
        self.name = name
        self.tools: Dict[str, Callable] = {}
        self.resources: Dict[str, Callable] = {}

    def tool(self, name: str):
        """
        Decorator to register a tool

        Usage:
            @server.tool("my_tool")
            async def my_tool(param: str) -> MCPResult:
                return MCPResult(data={"result": "ok"})
        """
        def decorator(func: Callable):
            self.tools[name] = func
            return func
        return decorator

    def resource(self, uri: str):
        """
        Decorator to register a resource

        Usage:
            @server.resource("knowledge://graph")
            async def get_graph() -> str:
                return "graph data"
        """
        def decorator(func: Callable):
            self.resources[uri] = func
            return func
        return decorator

    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC request

        Args:
            request_data: Parsed JSON request

        Returns:
            JSON-RPC response dict
        """
        try:
            request = JSONRPCRequest.from_dict(request_data)

            # Route request
            if request.method == "tools/call":
                result = await self._handle_tool_call(request)
            elif request.method == "tools/list":
                result = await self._handle_tool_list(request)
            elif request.method == "resources/read":
                result = await self._handle_resource_read(request)
            elif request.method == "resources/list":
                result = await self._handle_resource_list(request)
            else:
                raise MCPError(f"Unknown method: {request.method}", code=-32601)

            # Build response
            if isinstance(result, MCPResult):
                return JSONRPCResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    result=result.data,
                    meta=result.meta
                ).to_dict()
            else:
                return JSONRPCResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    result=result
                ).to_dict()

        except MCPError as e:
            return JSONRPCResponse(
                jsonrpc="2.0",
                id=request_data.get("id"),
                error={
                    "code": e.code,
                    "message": e.message
                }
            ).to_dict()

        except Exception as e:
            return JSONRPCResponse(
                jsonrpc="2.0",
                id=request_data.get("id"),
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            ).to_dict()

    async def _handle_tool_call(self, request: JSONRPCRequest) -> Any:
        """Handle tools/call request"""
        tool_name = request.params.get("name")
        tool_params = request.params.get("arguments", {})

        if tool_name not in self.tools:
            raise MCPError(f"Tool not found: {tool_name}", code=-32602)

        tool_func = self.tools[tool_name]
        result = await tool_func(**tool_params)

        return result

    async def _handle_tool_list(self, request: JSONRPCRequest) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools_list = [
            {
                "name": name,
                "description": func.__doc__ or "No description"
            }
            for name, func in self.tools.items()
        ]

        return {"tools": tools_list}

    async def _handle_resource_read(self, request: JSONRPCRequest) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = request.params.get("uri")

        if uri not in self.resources:
            raise MCPError(f"Resource not found: {uri}", code=-32602)

        resource_func = self.resources[uri]
        content = await resource_func()

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": content
                }
            ]
        }

    async def _handle_resource_list(self, request: JSONRPCRequest) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources_list = [
            {
                "uri": uri,
                "name": uri.split("://")[1] if "://" in uri else uri,
                "description": func.__doc__ or "No description"
            }
            for uri, func in self.resources.items()
        ]

        return {"resources": resources_list}
