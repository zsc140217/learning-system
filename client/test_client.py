"""
测试 Phase 2-3 客户端
"""
import asyncio
from pathlib import Path
import sys

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.main import LearningSystemClient


async def test_basic_functionality():
    """测试基础功能"""
    print("=" * 60)
    print("Phase 2-3 客户端测试")
    print("=" * 60)

    client = LearningSystemClient()

    try:
        # 1. 启动客户端
        print("\n[Test 1] 启动客户端...")
        await client.start()
        print("✅ 客户端启动成功")

        # 2. 测试工具列表
        print("\n[Test 2] 列出可用工具...")
        tools = await client.mcp_pool.get_client("learning-system").list_tools()
        print(f"✅ 找到 {len(tools)} 个工具")

        # 3. 测试状态管理
        print("\n[Test 3] 状态管理...")
        client.state.set_current_project("E:\\Desktop\\learning-system")
        client.state.add_message("user", "测试消息")
        summary = client.state.get_state_summary()
        print(f"✅ 状态管理正常: {summary}")

        # 4. 测试简单工具调用
        print("\n[Test 4] 调用 project/detect_framework...")
        try:
            result = await client.call_tool("project/detect_framework", {
                "project_path": "E:\\Desktop\\learning-system"
            })
            print(f"✅ 工具调用成功: {result.get('framework', 'unknown')}")
        except Exception as e:
            print(f"⚠️  工具调用失败（可能 MCP Server 未正确配置）: {e}")

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
