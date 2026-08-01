"""ID生成器测试"""
import sys
from pathlib import Path
import pytest
import re

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))


def test_generate_id():
    """测试ID生成"""
    from src.utils.id_generator import generate_id
    
    id1 = generate_id("test")
    id2 = generate_id("test")
    
    # 格式验证
    pattern = r"^test_\d+_[a-z0-9]{8}$"
    assert re.match(pattern, id1)
    assert re.match(pattern, id2)
    
    # 唯一性验证
    assert id1 != id2


def test_generate_session_id():
    """测试会话ID生成"""
    from src.utils.id_generator import generate_session_id
    
    session_id = generate_session_id()
    pattern = r"^session_\d+_[a-z0-9]{8}$"
    assert re.match(pattern, session_id)


def test_generate_project_id():
    """测试项目ID生成"""
    from src.utils.id_generator import generate_project_id
    
    project_id = generate_project_id()
    pattern = r"^project_\d+_[a-z0-9]{8}$"
    assert re.match(pattern, project_id)


def test_generate_knowledge_id():
    """测试知识ID生成"""
    from src.utils.id_generator import generate_knowledge_id
    
    knowledge_id = generate_knowledge_id()
    pattern = r"^knowledge_\d+_[a-z0-9]{8}$"
    assert re.match(pattern, knowledge_id)


def test_generate_task_id():
    """测试任务ID生成"""
    from src.utils.id_generator import generate_task_id
    
    task_id = generate_task_id()
    pattern = r"^task_\d+_[a-z0-9]{8}$"
    assert re.match(pattern, task_id)


def test_custom_length():
    """测试自定义长度"""
    from src.utils.id_generator import generate_id
    
    id_short = generate_id("test", length=4)
    id_long = generate_id("test", length=16)
    
    pattern_short = r"^test_\d+_[a-z0-9]{4}$"
    pattern_long = r"^test_\d+_[a-z0-9]{16}$"
    
    assert re.match(pattern_short, id_short)
    assert re.match(pattern_long, id_long)
