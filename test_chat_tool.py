"""
测试 chat 工具
"""
import asyncio
import httpx
import json


async def test_chat():
    """测试 chat 工具"""

    # MCP Server 地址
    url = "http://localhost:8080/jsonrpc"

    # 1. 测试 tools/list - 查看是否有 chat 工具
    print("=" * 50)
    print("1. 查询所有工具...")
    print("=" * 50)

    list_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=list_request)
        result = response.json()

        if "result" in result:
            tools = result["result"].get("tools", [])
            chat_tool = [t for t in tools if t["name"] == "chat"]

            if chat_tool:
                print("[OK] chat 工具已注册")
                print(f"  描述: {chat_tool[0].get('description', 'N/A')}")
                print(f"  参数: {json.dumps(chat_tool[0].get('inputSchema', {}), indent=2, ensure_ascii=False)}")
            else:
                print("[FAIL] chat 工具未找到")
                print(f"可用工具: {[t['name'] for t in tools]}")
        else:
            print(f"[FAIL] 获取工具列表失败: {result}")

    # 2. 测试调用 chat 工具
    print("\n" + "=" * 50)
    print("2. 测试 chat 工具...")
    print("=" * 50)

    chat_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "chat",
            "arguments": {
                "message": "你好，请用一句话介绍什么是 FastAPI"
            }
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("发送请求: 你好，请用一句话介绍什么是 FastAPI")
        response = await client.post(url, json=chat_request)
        result = response.json()

        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 检查结果
        if "result" in result:
            content = result["result"].get("content", [])
            if content:
                text_content = [c for c in content if c.get("type") == "text"]
                if text_content:
                    print(f"\n[OK] AI 回答:")
                    print(f"  {text_content[0]['text']}")
                else:
                    print(f"\n[FAIL] 没有找到文本内容")
        elif "error" in result:
            print(f"\n[FAIL] 错误: {result['error']}")


if __name__ == "__main__":
    print("测试 Chat 工具")
    print("确保 MCP Server 正在运行: python mcp-server/http_server.py")
    print()

    try:
        asyncio.run(test_chat())
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
