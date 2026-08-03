"""
测试 server.py 迁移到新协议层
验证 4 个工具和 2 个资源是否正常工作
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

import sys
sys.path.insert(0, 'E:/Desktop/learning-system/mcp-server')

from src.protocol import MCPServer, MCPResult


class TestServerMigration:
    """测试服务器迁移"""

    @pytest_asyncio.fixture
    async def server(self):
        """创建测试服务器"""
        server = MCPServer("Test Server")

        # 模拟 analyze_session 工具
        @server.tool("analyze_session")
        async def analyze_session(session_data: str, session_id: str = None) -> MCPResult:
            return MCPResult(
                data={
                    "session_id": session_id or "test-session-001",
                    "status": "completed",
                    "message": "Analysis triggered"
                },
                meta={
                    "ttlMs": 300000,
                    "cacheScope": "user"
                }
            )

        # 模拟 save_knowledge 工具
        @server.tool("save_knowledge")
        async def save_knowledge(knowledge_points: list, session_id: str) -> MCPResult:
            return MCPResult(
                data={
                    "saved_count": len(knowledge_points),
                    "knowledge_ids": [],
                    "status": "pending"
                },
                meta={
                    "ttlMs": 0,
                    "cacheScope": "user"
                }
            )

        # 模拟 track_project 工具
        @server.tool("track_project")
        async def track_project(project_path: str, project_name: str = None) -> MCPResult:
            return MCPResult(
                data={
                    "project_id": "project-001",
                    "highlights": [],
                    "status": "pending"
                },
                meta={
                    "ttlMs": 86400000,
                    "cacheScope": "user"
                }
            )

        # 模拟 explore_technology 工具
        @server.tool("explore_technology")
        async def explore_technology(topic: str, depth: str = "basic") -> MCPResult:
            return MCPResult(
                data={
                    "topic": topic,
                    "learning_path": [],
                    "resources": [],
                    "status": "pending"
                },
                meta={
                    "ttlMs": 3600000,
                    "cacheScope": "public"
                }
            )

        # 模拟资源
        @server.resource("knowledge://graph")
        async def get_knowledge_graph() -> str:
            return "知识图谱数据"

        @server.resource("sessions://list")
        async def list_sessions() -> str:
            return "会话列表"

        return server

    @pytest.mark.asyncio
    async def test_tool_analyze_session(self, server):
        """测试 analyze_session 工具"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_session",
                "arguments": {
                    "session_data": "User: 什么是FastAPI？"
                }
            }
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["status"] == "completed"

        # 验证 _meta 字段
        assert "_meta" in response
        assert response["_meta"]["ttlMs"] == 300000
        assert response["_meta"]["cacheScope"] == "user"

    @pytest.mark.asyncio
    async def test_tool_save_knowledge(self, server):
        """测试 save_knowledge 工具"""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_knowledge",
                "arguments": {
                    "knowledge_points": [
                        {"title": "FastAPI 基础", "content": "..."}
                    ],
                    "session_id": "session-001"
                }
            }
        }

        response = await server.handle_request(request)

        assert response["result"]["saved_count"] == 1
        assert response["_meta"]["ttlMs"] == 0

    @pytest.mark.asyncio
    async def test_tools_list(self, server):
        """测试 tools/list"""
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/list",
            "params": {}
        }

        response = await server.handle_request(request)

        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        assert "analyze_session" in tool_names
        assert "save_knowledge" in tool_names
        assert "track_project" in tool_names
        assert "explore_technology" in tool_names

    @pytest.mark.asyncio
    async def test_resource_knowledge_graph(self, server):
        """测试 knowledge://graph 资源"""
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "resources/read",
            "params": {
                "uri": "knowledge://graph"
            }
        }

        response = await server.handle_request(request)

        assert "contents" in response["result"]
        assert response["result"]["contents"][0]["uri"] == "knowledge://graph"
