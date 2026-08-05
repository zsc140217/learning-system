"""
HTTP Transport for MCP 2026-07-28
Stateless request/response model
"""
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
import json

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger


@dataclass
class MCPRequest:
    """Parsed MCP request"""
    jsonrpc: str
    method: str
    params: Dict[str, Any]
    id: int

    # MCP 2026 metadata
    protocol_version: Optional[str] = None
    client_info: Optional[Dict[str, Any]] = None

    @classmethod
    def from_http(cls, body: Dict[str, Any], headers: Dict[str, str]) -> "MCPRequest":
        """Parse HTTP request to MCPRequest"""
        # Extract metadata
        meta = body.get("params", {}).get("_meta", {})
        client_info = meta.get("io.modelcontextprotocol/clientInfo")

        return cls(
            jsonrpc=body.get("jsonrpc", "2.0"),
            method=body["method"],
            params=body.get("params", {}),
            id=body.get("id", 0),
            protocol_version=headers.get("mcp-protocol-version"),
            client_info=client_info
        )


@dataclass
class MCPResponse:
    """MCP response following 2026-07-28 spec"""
    jsonrpc: str = "2.0"
    id: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
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


class HTTPTransport:
    """
    HTTP Transport Layer for MCP 2026-07-28

    Features:
    - Stateless request/response
    - MRTR (Multi Round-Trip Request) support
    - Tasks extension support
    - MCP Apps UI template support
    """

    def __init__(self, mcp_server):
        """
        Initialize HTTP transport

        Args:
            mcp_server: MCPServer instance
        """
        self.mcp_server = mcp_server
        self.app = FastAPI(title="MCP 2026 HTTP Server")

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register FastAPI routes"""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "protocol": "MCP 2026-07-28",
                "server": self.mcp_server.name
            }

        @self.app.post("/jsonrpc")
        async def handle_jsonrpc(request: Request):
            """
            Main JSON-RPC endpoint

            Handles:
            - tools/list
            - tools/call
            - resources/list
            - resources/read
            - prompts/list
            - prompts/get
            """
            try:
                # Parse request
                body = await request.json()
                headers = dict(request.headers)

                mcp_request = MCPRequest.from_http(body, headers)

                logger.info(f"[HTTP] {mcp_request.method}")
                logger.debug(f"Headers: {headers}")
                logger.debug(f"Body: {json.dumps(body, indent=2, ensure_ascii=False)}")

                # Route to handler
                if mcp_request.method == "tools/list":
                    result = await self._handle_tools_list()
                elif mcp_request.method == "tools/call":
                    # Extract tool name from params
                    tool_name = mcp_request.params.get("name")
                    if not tool_name:
                        raise HTTPException(status_code=400, detail="Missing 'name' in params")
                    tool_args = mcp_request.params.get("arguments", {})
                    result = await self._handle_tool_call(tool_name, tool_args)
                elif mcp_request.method == "resources/list":
                    result = await self._handle_resources_list()
                elif mcp_request.method.startswith("resources/"):
                    result = await self._handle_resource_read(mcp_request.params)
                elif mcp_request.method == "prompts/list":
                    result = await self._handle_prompts_list()
                elif mcp_request.method == "prompts/get":
                    result = await self._handle_prompt_get(mcp_request.params)
                else:
                    return JSONResponse(
                        status_code=400,
                        content=MCPResponse(
                            id=mcp_request.id,
                            error={"code": -32601, "message": f"Method not found: {mcp_request.method}"}
                        ).to_dict()
                    )

                # Build response
                response = MCPResponse(
                    id=mcp_request.id,
                    result=result.data if hasattr(result, "data") else result,
                    meta=result.meta if hasattr(result, "meta") else {}
                )

                return JSONResponse(content=response.to_dict())

            except Exception as e:
                logger.error(f"Request handling error: {e}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content=MCPResponse(
                        id=0,
                        error={"code": -32603, "message": str(e)}
                    ).to_dict()
                )

    async def _handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = []
        for tool_name, tool_info in self.mcp_server.tools.items():
            tools.append({
                "name": tool_name,
                "description": tool_info.get("description", ""),
                "inputSchema": tool_info.get("input_schema", {})
            })

        return {
            "tools": tools
        }

    async def _handle_tool_call(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Handle tools/call request

        Returns:
            MCPResult or TaskHandleResult
        """
        # Remove _meta from params before passing to tool
        tool_params = {k: v for k, v in params.items() if k != "_meta"}

        # Get tool handler
        tool_info = self.mcp_server.tools.get(tool_name)
        if not tool_info:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

        handler = tool_info["handler"]

        # Call tool
        result = await handler(**tool_params)

        return result

    async def _handle_resources_list(self) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources = []
        for uri, info in self.mcp_server.resources.items():
            resources.append({
                "uri": uri,
                "name": info.get("name", uri),
                "description": info.get("description", ""),
                "mimeType": info.get("mime_type", "text/plain")
            })

        return {
            "resources": resources
        }

    async def _handle_resource_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        if not uri:
            raise HTTPException(status_code=400, detail="Missing uri parameter")

        resource_info = self.mcp_server.resources.get(uri)
        if not resource_info:
            raise HTTPException(status_code=404, detail=f"Resource not found: {uri}")

        handler = resource_info["handler"]
        content = await handler()

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource_info.get("mime_type", "text/plain"),
                    "text": content
                }
            ]
        }

    async def _handle_prompts_list(self) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts = []
        for name, info in self.mcp_server.prompts.items():
            prompts.append({
                "name": name,
                "description": info.get("description", ""),
                "arguments": info.get("arguments", [])
            })

        return {
            "prompts": prompts
        }

    async def _handle_prompt_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        name = params.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Missing name parameter")

        prompt_info = self.mcp_server.prompts.get(name)
        if not prompt_info:
            raise HTTPException(status_code=404, detail=f"Prompt not found: {name}")

        handler = prompt_info["handler"]
        result = await handler(params.get("arguments", {}))

        return {
            "description": prompt_info.get("description", ""),
            "messages": result
        }

    def get_app(self) -> FastAPI:
        """Get FastAPI application instance"""
        return self.app
