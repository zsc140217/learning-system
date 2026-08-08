"""
MRTR 处理器
处理 MCP 2026 的 MRTR 特性（多轮事务请求）
"""
from typing import Dict, Any, Callable, Optional


class MRTRHandler:
    """
    MRTR（Multi-Round Tool Responses）处理器

    职责：
    1. 检测工具返回的 inputRequired
    2. 弹出确认对话框（通过 UI 回调）
    3. 用户确认后，带上 request_state 再次调用工具

    使用示例：
    result = await mcp.call_tool("delete_knowledge", {"ids": [...]})
    if result.get("_mcp_feature") == "mrtr":
        result = await mrtr_handler.handle(
            tool_name="delete_knowledge",
            arguments={"ids": [...]},
            result=result,
            ui_callback=show_confirmation_dialog
        )
    """

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

    async def handle(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        state_manager,
        ui_callback: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        处理 MRTR 流程

        Args:
            tool_name: 工具名称
            arguments: 原始参数
            result: 工具返回结果（包含 inputRequired）
            state_manager: 状态管理器
            ui_callback: UI 回调函数（显示确认对话框，返回用户输入）

        Returns:
            第二轮调用的结果
        """
        if result.get("_mcp_feature") != "mrtr":
            return result

        # 提取 inputRequired 数据
        mrtr_data = result.get("_mrtr_data", {})
        request_state = mrtr_data.get("requestState")
        prompt = mrtr_data.get("prompt", "确认执行此操作？")
        fields = mrtr_data.get("fields", [])

        # 保存到状态管理器
        request_id = f"mrtr_{request_state}"
        state_manager.add_confirmation(
            request_id=request_id,
            tool_name=tool_name,
            args=arguments,
            prompt=prompt,
            fields=fields,
            request_state=request_state
        )

        # 调用 UI 回调，显示确认对话框
        try:
            user_input = ui_callback({
                "prompt": prompt,
                "fields": fields,
                "request_id": request_id
            })

            # 用户取消
            if not user_input or not user_input.get("confirmed"):
                state_manager.remove_confirmation(request_id)
                return {
                    "status": "cancelled",
                    "message": "User cancelled the operation"
                }

            # 第二轮调用（带上 request_state）
            second_arguments = {
                **arguments,
                "request_state": request_state,
                **user_input  # 用户输入的字段值
            }

            second_result = await self.mcp_client.call_tool(tool_name, second_arguments)

            # 清理确认记录
            state_manager.remove_confirmation(request_id)

            return second_result

        except Exception as e:
            state_manager.remove_confirmation(request_id)
            raise


class ConsoleUICallback:
    """
    控制台 UI 回调（用于测试）
    """

    @staticmethod
    def show_confirmation(mrtr_request: Dict[str, Any]) -> Dict[str, Any]:
        """显示确认对话框（控制台版本）"""
        print("\n" + "=" * 60)
        print("[确认操作]")
        print(f"提示：{mrtr_request['prompt']}")
        print("=" * 60)

        # 显示字段
        user_input = {}
        for field in mrtr_request.get("fields", []):
            field_name = field.get("name")
            field_type = field.get("type")
            field_label = field.get("label", field_name)

            if field_type == "boolean":
                response = input(f"{field_label} (y/n): ").strip().lower()
                user_input[field_name] = response in ["y", "yes", "true", "1"]
            else:
                user_input[field_name] = input(f"{field_label}: ").strip()

        # 最终确认
        confirm = input("\n确认执行？(y/n): ").strip().lower()
        user_input["confirmed"] = confirm in ["y", "yes"]

        return user_input
