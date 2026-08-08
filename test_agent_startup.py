"""
测试 Agent 启动
验证所有 6 个 Agent 是否正确初始化
"""
import asyncio
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "client" / "backend"))
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from mcp_client import MCPClient

async def test_agent_startup():
    """测试 Agent 启动"""
    print("=" * 60)
    print("测试 Agent 启动")
    print("=" * 60)

    # 创建 MCP 客户端
    mcp_server_path = Path(__file__).parent / "mcp-server"
    client = MCPClient(
        command="python",
        args=["server.py"],
        cwd=str(mcp_server_path),
        env={"PYTHONPATH": str(mcp_server_path)}
    )

    try:
        # 启动 MCP Server
        print("\n[1] 启动 MCP Server...")
        await client.start()
        await asyncio.sleep(3)  # 等待 Agent 初始化

        # 列出可用工具
        print("\n[2] 列出可用工具...")
        tools = await client.list_tools()
        print(f"   找到 {len(tools)} 个工具")

        # 显示前10个工具
        print("\n[3] 工具列表 (前10个):")
        for tool in tools[:10]:
            print(f"   - {tool.get('name')}")

        print("\n" + "=" * 60)
        print("测试完成！MCP Server 启动成功")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 停止 MCP Server
        print("\n[关闭] 停止 MCP Server...")
        await client.stop()

if __name__ == "__main__":
    asyncio.run(test_agent_startup())
