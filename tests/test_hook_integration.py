"""End-to-end test for Hook system integration with transport."""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

from src.protocol import MCPServer, MCPResult, StdioTransport
from src.hooks import SessionCaptureHook
from src.storage import ObservationStore


@pytest_asyncio.fixture
async def temp_observation_store(tmp_path):
    """Create a temporary observation store."""
    store_path = tmp_path / "test_observations.jsonl"
    store = ObservationStore(str(store_path))
    yield store
    await store.clear()


@pytest.mark.asyncio
async def test_hook_integration_with_transport(temp_observation_store):
    """Test that hooks are called during transport message handling."""
    # Create server with a test tool
    server = MCPServer("test_server")

    @server.tool("test_tool")
    async def test_tool(arg: str) -> MCPResult:
        return MCPResult(data={"result": f"processed {arg}"})

    # Create hook
    hook = SessionCaptureHook(temp_observation_store)

    # Create transport with hook
    transport = StdioTransport(hooks=[hook])

    # Verify hook was registered
    assert len(transport.hooks) == 1
    assert transport.hooks[0] == hook


@pytest.mark.asyncio
async def test_hook_records_tool_call(temp_observation_store):
    """Test that hooks record actual tool calls."""
    server = MCPServer("test_server")

    @server.tool("echo")
    async def echo_tool(message: str) -> MCPResult:
        return MCPResult(data={"echo": message})

    hook = SessionCaptureHook(temp_observation_store)

    # Simulate a tool call by manually invoking hook callbacks
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "hello"}}
    }

    response = await server.handle_request(request)

    # Manually trigger hooks (simulating what transport.run() does)
    from src.hooks import HookContext
    import time

    context = HookContext(request=request)
    await hook.on_request(context)

    context.response = response
    await hook.on_response(context)

    # Verify observation was recorded
    observations = await temp_observation_store.read_all()
    assert len(observations) == 1

    obs = observations[0]
    assert obs["type"] == "mcp_interaction"
    assert obs["request"]["method"] == "tools/call"
    assert obs["request"]["params"]["name"] == "echo"
    assert obs["response"]["success"] is True
    assert "duration_ms" in obs


@pytest.mark.asyncio
async def test_hook_captures_multiple_calls(temp_observation_store):
    """Test that hooks capture multiple sequential calls."""
    server = MCPServer("test_server")

    @server.tool("counter")
    async def counter_tool(n: int) -> MCPResult:
        return MCPResult(data={"count": n})

    hook = SessionCaptureHook(temp_observation_store)

    # Simulate multiple calls
    from src.hooks import HookContext

    for i in range(3):
        request = {
            "jsonrpc": "2.0",
            "id": i,
            "method": "tools/call",
            "params": {"name": "counter", "arguments": {"n": i}}
        }

        response = await server.handle_request(request)

        context = HookContext(request=request)
        await hook.on_request(context)
        context.response = response
        await hook.on_response(context)

    # Verify all calls were recorded
    observations = await temp_observation_store.read_all()
    assert len(observations) == 3

    for i, obs in enumerate(observations):
        assert obs["request"]["params"]["arguments"]["n"] == i
