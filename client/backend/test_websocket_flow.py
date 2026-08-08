"""
测试 WebSocket 完整数据流
验证 _meta 字段是否正确传递
"""
import asyncio
import json
import websockets

async def test_knowledge_graph():
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:
        print("[OK] Connected to WebSocket")

        # 发送 ui_knowledge_graph 请求
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ui_knowledge_graph",
                "arguments": {}
            }
        }

        print(f"\n[->] Sending request: {json.dumps(request, indent=2)}")
        await websocket.send(json.dumps(request))

        # 接收响应
        response_text = await websocket.recv()
        response = json.loads(response_text)

        print(f"\n[<-] Received response keys: {list(response.keys())}")

        # 验证响应结构
        has_meta = "_meta" in response
        has_result = "result" in response

        print(f"\nValidation:")
        print(f"  Has 'result': {has_result}")
        print(f"  Has '_meta': {has_meta}")

        if has_meta:
            meta = response["_meta"]
            print(f"  _meta keys: {list(meta.keys())}")

            ui_template = meta.get("io.modelcontextprotocol/uiTemplate")
            if ui_template:
                print(f"  [OK] uiTemplate found")
                print(f"    templateId: {ui_template.get('templateId')}")
                print(f"    template length: {len(ui_template.get('template', ''))}")
                print(f"    data keys: {list(ui_template.get('data', {}).keys())}")

                data = ui_template.get("data", {})
                print(f"    nodes: {len(data.get('nodes', []))}")
                print(f"    edges: {len(data.get('edges', []))}")
            else:
                print(f"  [ERROR] No uiTemplate in _meta")
        else:
            print(f"  [ERROR] No _meta field in response")
            print(f"\nFull response:\n{json.dumps(response, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_knowledge_graph())
