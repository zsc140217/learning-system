"""
MCP 协议客户端（stdio 通信）
Phase 2-3 核心模块
"""
import json
import asyncio
import uuid
from typing import Any, Dict, Optional
from pathlib import Path
import subprocess


class MCPClient:
    """
    MCP 协议客户端（stdio 通信）

    职责：
    1. 启动 MCP Server 进程（stdio 通信）
    2. 发送 JSON-RPC 请求
    3. 接收并解析响应
    4. 处理 MCP 2026 特性（MRTR、Tasks、Apps、Cache）
    """

    def __init__(self, command: str, args: list[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        self.command = command
        self.args = args
        self.cwd = cwd
        self.env = env
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0

    async def start(self):
        """启动 MCP Server 进程"""
        import os

        # 合并环境变量
        process_env = os.environ.copy()
        if self.env:
            process_env.update(self.env)

        # 启动进程（stdio 通信）
        self.process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=process_env,
            text=True,
            bufsize=1,  # 行缓冲
        )

        print(f"[MCPClient] MCP Server started (PID: {self.process.pid})")

    async def stop(self):
        """停止 MCP Server 进程"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("[MCPClient] MCP Server stopped")

    def _next_request_id(self) -> int:
        """生成请求 ID"""
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送 JSON-RPC 请求

        格式：
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {...}
        }
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP Server not started")

        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
            "params": params or {}
        }

        # 发送请求
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        # 接收响应
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("MCP Server closed connection")

        response = json.loads(response_line)

        # 检查错误
        if "error" in response:
            raise RuntimeError(f"MCP Error: {response['error']}")

        # 返回 result 和 _meta（如果存在）
        result = response.get("result", {})
        if "_meta" in response:
            result["_meta"] = response["_meta"]

        return result

    # ===== MCP 基础方法 =====

    async def list_tools(self) -> list[Dict[str, Any]]:
        """列出所有可用工具"""
        result = await self._send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具

        自动处理 MCP 2026 特性：
        - MRTR: 返回 inputRequired 时标记需要确认
        - Tasks: 返回 taskHandle 时标记为长任务
        - Apps: 返回 uiTemplate 时标记为 UI 组件
        - Cache: 透明处理（服务端自动缓存）
        """
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        # 标记 MCP 特性
        meta = result.get("_meta", {})

        # MRTR 检测
        if "io.modelcontextprotocol/inputRequired" in meta:
            result["_mcp_feature"] = "mrtr"
            result["_mrtr_data"] = meta["io.modelcontextprotocol/inputRequired"]

        # Tasks 检测
        if "taskHandle" in meta:
            result["_mcp_feature"] = "task"
            result["_task_data"] = meta["taskHandle"]

        # Apps 检测 - 修复：检查 _meta 而不是 result
        if "io.modelcontextprotocol/uiTemplate" in meta:
            result["_mcp_feature"] = "app"
            result["_app_data"] = meta["io.modelcontextprotocol/uiTemplate"]

        return result

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return await self._send_request("tasks/status", {"task_id": task_id})

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        return await self._send_request("tasks/cancel", {"task_id": task_id})

    # ===== 高级方法（带上下文） =====

    async def call_tool_with_context(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用工具（显式传递上下文）

        context 包含：
        - session_id: 会话标识
        - user_id: 用户标识
        - project_id: 当前项目
        """
        # 合并上下文参数
        full_arguments = {**arguments, **context}
        return await self.call_tool(name, full_arguments)


class MCPClientPool:
    """
    MCP 客户端池

    支持连接多个 MCP Server：
    - learning-system (本项目)
    - context7 (文档查询)
    - exa (网络搜索)
    - memory (Anthropic Memory MCP)
    """

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}

    async def add_client(self, name: str, client: MCPClient):
        """添加客户端"""
        await client.start()
        self.clients[name] = client

    async def get_client(self, name: str) -> MCPClient:
        """获取客户端"""
        if name not in self.clients:
            raise ValueError(f"MCP client '{name}' not found")
        return self.clients[name]

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用指定 MCP Server 的工具

        示例：
        await pool.call_tool("learning-system", "project/detect_framework", {...})
        await pool.call_tool("context7", "query-docs", {...})
        """
        client = await self.get_client(server_name)

        if context:
            return await client.call_tool_with_context(tool_name, arguments, context)
        else:
            return await client.call_tool(tool_name, arguments)

    async def stop_all(self):
        """停止所有客户端"""
        for client in self.clients.values():
            await client.stop()
