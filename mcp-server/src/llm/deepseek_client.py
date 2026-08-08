"""
DeepSeek API Client

支持工具调用（Tool Use）的 DeepSeek API 客户端
"""
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
import httpx

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    DeepSeek API 客户端，支持工具调用

    使用方式：
    1. 注册工具函数
    2. 调用 chat_with_tools()
    3. DeepSeek 决定是否调用工具
    4. 自动执行工具并返回结果
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com"):
        """
        初始化 DeepSeek 客户端

        Args:
            api_key: DeepSeek API Key，默认从配置文件读取
            base_url: API 基础 URL
        """
        if not api_key:
            # 优先从配置文件读取
            try:
                from config import settings
                api_key = settings.deepseek_api_key
            except ImportError:
                api_key = os.getenv("DEEPSEEK_API_KEY")

        self.api_key = api_key
        if not self.api_key:
            raise ValueError("DeepSeek API key not found. Set DEEPSEEK_API_KEY in mcp-server/.env file")

        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

        # 工具注册表
        self.tools_registry: Dict[str, Callable] = {}
        self.tools_specs: List[Dict] = []

    def register_tool(self, name: str, func: Callable, spec: Dict):
        """
        注册工具函数

        Args:
            name: 工具名称
            func: 工具函数
            spec: 工具规范（OpenAI Function Calling 格式）
        """
        self.tools_registry[name] = func
        self.tools_specs.append({
            "type": "function",
            "function": spec
        })
        logger.info(f"Registered tool: {name}")

    async def chat_with_tools(
        self,
        prompt: str,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        与 DeepSeek 对话，支持工具调用

        Args:
            prompt: 用户 Prompt
            max_iterations: 最大迭代次数（防止无限循环）

        Returns:
            最终响应
        """
        messages = [{"role": "user", "content": prompt}]

        for iteration in range(max_iterations):
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")

            # 调用 DeepSeek API
            response = await self._call_api(messages)

            # 检查是否有工具调用
            if response.get("finish_reason") == "tool_calls":
                tool_calls = response.get("tool_calls", [])

                logger.info(f"DeepSeek requested {len(tool_calls)} tool calls")

                # 执行工具调用
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    tool_id = tool_call["id"]

                    logger.info(f"Calling tool: {tool_name} with args: {tool_args}")

                    # 执行工具
                    tool_result = await self._execute_tool(tool_name, tool_args)

                    # 添加工具结果到消息历史
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps(tool_result)
                    })

                # 继续下一轮对话
                continue

            else:
                # 没有工具调用，返回最终结果
                final_content = response.get("content", "")
                logger.info("DeepSeek finished, no more tool calls")

                return {
                    "content": final_content,
                    "iterations": iteration + 1,
                    "messages": messages
                }

        # 达到最大迭代次数
        logger.warning(f"Reached max iterations ({max_iterations})")
        return {
            "content": "Max iterations reached",
            "iterations": max_iterations,
            "messages": messages,
            "error": "max_iterations_exceeded"
        }

    async def _call_api(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        调用 DeepSeek API

        Args:
            messages: 消息历史

        Returns:
            API 响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "tools": self.tools_specs if self.tools_specs else None,
            "temperature": 0.7,
            "max_tokens": 4000
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]

            return {
                "content": message.get("content"),
                "tool_calls": message.get("tool_calls"),
                "finish_reason": choice.get("finish_reason")
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            raise

    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> Any:
        """
        执行工具函数

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            工具执行结果
        """
        if tool_name not in self.tools_registry:
            logger.error(f"Tool not found: {tool_name}")
            return {"error": f"Tool '{tool_name}' not registered"}

        try:
            tool_func = self.tools_registry[tool_name]

            # 如果是异步函数
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_args)
            else:
                result = tool_func(**tool_args)

            logger.info(f"Tool {tool_name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {"error": str(e)}

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
