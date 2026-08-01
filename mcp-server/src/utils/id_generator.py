"""
ID生成器
生成唯一标识符，格式: {prefix}_{timestamp}_{random}
"""
import time
import random
import string
from typing import Optional


def generate_id(prefix: str, length: int = 8) -> str:
    """
    生成唯一ID

    Args:
        prefix: ID前缀 (如 'session', 'project', 'knowledge')
        length: 随机字符串长度，默认8

    Returns:
        格式: {prefix}_{timestamp}_{random}
        示例: session_1722518400_a7b3c9d2
    """
    timestamp = int(time.time())
    random_str = ''.join(
        random.choices(string.ascii_lowercase + string.digits, k=length)
    )
    return f"{prefix}_{timestamp}_{random_str}"


def generate_session_id() -> str:
    """生成会话ID"""
    return generate_id("session")


def generate_project_id() -> str:
    """生成项目ID"""
    return generate_id("project")


def generate_knowledge_id() -> str:
    """生成知识ID"""
    return generate_id("knowledge")


def generate_task_id() -> str:
    """生成任务ID"""
    return generate_id("task")
