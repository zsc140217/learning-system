"""
测试文件系统工具
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8080"

async def test_read_file():
    """测试读取文件"""
    print("\n=== 测试 read_file ===")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/mcp/call_tool",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "read_file",
                    "arguments": {
                        "file_path": "mcp-server/config.py"
                    }
                }
            },
            timeout=10.0
        )

        result = response.json()
        print(f"状态码: {response.status_code}")

        if "result" in result:
            data = result["result"]
            if "error" in data:
                print(f"错误: {data['error']}")
            else:
                print(f"文件路径: {data['path']}")
                print(f"文件大小: {data['size']} bytes")
                print(f"行数: {data['lines']}")
                print(f"内容预览: {data['content'][:100]}...")
        else:
            print(f"完整响应: {result}")

async def test_list_directory():
    """测试列出目录"""
    print("\n=== 测试 list_directory ===")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/mcp/call_tool",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "list_directory",
                    "arguments": {
                        "directory_path": "mcp-server",
                        "max_depth": 1,
                        "show_hidden": False
                    }
                }
            },
            timeout=10.0
        )

        result = response.json()
        print(f"状态码: {response.status_code}")

        if "result" in result:
            data = result["result"]
            if "error" in data:
                print(f"错误: {data['error']}")
            else:
                print(f"目录路径: {data['path']}")
                print(f"项目数量: {data['count']}")
                print(f"前5个项目:")
                for item in data['items'][:5]:
                    print(f"  - {item['name']} ({item['type']})")
        else:
            print(f"完整响应: {result}")

async def test_search_files():
    """测试搜索文件"""
    print("\n=== 测试 search_files ===")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/mcp/call_tool",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "search_files",
                    "arguments": {
                        "directory_path": "mcp-server",
                        "pattern": "*.py",
                        "max_results": 10
                    }
                }
            },
            timeout=10.0
        )

        result = response.json()
        print(f"状态码: {response.status_code}")

        if "result" in result:
            data = result["result"]
            if "error" in data:
                print(f"错误: {data['error']}")
            else:
                print(f"匹配数量: {data['count']}")
                print(f"匹配文件:")
                for match in data['matches'][:5]:
                    print(f"  - {match['name']} ({match['size']} bytes)")
        else:
            print(f"完整响应: {result}")

async def main():
    """运行所有测试"""
    print("开始测试文件系统工具...")
    print("注意: 需要先重启 MCP Server 以加载新工具")

    try:
        await test_read_file()
        await test_list_directory()
        await test_search_files()
        print("\n✅ 测试完成")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
