"""
MCP 2026 CLI Client
Supports MRTR, Tasks, and MCP Apps
"""
import asyncio
import json
from typing import Any, Dict, Optional
from dataclasses import dataclass

import httpx
from loguru import logger


@dataclass
class MCPResponse:
    """MCP Response wrapper"""
    result: Any
    meta: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        """Check if response is successful"""
        return self.error is None

    def is_mrtr(self) -> bool:
        """Check if response requires user input (MRTR)"""
        if not self.meta:
            return False
        return "io.modelcontextprotocol/inputRequired" in self.meta

    def is_task(self) -> bool:
        """Check if response contains task handle"""
        if not self.meta:
            return False
        return "io.modelcontextprotocol/taskHandle" in self.meta

    def is_ui_template(self) -> bool:
        """Check if response contains UI template"""
        if not self.meta:
            return False
        return "io.modelcontextprotocol/uiTemplate" in self.meta

    def get_mrtr_data(self) -> Dict[str, Any]:
        """Extract MRTR data"""
        if not self.is_mrtr():
            return {}
        return self.meta.get("io.modelcontextprotocol/inputRequired", {})

    def get_task_data(self) -> Dict[str, Any]:
        """Extract task data"""
        if not self.is_task():
            return {}
        return self.meta.get("io.modelcontextprotocol/taskHandle", {})

    def get_ui_template_data(self) -> Dict[str, Any]:
        """Extract UI template data"""
        if not self.is_ui_template():
            return {}
        return self.meta.get("io.modelcontextprotocol/uiTemplate", {})


class MCPClient:
    """
    MCP 2026 Protocol Client

    Supports:
    - Standard tool calls
    - MRTR (Multi-Round Trip Request)
    - Tasks with progress tracking
    - MCP Apps UI templates
    """

    def __init__(self, server_url: str = "http://localhost:8080", timeout: float = 30.0):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.request_id = 0
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _next_request_id(self) -> int:
        """Generate next request ID"""
        self.request_id += 1
        return self.request_id

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> MCPResponse:
        """
        Call MCP tool

        Args:
            tool_name: Tool name (e.g., "analyze_session")
            params: Tool parameters

        Returns:
            MCPResponse with result and metadata
        """
        request_id = self._next_request_id()

        payload = {
            "jsonrpc": "2.0",
            "method": f"tools/{tool_name}",
            "params": params,
            "id": request_id
        }

        logger.debug(f"Sending request: {json.dumps(payload, indent=2)}")

        try:
            response = await self.client.post(
                f"{self.server_url}/jsonrpc",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Received response: {json.dumps(data, indent=2)}")

            return MCPResponse(
                result=data.get("result"),
                meta=data.get("_meta"),
                error=data.get("error")
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return MCPResponse(
                result=None,
                error={"code": -32000, "message": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return MCPResponse(
                result=None,
                error={"code": -32603, "message": str(e)}
            )

    async def confirm_mrtr(
        self,
        tool_name: str,
        request_state: str,
        user_input: Dict[str, Any]
    ) -> MCPResponse:
        """
        Confirm MRTR request with user input

        Args:
            tool_name: Original tool name
            request_state: JWT token from MRTR response
            user_input: User's input values (e.g., {"confirm": True})

        Returns:
            MCPResponse with final result
        """
        params = {
            "requestState": request_state,
            **user_input
        }

        return await self.call_tool(tool_name, params)

    async def get_task_status(self, task_id: str) -> MCPResponse:
        """
        Query task status

        Args:
            task_id: Task ID from TaskHandleResult

        Returns:
            MCPResponse with task status
        """
        return await self.call_tool("tasks/get", {"task_id": task_id})

    async def list_tools(self) -> MCPResponse:
        """List all available tools"""
        request_id = self._next_request_id()

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": request_id
        }

        try:
            response = await self.client.post(
                f"{self.server_url}/jsonrpc",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            return MCPResponse(
                result=data.get("result"),
                meta=data.get("_meta"),
                error=data.get("error")
            )

        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return MCPResponse(
                result=None,
                error={"code": -32000, "message": str(e)}
            )

    async def health_check(self) -> bool:
        """
        Check if server is healthy

        Returns:
            True if server is reachable and responding
        """
        try:
            response = await self.client.get(
                f"{self.server_url}/health",
                timeout=5.0
            )
            return response.status_code == 200
        except:
            return False
