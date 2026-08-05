"""
Test HTTP Server Connection
Tests MCP 2026-07-28 protocol compliance
"""
import asyncio
import sys
from pathlib import Path

# Add client-cli to path
sys.path.insert(0, str(Path(__file__).parent.parent / "client-cli"))

from mcp_client import MCPClient
from loguru import logger


async def test_health():
    """Test health endpoint"""
    client = MCPClient("http://localhost:8080")

    print("\n[1/5] Testing health endpoint...")
    is_healthy = await client.health_check()

    if is_healthy:
        print("✓ Server is healthy")
        return True
    else:
        print("✗ Server is not responding")
        return False


async def test_list_tools():
    """Test tools/list"""
    client = MCPClient("http://localhost:8080")

    print("\n[2/5] Testing tools/list...")
    response = await client.list_tools()

    if response.is_success():
        tools = response.result.get("tools", [])
        print(f"✓ Found {len(tools)} tools:")
        for tool in tools[:5]:  # Show first 5
            print(f"  - {tool['name']}")
        if len(tools) > 5:
            print(f"  ... and {len(tools) - 5} more")
        return True
    else:
        print(f"✗ Failed: {response.error}")
        return False


async def test_tool_call():
    """Test simple tool call"""
    client = MCPClient("http://localhost:8080")

    print("\n[3/5] Testing tool call (cache_stats)...")
    response = await client.call_tool("cache_stats", {})

    if response.is_success():
        print("✓ Tool call successful")
        print(f"  Result: {response.result}")
        return True
    else:
        print(f"✗ Failed: {response.error}")
        return False


async def test_mrtr():
    """Test MRTR (Multi Round-Trip Request)"""
    client = MCPClient("http://localhost:8080")

    print("\n[4/5] Testing MRTR (delete_knowledge with confirmation)...")

    # First round: should return confirmation request
    response = await client.call_tool("delete_knowledge", {
        "knowledge_ids": ["test_node_1", "test_node_2"]
    })

    if response.is_success() and response.is_mrtr():
        print("✓ MRTR confirmation request received")
        mrtr_data = response.get_mrtr_data()
        print(f"  Request state: {mrtr_data.get('requestState', 'N/A')[:20]}...")
        print(f"  Fields: {[f['name'] for f in mrtr_data.get('fields', [])]}")
        return True
    else:
        print(f"✗ Expected MRTR response, got: {response.result}")
        return False


async def test_tasks():
    """Test Tasks extension"""
    client = MCPClient("http://localhost:8080")

    print("\n[5/5] Testing Tasks extension (list_tasks)...")
    response = await client.call_tool("tasks/list", {})

    if response.is_success():
        tasks = response.result.get("tasks", [])
        print(f"✓ Tasks list retrieved: {len(tasks)} tasks")
        return True
    else:
        print(f"✗ Failed: {response.error}")
        return False


async def main():
    """Run all tests"""
    logger.remove()
    logger.add(lambda msg: None)  # Suppress logs

    print("=" * 60)
    print("MCP HTTP Server Connection Test")
    print("Protocol: MCP 2026-07-28")
    print("=" * 60)

    results = []

    # Run tests
    results.append(await test_health())
    if not results[-1]:
        print("\n✗ Server not reachable. Make sure http_server.py is running.")
        return False

    results.append(await test_list_tools())
    results.append(await test_tool_call())
    results.append(await test_mrtr())
    results.append(await test_tasks())

    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests passed! HTTP server is working correctly.")
        return True
    else:
        print("\n✗ Some tests failed. Check server logs for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
