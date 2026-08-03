"""
LLM Prompts for Semantic Analysis
Few-Shot prompts with JSON Schema output
"""

# Few-Shot Prompt for Knowledge Point Extraction
EXTRACT_CONCEPTS_PROMPT = """
从对话中提取学习了哪些技术概念。

# 规则
1. 只提取技术性概念（如"异步编程"、"MCP协议"、"知识图谱"）
2. 忽略过程性描述（如"我们讨论了"、"接下来要做"）
3. 每个概念附带简短定义（20字内）
4. 按重要性排序（0.0-1.0）

# 示例

输入对话：
```
User: 如何实现异步任务？
Assistant: 可以用 asyncio.create_task 创建后台任务，它会返回一个 Task 对象，不阻塞当前协程...
```

输出JSON：
{{
  "concepts": [
    {{
      "name": "asyncio.create_task",
      "definition": "Python异步任务创建方法",
      "importance": 0.9,
      "category": "async"
    }},
    {{
      "name": "协程",
      "definition": "可暂停和恢复的异步函数",
      "importance": 0.7,
      "category": "async"
    }}
  ]
}}

# 现在处理：
对话内容：
{conversation}

输出JSON（只输出JSON，不要其他内容）：
"""

# Few-Shot Prompt for Difficulty Assessment
ASSESS_DIFFICULTY_PROMPT = """
评估技术概念的学习难度（0.3-0.9）。

# 评分标准
- 0.3-0.4: 基础概念（变量、函数、循环）
- 0.5-0.6: 中级概念（异步编程、装饰器、泛型）
- 0.7-0.8: 高级概念（元编程、协议设计、分布式系统）
- 0.9: 专家级（编译器设计、分布式一致性算法）

# 考虑因素
1. 需要的前置知识量
2. 抽象层次
3. 常见错误陷阱数量
4. 掌握时间

# 示例

输入概念：
```
name: asyncio.create_task
definition: Python异步任务创建方法
category: async
```

输出JSON：
{{
  "difficulty": 0.6,
  "reasoning": "需理解事件循环和协程，属于中级异步编程",
  "prerequisites": ["事件循环", "协程基础"],
  "estimated_hours": 8
}}

# 现在处理：
概念：{concept_name}
定义：{concept_definition}
类别：{concept_category}

输出JSON（只输出JSON，不要其他内容）：
"""

# Few-Shot Prompt for Relation Inference
INFER_RELATIONS_PROMPT = """
推断技术概念之间的关系。

# 关系类型
- requires: A需要先学B（前置依赖）
- part_of: A是B的一部分（组成关系）
- related_to: A和B相关（一般关联）
- alternative_to: A和B是替代方案（竞品关系）

# 示例

输入概念：
```
[
  {{"name": "asyncio.create_task", "category": "async"}},
  {{"name": "协程", "category": "async"}},
  {{"name": "FastAPI", "category": "web"}},
  {{"name": "异步编程", "category": "async"}}
]
```

输出JSON：
{{
  "relations": [
    {{
      "from": "asyncio.create_task",
      "to": "协程",
      "type": "requires",
      "reasoning": "create_task 需要协程作为参数"
    }},
    {{
      "from": "asyncio.create_task",
      "to": "异步编程",
      "type": "part_of",
      "reasoning": "create_task 是异步编程的一个工具"
    }},
    {{
      "from": "FastAPI",
      "to": "异步编程",
      "type": "requires",
      "reasoning": "FastAPI 基于异步框架"
    }}
  ]
}}

# 现在处理：
概念列表：
{concepts}

输出JSON（只输出JSON，不要其他内容）：
"""


def build_extract_prompt(conversation: str) -> str:
    """
    构建知识点提取 Prompt

    Args:
        conversation: 对话内容（完整转录）

    Returns:
        完整的 prompt 字符串
    """
    # 截断过长对话（保留前3000字符）
    if len(conversation) > 3000:
        conversation = conversation[:3000] + "\n...(truncated)"

    return EXTRACT_CONCEPTS_PROMPT.format(conversation=conversation)


def build_difficulty_prompt(
    concept_name: str,
    concept_definition: str,
    concept_category: str = "general"
) -> str:
    """
    构建难度评估 Prompt

    Args:
        concept_name: 概念名称
        concept_definition: 概念定义
        concept_category: 概念类别

    Returns:
        完整的 prompt 字符串
    """
    return ASSESS_DIFFICULTY_PROMPT.format(
        concept_name=concept_name,
        concept_definition=concept_definition,
        concept_category=concept_category
    )


def build_relation_prompt(concepts: list) -> str:
    """
    构建关系推断 Prompt

    Args:
        concepts: 概念列表，每个概念包含 name 和 category

    Returns:
        完整的 prompt 字符串
    """
    import json
    concepts_json = json.dumps(concepts, ensure_ascii=False, indent=2)
    return INFER_RELATIONS_PROMPT.format(concepts=concepts_json)
