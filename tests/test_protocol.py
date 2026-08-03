"""
Test MCP Protocol Core
Tests for JSON-RPC 2.0 with _meta field support
"""

import pytest
import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

from src.protocol import (
    MCPServer,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPResult,
    InputRequiredResult,
    TaskHandleResult,
    UITemplateResult,
    MCPError
)


class TestMCPResult:
    """Test MCPResult base class"""

    def test_basic_result(self):
        """Test basic result without meta"""
        result = MCPResult(data={"status": "ok"})
        response = result.to_jsonrpc(request_id=1)

        assert response == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok"}
        }

    def test_result_with_meta(self):
        """Test result with _meta field"""
        result = MCPResult(
            data={"status": "ok"},
            meta={"ttlMs": 3600000, "cacheScope": "user"}
        )
        response = result.to_jsonrpc(request_id=1)

        assert response == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok"},
            "_meta": {
                "ttlMs": 3600000,
                "cacheScope": "user"
            }
        }


class TestInputRequiredResult:
    """Test InputRequiredResult for MRTR"""

    def test_input_required_basic(self):
        """Test basic input required result"""
        result = InputRequiredResult(
            message="Confirm deletion",
            fields=[
                {"name": "confirm", "type": "boolean", "label": "Confirm"}
            ]
        )

        assert "io.modelcontextprotocol/inputRequired" in result.meta
        assert result.meta["io.modelcontextprotocol/inputRequired"]["message"] == "Confirm deletion"
        assert len(result.meta["io.modelcontextprotocol/inputRequired"]["fields"]) == 1

    def test_input_required_with_state(self):
        """Test input required with JWT state"""
        result = InputRequiredResult(
            message="Confirm deletion",
            fields=[{"name": "confirm", "type": "boolean"}],
            request_state="eyJhbGciOiJIUzI1NiJ9.test"
        )

        assert result.meta["io.modelcontextprotocol/inputRequired"]["requestState"] == "eyJhbGciOiJIUzI1NiJ9.test"


class TestTaskHandleResult:
    """Test TaskHandleResult for long tasks"""

    def test_task_handle_running(self):
        """Test task handle in running state"""
        result = TaskHandleResult(
            task_id="task-001",
            status="running",
            progress=0.3,
            message="Processing...",
            eta_seconds=300
        )

        assert "io.modelcontextprotocol/taskHandle" in result.meta
        task_data = result.meta["io.modelcontextprotocol/taskHandle"]

        assert task_data["taskId"] == "task-001"
        assert task_data["status"] == "running"
        assert task_data["progress"] == 0.3
        assert task_data["message"] == "Processing..."
        assert task_data["etaSeconds"] == 300

    def test_task_handle_completed(self):
        """Test task handle in completed state"""
        result = TaskHandleResult(
            task_id="task-001",
            status="completed",
            progress=1.0,
            result={"analysis": "done"}
        )

        task_data = result.meta["io.modelcontextprotocol/taskHandle"]
        assert task_data["status"] == "completed"
        assert task_data["progress"] == 1.0
        assert task_data["result"] == {"analysis": "done"}


class TestUITemplateResult:
    """Test UITemplateResult for MCP Apps"""

    def test_ui_template(self):
        """Test UI template result"""
        result = UITemplateResult(
            template_id="com.learning-system.summary",
            template_path="/templates/summary.html",
            template_data={"session_id": "session_001"}
        )

        assert "io.modelcontextprotocol/uiTemplate" in result.meta
        ui_data = result.meta["io.modelcontextprotocol/uiTemplate"]

        assert ui_data["templateId"] == "com.learning-system.summary"
        assert ui_data["templatePath"] == "/templates/summary.html"
        assert ui_data["data"]["session_id"] == "session_001"


class TestJSONRPCRequest:
    """Test JSON-RPC request parsing"""

    def test_parse_tool_call(self):
        """Test parsing tools/call request"""
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_session",
                "arguments": {"session_data": "test"}
            }
        }

        request = JSONRPCRequest.from_dict(request_data)

        assert request.jsonrpc == "2.0"
        assert request.id == 1
        assert request.method == "tools/call"
        assert request.params["name"] == "analyze_session"


class TestJSONRPCResponse:
    """Test JSON-RPC response generation"""

    def test_success_response(self):
        """Test successful response"""
        response = JSONRPCResponse(
            jsonrpc="2.0",
            id=1,
            result={"status": "ok"}
        )

        assert response.to_dict() == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok"}
        }

    def test_error_response(self):
        """Test error response"""
        response = JSONRPCResponse(
            jsonrpc="2.0",
            id=1,
            error={"code": -32602, "message": "Invalid params"}
        )

        response_dict = response.to_dict()
        assert "error" in response_dict
        assert "result" not in response_dict


class TestMCPServer:
    """Test MCP Server"""

    @pytest.mark.asyncio
    async def test_register_tool(self):
        """Test tool registration"""
        server = MCPServer("Test Server")

        @server.tool("test_tool")
        async def test_tool(param: str) -> MCPResult:
            return MCPResult(data={"param": param})

        assert "test_tool" in server.tools

    @pytest.mark.asyncio
    async def test_handle_tool_call(self):
        """Test handling tool call"""
        server = MCPServer("Test Server")

        @server.tool("echo")
        async def echo(message: str) -> MCPResult:
            return MCPResult(data={"echo": message})

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "hello"}
            }
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["echo"] == "hello"

    @pytest.mark.asyncio
    async def test_handle_tool_list(self):
        """Test listing tools"""
        server = MCPServer("Test Server")

        @server.tool("tool1")
        async def tool1():
            return MCPResult(data={})

        @server.tool("tool2")
        async def tool2():
            return MCPResult(data={})

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        response = await server.handle_request(request)

        assert len(response["result"]["tools"]) == 2

    @pytest.mark.asyncio
    async def test_tool_not_found(self):
        """Test tool not found error"""
        server = MCPServer("Test Server")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "nonexistent",
                "arguments": {}
            }
        }

        response = await server.handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_register_resource(self):
        """Test resource registration"""
        server = MCPServer("Test Server")

        @server.resource("test://data")
        async def get_data():
            return "test data"

        assert "test://data" in server.resources

    @pytest.mark.asyncio
    async def test_handle_resource_read(self):
        """Test reading resource"""
        server = MCPServer("Test Server")

        @server.resource("knowledge://graph")
        async def get_graph():
            return "graph data"

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {"uri": "knowledge://graph"}
        }

        response = await server.handle_request(request)

        assert response["result"]["contents"][0]["uri"] == "knowledge://graph"
        assert response["result"]["contents"][0]["text"] == "graph data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
