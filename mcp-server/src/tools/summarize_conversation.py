"""
知识总结工具 - 从对话中提取知识点
"""
import json
import re
import logging
from typing import Optional
from ..llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)

# Few-shot 提示词模板
EXTRACTION_PROMPT_TEMPLATE = """
请从以下对话中提取关键知识点，以 JSON 数组格式返回。

示例输入：
用户: 什么是 FastAPI？
助手: FastAPI 是一个现代、快速的 Python Web 框架，基于 Starlette 和 Pydantic。它的主要特点是高性能、自动生成 API 文档、支持类型提示。

用户: 它有什么优点？
助手: 主要优点包括：1. 性能接近 NodeJS 和 Go；2. 自动生成 OpenAPI 和 Swagger 文档；3. 类型提示支持减少错误；4. 异步支持。

示例输出：
[
  {{
    "title": "FastAPI 定义",
    "content": "FastAPI 是一个现代、快速的 Python Web 框架，基于 Starlette（ASGI 框架）和 Pydantic（数据验证）。",
    "tags": ["Python", "Web框架", "ASGI"],
    "type": "technology"
  }},
  {{
    "title": "FastAPI 核心特性",
    "content": "1. 高性能（性能接近 NodeJS 和 Go）\\n2. 自动生成 API 文档（OpenAPI 和 Swagger UI）\\n3. 类型提示支持（利用 Python 3.6+ 的类型注解）\\n4. 原生异步支持（async/await）",
    "tags": ["FastAPI", "特性", "性能"],
    "type": "concept"
  }},
  {{
    "title": "FastAPI 技术栈",
    "content": "FastAPI 构建在两个核心库之上：\\n- Starlette：提供 ASGI 支持和 Web 功能\\n- Pydantic：提供数据验证和序列化",
    "tags": ["FastAPI", "Starlette", "Pydantic"],
    "type": "concept"
  }}
]

现在请处理以下对话：
{conversation_text}

要求：
1. 每个知识点包含 title、content、tags、type 字段
2. title 简短明确（10 字以内）
3. content 详细完整（包含定义、特点、用途等）
4. tags 至少 2 个，最多 5 个
5. type 必须是 concept/technology/method/tool 之一
6. 至少提取 3 个知识点
7. 只提取实质性的技术知识，不包括问候语和重复内容
8. 直接返回 JSON 数组，不要添加额外说明
"""


async def summarize_conversation(
    conversation_text: str,
    extraction_prompt: Optional[str] = None
) -> dict:
    """
    从对话中提取知识点

    参数：
      conversation_text: 完整的对话文本
      extraction_prompt: 可选的自定义提取提示词

    返回：
      {
        "knowledge_points": [
          {
            "title": "知识点标题",
            "content": "详细内容",
            "tags": ["标签1", "标签2"],
            "type": "concept"
          }
        ],
        "count": 3
      }
    """
    try:
        # 构造提示词
        prompt = extraction_prompt or EXTRACTION_PROMPT_TEMPLATE.format(
            conversation_text=conversation_text
        )

        # 调用 LLM
        llm_client = LLMProviderFactory.create()
        messages = [{"role": "user", "content": prompt}]
        response = await llm_client.chat(messages)

        # 解析 JSON
        knowledge_points = []
        try:
            knowledge_points = json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 部分（LLM 可能返回额外文本）
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                knowledge_points = json.loads(json_match.group())
            else:
                raise ValueError("Failed to extract JSON from LLM response")

        # 验证和格式化返回的知识点
        validated_points = []
        for point in knowledge_points:
            # 必需字段检查
            if not all(k in point for k in ['title', 'content', 'tags', 'type']):
                logger.warning(f"Skipping invalid knowledge point: {point}")
                continue

            # 类型检查
            if point['type'] not in ['concept', 'technology', 'method', 'tool']:
                logger.warning(f"Invalid type {point['type']}, defaulting to 'concept'")
                point['type'] = 'concept'

            # 标签格式化
            if isinstance(point['tags'], str):
                point['tags'] = [tag.strip() for tag in point['tags'].split(',')]

            # 确保 tags 是列表
            if not isinstance(point['tags'], list):
                point['tags'] = []

            validated_points.append(point)

        if not validated_points:
            raise ValueError("No valid knowledge points extracted")

        return {
            "knowledge_points": validated_points,
            "count": len(validated_points)
        }

    except Exception as e:
        logger.error(f"Summarize conversation failed: {e}")
        return {
            "knowledge_points": [],
            "count": 0,
            "error": str(e)
        }
