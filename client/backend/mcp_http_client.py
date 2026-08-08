"""
MCP HTTP 客户端（替代 stdio 通信）
直接调用 http_server.py 的 JSON-RPC 端点
"""
import httpx
from typing import Any, Dict, Optional


class MCPHTTPClient:
    """
    MCP HTTP 客户端

    通过 HTTP 与 MCP Server 通信，避免 stdio 死锁问题
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.jsonrpc_url = f"{base_url}/jsonrpc"
        self._request_id = 0
        self.client = httpx.AsyncClient(timeout=30.0)

    def _next_request_id(self) -> int:
        """生成请求 ID"""
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送 JSON-RPC 请求

        返回格式：
        {
            "result": {...},
            "_meta": {...}  # 如果存在
        }
        """
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
            "params": params or {}
        }

        response = await self.client.post(self.jsonrpc_url, json=request)
        response.raise_for_status()

        data = response.json()

        # 检查错误
        if "error" in data:
            raise RuntimeError(f"MCP Error: {data['error']}")

        # 返回完整响应结构，保持 result 和 _meta 在顶层
        return {
            "result": data.get("result", {}),
            "_meta": data.get("_meta")
        }

    async def list_tools(self) -> list[Dict[str, Any]]:
        """列出所有可用工具"""
        result = await self._send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具

        返回包含 _meta 的完整响应
        """
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        return result

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
